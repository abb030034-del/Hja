"""
helpers/Ranks.py
=================
نظام الرتب والصلاحيات بالكامل مع تخزين Redis.

التسلسل الهرمي (من الأعلى للأدنى) :
    1) Dev (المطور)           - عام    - واحد فقط (Dev_Zaid)
    2) DevP (مطور مساعد)      - عام
    3) MY (مشغّل البوت)        - عام
    4) Primary Owner (مالك أساسي) - حسب المجموعة
    5) Owner (مالك)            - حسب المجموعة
    6) Manager (مدير)          - حسب المجموعة
    7) Admin (أدمن)            - حسب المجموعة
    8) VIP (مميز)              - حسب المجموعة
"""

import config

# ====== أسماء الرتب ======
RANK_DEV = "dev"
RANK_DEVP = "devp"
RANK_MY = "my"
RANK_PRIMARY_OWNER = "primary_owner"
RANK_OWNER = "owner"
RANK_MANAGER = "manager"
RANK_ADMIN = "admin"
RANK_VIP = "vip"

# ====== أسماء الرتب بالعربي ======
RANK_NAMES_AR = {
    RANK_DEV: "المطور",
    RANK_DEVP: "المطور المساعد",
    RANK_MY: "مشغل البوت",
    RANK_PRIMARY_OWNER: "المالك الأساسي",
    RANK_OWNER: "المالك",
    RANK_MANAGER: "المدير",
    RANK_ADMIN: "الأدمن",
    RANK_VIP: "المميز",
}

# ====== تصنيف الرتب ======
GLOBAL_RANKS = {RANK_DEV, RANK_DEVP, RANK_MY}
CHAT_RANKS = {RANK_PRIMARY_OWNER, RANK_OWNER, RANK_MANAGER, RANK_ADMIN, RANK_VIP}

# ====== ترتيب الرتب (الأعلى = الأقوى) ======
RANK_HIERARCHY = [
    RANK_DEV, RANK_DEVP, RANK_MY,
    RANK_PRIMARY_OWNER, RANK_OWNER, RANK_MANAGER, RANK_ADMIN, RANK_VIP,
]


# ====== مفاتيح Redis ======
def _rank_key(rank: str, chat_id: int = None) -> str:
    """مفتاح Redis لكل رتبة"""
    if rank in GLOBAL_RANKS:
        return f"rank:{rank}"
    return f"rank:{chat_id}:{rank}"


def _lock_key(rank: str, chat_id: int = None) -> str:
    """مفتاح Redis لقفل الرفع"""
    if rank in GLOBAL_RANKS:
        return f"rank_lock:global:{rank}"
    return f"rank_lock:{chat_id}:{rank}"


# ====== عمليات إضافة/حذف/قراءة الرتب ======
def add_rank(rds, rank: str, user_id: int, chat_id: int = None):
    rds.sadd(_rank_key(rank, chat_id), str(user_id))


def remove_rank(rds, rank: str, user_id: int, chat_id: int = None):
    rds.srem(_rank_key(rank, chat_id), str(user_id))


def has_rank(rds, rank: str, user_id: int, chat_id: int = None) -> bool:
    return bool(rds.sismember(_rank_key(rank, chat_id), str(user_id)))


def get_rank_members(rds, rank: str, chat_id: int = None) -> set:
    return rds.smembers(_rank_key(rank, chat_id)) or set()


def clear_rank(rds, rank: str, chat_id: int = None):
    rds.delete(_rank_key(rank, chat_id))


def clear_all_chat_ranks(rds, chat_id: int):
    """مسح كل الرتب الخاصة بمجموعة"""
    for r in CHAT_RANKS:
        rds.delete(_rank_key(r, chat_id))


def clear_all_global_ranks(rds):
    """مسح كل الرتب العامة (ما عدا Dev)"""
    for r in (RANK_DEVP, RANK_MY):
        rds.delete(_rank_key(r))


# ====== التحقق من الصلاحيات (Pls Functions) ======
def is_dev(user_id) -> bool:
    """هل المستخدم هو المطور Dev_Zaid ؟"""
    try:
        return int(user_id) == int(config.Dev_Zaid)
    except Exception:
        return False


