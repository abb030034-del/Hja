# 🤖 Factory Bot — دليل التنصيب على AWS Lightsail

## ⚙️ المتطلبات
- سيرفر AWS Lightsail يعمل بـ Ubuntu 22.04
- بوت تيليجرام جديد من [@BotFather](https://t.me/BotFather)
- معرفك على تيليجرام (User ID)

---

## 📁 هيكل المشروع

```
factory_bot/
├── main.py           ← الكود الرئيسي للبوت
├── requirements.txt  ← المكتبات المطلوبة
├── deploy.sh         ← سكريبت التنصيب التلقائي
├── bot.sh            ← أوامر إدارة البوت
├── .env.example      ← مثال على المتغيرات البيئية
└── README.md         ← هذا الملف
```

---

## 🚀 خطوات التنصيب

### 1. الاتصال بالسيرفر عبر SSH
```bash
ssh ubuntu@<IP-السيرفر>
```

### 2. رفع ملفات المشروع للسيرفر
من جهازك المحلي، استخدم أمر scp:
```bash
scp -r factory_bot/ ubuntu@<IP-السيرفر>:~/factory_bot
```
أو بالطريقة اليدوية عبر لوحة تحكم Lightsail > File Manager.

### 3. تشغيل سكريبت التنصيب
```bash
cd ~/factory_bot
chmod +x deploy.sh bot.sh
./deploy.sh
```
السكريبت سيقوم تلقائياً بـ:
- تحديث النظام
- تنصيب Python والمكتبات
- إعداد خدمة systemd لتشغيل البوت تلقائياً عند إعادة تشغيل السيرفر

### 4. إضافة التوكن والـ ID
```bash
nano ~/factory_bot/.env
```
عدّل السطرين:
```
MASTER_TOKEN=توكن_بوتك_هنا
MASTER_ID=معرفك_هنا
```
احفظ بـ `Ctrl+X` ثم `Y` ثم `Enter`

### 5. تشغيل البوت
```bash
./bot.sh start
```

---

## 🛠️ أوامر الإدارة اليومية

```bash
./bot.sh start        # تشغيل البوت
./bot.sh stop         # إيقاف البوت
./bot.sh restart      # إعادة التشغيل
./bot.sh status       # الحالة الحالية
./bot.sh logs         # عرض اللوج مباشرة (Ctrl+C للخروج)
./bot.sh logs-last    # عرض آخر 100 سطر من اللوج
./bot.sh update       # تحديث المكتبات وإعادة التشغيل
```

---

## 🔒 ملاحظات أمنية
- لا تشارك ملف `.env` مع أحد
- افتح فقط المنافذ الضرورية في Lightsail Firewall (لا يحتاج البوت لأي منفذ مفتوح)
- البوت يعمل عبر Long Polling فلا يحتاج IP ثابت أو Domain

---

## ⚠️ ملاحظة مهمة حول البيانات
البيانات تُحفظ في `bots_data.json` على السيرفر مباشرة.
اعمل نسخة احتياطية دورية:
```bash
cp ~/factory_bot/bots_data.json ~/bots_data_backup_$(date +%F).json
```
