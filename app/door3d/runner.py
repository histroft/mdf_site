"""Фоновая передача тела договора из WEB_NST в HTTP API RENDER_NEW."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

from config import Config
from app.door3d.mapping import build_render_request


_JOBS = {}
_LOCK = threading.Lock()
_JOB_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def _job_dir(job_id: str) -> Path:
    if not _JOB_ID_RE.fullmatch(job_id):
        raise ValueError("Некорректный идентификатор задачи")
    return Path(Config.RESULT_3D_DIR) / job_id


def _status_file(job_id: str) -> Path:
    return _job_dir(job_id) / "status.json"


def _write_status(job_id: str, status: str, message: str = "", **extra) -> None:
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    payload = {"status": status, "message": message}
    payload.update(extra)
    status_file = _status_file(job_id)
    temp_file = status_file.with_suffix(".json.tmp")
    temp_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temp_file, status_file)


def image_path(job_id: str, side: str) -> str:
    side = "in" if side == "in" else "out"
    return str(_job_dir(job_id) / f"door_{side}.png")


def _api_headers() -> dict[str, str]:
    token = str(getattr(Config, "RENDER_API_TOKEN", "") or "")
    return {"X-API-Key": token} if token else {}


def _same_render_origin(url: str) -> str:
    """Accept download links only from the configured render server."""
    base = str(Config.RENDER_API_URL).rstrip("/") + "/"
    absolute = urljoin(base, url)
    expected = urlsplit(base)
    actual = urlsplit(absolute)
    if (actual.scheme, actual.netloc) != (expected.scheme, expected.netloc):
        raise RuntimeError("Сервер рендера вернул ссылку на посторонний адрес")
    return absolute


def _response_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        message = payload.get("error") or payload.get("message")
        details = payload.get("details")
        if message and details:
            return f"{message}: {details}"
        if message:
            return str(message)
    text = (response.text or "").strip()
    return text[:1000] if text else f"HTTP {response.status_code}"


def _download_image(
    session: requests.Session, download_url: str, destination: Path
) -> None:
    url = _same_render_origin(download_url)
    timeout = (
        int(Config.RENDER_CONNECT_TIMEOUT),
        int(Config.RENDER_DOWNLOAD_TIMEOUT),
    )
    max_bytes = int(Config.RENDER_MAX_IMAGE_BYTES)
    temp_path = destination.with_suffix(destination.suffix + ".part")
    total = 0

    try:
        with session.get(url, stream=True, timeout=timeout) as response:
            if not response.ok:
                raise RuntimeError(f"Не удалось скачать PNG: {_response_error(response)}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with temp_path.open("wb") as output:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise RuntimeError("PNG от сервера рендера превышает допустимый размер")
                    output.write(chunk)

        signature = temp_path.read_bytes()[:8]
        if signature != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("Сервер рендера вернул повреждённый PNG")
        os.replace(temp_path, destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _run(job_id: str, request_file: str) -> None:
    """Отправить тело договора, дождаться рендера и скачать обе PNG."""
    try:
        api_url = str(Config.RENDER_API_URL).strip().rstrip("/")
        if not api_url:
            raise RuntimeError("Не задан RENDER_API_URL")

        render_request = json.loads(Path(request_file).read_text(encoding="utf-8"))

        timeout = (int(Config.RENDER_CONNECT_TIMEOUT), int(Config.RENDER_TIMEOUT))
        with requests.Session() as session:
            session.headers.update(_api_headers())
            response = session.post(
                f"{api_url}/render",
                json=render_request,
                timeout=timeout,
            )

            if not response.ok:
                raise RuntimeError(f"Ошибка RENDER_NEW: {_response_error(response)}")
            try:
                result = response.json()
            except ValueError as exc:
                raise RuntimeError("RENDER_NEW вернул некорректный JSON") from exc
            if not result.get("success"):
                raise RuntimeError(
                    f"Ошибка RENDER_NEW: {result.get('error', 'неизвестная ошибка')}"
                )

            images = result.get("images") or {}
            if not images.get("out") or not images.get("in"):
                raise RuntimeError("RENDER_NEW не вернул ссылки на обе стороны двери")

            _download_image(session, images["out"], Path(image_path(job_id, "out")))
            _download_image(session, images["in"], Path(image_path(job_id, "in")))

        _write_status(
            job_id,
            "done",
            "Готово",
            out_png=image_path(job_id, "out"),
            in_png=image_path(job_id, "in"),
            render_request_id=result.get("request_id"),
        )
    except requests.Timeout:
        _write_status(job_id, "error", "Превышено время ожидания RENDER_NEW")
    except requests.RequestException as exc:
        _write_status(job_id, "error", f"RENDER_NEW недоступен: {exc}")
    except Exception as exc:
        _write_status(job_id, "error", f"Ошибка 3D-рендера: {exc}")
    finally:
        with _LOCK:
            if job_id in _JOBS:
                _JOBS[job_id]["finished"] = True


def start_job(request_data: dict) -> tuple[str, list[str]]:
    """Передать RENDER_NEW тело договора и четыре текстуры сцены."""
    render_request = build_render_request(request_data)

    job_id = uuid.uuid4().hex[:12]
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=False)

    request_file = job_dir / "request.json"
    request_file.write_text(
        json.dumps(render_request, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_status(
        job_id,
        "running",
        "Запрос отправляется на RENDER_NEW",
    )

    with _LOCK:
        _JOBS[job_id] = {"finished": False}

    thread = threading.Thread(
        target=_run,
        args=(job_id, str(request_file)),
        daemon=True,
        name=f"door-render-{job_id}",
    )
    thread.start()
    return job_id, []


def get_status(job_id: str) -> dict:
    """Return status from disk (running|done|error|unknown)."""
    try:
        status_file = _status_file(job_id)
    except ValueError:
        return {"status": "unknown", "message": "Задача не найдена"}
    if not status_file.exists():
        return {"status": "unknown", "message": "Задача не найдена"}
    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "error", "message": f"Не удалось прочитать статус: {exc}"}

    data["out_ready"] = Path(image_path(job_id, "out")).exists()
    data["in_ready"] = Path(image_path(job_id, "in")).exists()
    return data
