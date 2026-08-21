#!/bin/bash
echo "🛑 Остановка сервисов WEB_NST и RENDER_NEW..."
sudo systemctl stop web_nst
sudo systemctl stop render_new
echo "✅ Сервисы остановлены."