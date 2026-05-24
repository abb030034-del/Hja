#!/bin/bash
# سكريبت التنصيب التلقائي على Ubuntu/Debian (AWS Lightsail)

set -e

echo "======================================"
echo "  تنصيب Factory Bot على AWS Lightsail"
echo "======================================"

# تحديث النظام
echo "[1/6] تحديث النظام..."
sudo apt update -y && sudo apt upgrade -y

# تنصيب Python وpip وأدوات أخرى
echo "[2/6] تنصيب Python..."
sudo apt install -y python3 python3-pip python3-venv git screen

# إنشاء مجلد المشروع
echo "[3/6] إعداد مجلد المشروع..."
mkdir -p ~/factory_bot
cd ~/factory_bot

# إنشاء البيئة الافتراضية وتنصيب المكتبات
echo "[4/6] تنصيب المكتبات..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# إنشاء ملف .env إذا لم يكن موجوداً
if [ ! -f .env ]; then
    echo "[5/6] إنشاء ملف .env..."
    cp .env.example .env
    echo ""
    echo "⚠️  يرجى تعديل ملف .env وإضافة التوكن والـ ID:"
    echo "    nano ~/factory_bot/.env"
else
    echo "[5/6] ملف .env موجود بالفعل."
fi

# إنشاء خدمة systemd لتشغيل البوت تلقائياً
echo "[6/6] إعداد خدمة systemd..."
CURRENT_USER=$(whoami)
PROJECT_DIR=$(pwd)

sudo tee /etc/systemd/system/factory-bot.service > /dev/null << SYSTEMD
[Unit]
Description=Telegram Factory Bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD

sudo systemctl daemon-reload
sudo systemctl enable factory-bot

echo ""
echo "======================================"
echo "✅ اكتمل التنصيب!"
echo ""
echo "📋 الخطوات التالية:"
echo "   1. عدّل ملف .env:"
echo "      nano ~/factory_bot/.env"
echo ""
echo "   2. شغّل البوت:"
echo "      sudo systemctl start factory-bot"
echo ""
echo "   3. تحقق من الحالة:"
echo "      sudo systemctl status factory-bot"
echo "======================================"