def dev_pls(rds, user_id, chat_id=None) -> bool:
    """يسمح فقط للمطور Dev"""
    return is_dev(user_id)


def devp_pls(rds, user_id, chat_id=None) -> bool:
    """يسمح للمطور وللمطور المساعد"""
    if is_dev(user_id):
        return True
    return has_rank(rds, RANK_DEVP, user_id)


def my_pls(rds, user_id, chat_id=None) -> bool:
    """يسمح للمطور والمساعد ومشغّل البوت"""
    if devp_pls(rds, user_id):
        return True
    return has_rank(rds, RANK_MY, user_id)


def primary_owner_pls(rds, user_id, chat_id) -> bool:
    """يسمح للمالك الأساسي وما فوق"""
    if my_pls(rds, user_id):
        return True
    return has_rank(rds, RANK_PRIMARY_OWNER, user_id, chat_id)


def owner_pls(rds, user_id, chat_id) -> bool:
    """يسمح للمالك وما فوق"""
    if primary_owner_pls(rds, user_id, chat_id):
        return True
    return has_rank(rds, RANK_OWNER, user_id, chat_id)


def manager_pls(rds, user_id, chat_id) -> bool:
    """يسمح للمدير وما فوق"""
    if owner_pls(rds, user_id, chat_id):
        return True
    return has_rank(rds, RANK_MANAGER, user_id, chat_id)


def admin_pls(rds, user_id, chat_id) -> bool:
    """يسمح للأدمن وما فوق"""
    if manager_pls(rds, user_id, chat_id):
        return True
    return has_rank(rds, RANK_ADMIN, user_id, chat_id)


def vip_pls(rds, user_id, chat_id) -> bool:
    """يسمح للمميز وما فوق"""
    if admin_pls(rds, user_id, chat_id):
        return True
    return has_rank(rds, RANK_VIP, user_id, chat_id)


# ====== جلب رتبة المستخدم الأعلى ======
def get_user_top_rank(rds, user_id, chat_id=None):
    """ارجع أعلى رتبة لدى المستخدم (أو None)"""
    if is_dev(user_id):
        return RANK_DEV
    for r in (RANK_DEVP, RANK_MY):
        if has_rank(rds, r, user_id):
            return r
    if chat_id is not None:
        for r in (RANK_PRIMARY_OWNER, RANK_OWNER, RANK_MANAGER, RANK_ADMIN, RANK_VIP):
            if has_rank(rds, r, user_id, chat_id):
                return r
    return None


# ====== قفل / تفعيل الرفع ======
def lock_promotion(rds, rank: str, chat_id: int = None):
    rds.set(_lock_key(rank, chat_id), "1")


def unlock_promotion(rds, rank: str, chat_id: int = None):
    rds.set(_lock_key(rank, chat_id), "0")


def is_promotion_locked(rds, rank: str, chat_id: int = None) -> bool:
    return rds.get(_lock_key(rank, chat_id)) == "1"


# ====== صلاحية الرفع لكل رتبة ======
# من يستطيع رفع/تنزيل هذه الرتبة ؟
RANK_PROMOTER = {
    RANK_DEV:            dev_pls,            # المطور فقط
    RANK_DEVP:           dev_pls,            # المطور فقط
    RANK_MY:             devp_pls,           # المطور أو المساعد
    RANK_PRIMARY_OWNER:  my_pls,             # مشغّل البوت أو أعلى
    RANK_OWNER:          primary_owner_pls,  # المالك الأساسي أو أعلى
    RANK_MANAGER:        owner_pls,          # المالك أو أعلى
    RANK_ADMIN:          manager_pls,        # المدير أو أعلى
    RANK_VIP:            admin_pls,          # الأدمن أو أعلى
}


def can_promote(rds, user_id, target_rank: str, chat_id=None) -> bool:
    """هل يحق لهذا المستخدم رفع/تنزيل هذه الرتبة ؟"""
    checker = RANK_PROMOTER.get(target_rank)
    if not checker:
        return False
    # الرتب العامة لا تحتاج chat_id
    if target_rank in GLOBAL_RANKS:
        return checker(rds, user_id)
    return checker(rds, user_id, chat_id)
