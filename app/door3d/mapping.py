"""Формирование прозрачного запроса WEB_NST → RENDER_NEW.

Данные договора не расшифровываются на стороне сайта. RENDER_NEW получает
тот же объект ``data``, что и ``/api/make-order``, плюс только выбранные
текстуры стены и пола.
"""

from __future__ import annotations

from typing import Any

from app.door3d.scene_catalog import get_scene_assets


SCENE_REQUEST_FIELDS = (
    "wall_texture_path",
    "floor_texture_path",
    "wall_texture_path_inner",
    "floor_texture_path_inner",
)


class RenderRequestError(ValueError):
    pass


def _scene_asset(value: Any, field_name: str) -> str:
    asset = str(value or "").strip()
    if asset not in get_scene_assets():
        raise RenderRequestError(
            f"Для поля «{field_name}» выбрана неизвестная текстура: {asset}"
        )
    return asset


def build_render_request(request_data: dict[str, Any]) -> dict[str, Any]:
    """Оставить тело договора без изменений и проверить четыре поля сцены."""
    if not isinstance(request_data, dict):
        raise RenderRequestError("Некорректное тело запроса 3D")

    order = request_data.get("data")
    if not isinstance(order, dict) or not order:
        raise RenderRequestError("Нет данных заказа")
    if "панель" in str(order.get("model") or "").casefold():
        raise RenderRequestError("3D-рендер поддерживается только для дверей")

    payload: dict[str, Any] = {"data": dict(order)}
    for field_name in SCENE_REQUEST_FIELDS:
        payload[field_name] = _scene_asset(
            request_data.get(field_name),
            field_name,
        )
    return payload
