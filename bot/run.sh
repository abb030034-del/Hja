#!/usr/bin/env bash
# run.sh — تشغيل البوت
# يدعم إعادة التشغيل التلقائي عند الـ exit (مفيد مع أمر "تحديث")

set -e
cd "$(dirname "$0")"

# تأكد من المتطلبات
if [ ! -d ".venv" ]; then
    echo "🛠 إنشاء بيئة افتراضية ..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "📦 تثبيت المتطلبات ..."
pip install --quiet -r requirements.txt

# حلقة لإعادة التشغيل التلقائي
while true; do
    echo "🚀 تشغيل البوت ..."
    python main.py
    EXIT_CODE=$?
    echo "⚠️ البوت أُغلق (code=$EXIT_CODE). إعادة التشغيل بعد 2 ثانية ..."
    sleep 2
done
