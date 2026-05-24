#!/usr/bin/env python3
"""
clean.py
=========
تنظيف الملفات المؤقتة والـsessions والـcache .

الاستخدام :
    python clean.py            # تنظيف عادي
    python clean.py --all       # شامل (Redis + ملفات)
    python clean.py --sessions  # session فقط
"""

import os
import sys
import shutil
import glob


HERE = os.path.dirname(os.path.abspath(__file__))


def remove(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            print(f"  [DIR]  removed  {path}")
        elif os.path.exists(path):
            os.remove(path)
            print(f"  [FILE] removed  {path}")
    except Exception as e:
        print(f"  [ERR]  {path}  :  {e}")


def clean_basic():
    print("🧹 تنظيف عام ...")
    # __pycache__
    for root, dirs, _ in os.walk(HERE):
        for d in list(dirs):
            if d == "__pycache__":
                remove(os.path.join(root, d))
                dirs.remove(d)
    # .pyc
    for p in glob.glob(os.path.join(HERE, "**", "*.pyc"), recursive=True):
        remove(p)
    # logs
    for p in glob.glob(os.path.join(HERE, "*.log")):
        remove(p)
    # /tmp
    for p in ("/tmp/bot_groups.txt", "/tmp/bot_users.txt"):
        remove(p)


def clean_sessions():
    print("🗑 تنظيف session ...")
    for ext in ("*.session", "*.session-journal"):
        for p in glob.glob(os.path.join(HERE, ext)):
            remove(p)


def clean_redis():
    print("🔻 تنظيف Redis ...")
    try:
        import redis
        sys.path.insert(0, HERE)
        import config as cfg  # type: ignore
        r = redis.Redis(
            host=cfg.REDIS_HOST, port=cfg.REDIS_PORT,
            db=cfg.REDIS_DB, password=cfg.REDIS_PASSWORD,
            decode_responses=True,
        )
        n = 0
        for pattern in ("game:active:*", "sarhni:token:*", "sarhni:pending:*",
                        "marriage:proposal:*", "whisper:*", "bc:state:*"):
            for key in r.scan_iter(pattern):
                r.delete(key); n += 1
        print(f"  Redis : حُذف {n} مفتاح مؤقت")
    except Exception as e:
        print(f"  Redis : فشل  ({e})")


def main():
    argv = sys.argv[1:]
    clean_basic()
    if "--sessions" in argv or "--all" in argv:
        clean_sessions()
    if "--all" in argv:
        clean_redis()
    print("✅ تم.")


if __name__ == "__main__":
    main()
