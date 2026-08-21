#!/bin/bash
echo "🔄 Перезапуск сервисов WEB_NST и RENDER_NEW..."
sudo systemctl restart web_nst
sudo systemctl restart render_new
echo "✅ Готово. Проверьте статус."