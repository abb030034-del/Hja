#!/bin/bash
# أوامر إدارة البوت اليومية

ACTION=$1

case $ACTION in
  start)
    sudo systemctl start factory-bot
    echo "✅ تم تشغيل البوت"
    ;;
  stop)
    sudo systemctl stop factory-bot
    echo "⛔ تم إيقاف البوت"
    ;;
  restart)
    sudo systemctl restart factory-bot
    echo "🔄 تم إعادة تشغيل البوت"
    ;;
  status)
    sudo systemctl status factory-bot
    ;;
  logs)
    sudo journalctl -u factory-bot -f --no-pager
    ;;
  logs-last)
    sudo journalctl -u factory-bot -n 100 --no-pager
    ;;
  update)
    echo "📥 تحديث الكود..."
    sudo systemctl stop factory-bot
    cd ~/factory_bot
    source venv/bin/activate
    pip install -r requirements.txt --upgrade
    sudo systemctl start factory-bot
    echo "✅ تم التحديث وإعادة التشغيل"
    ;;
  *)
    echo "الاستخدام: ./bot.sh [start|stop|restart|status|logs|logs-last|update]"
    ;;
esac
