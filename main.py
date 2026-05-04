"""
OTPKING PRO v5 — FULLY ADVANCED
✅ Live Stock + Price (SmsPool + Vak-SMS) — dono dikhein
✅ Admin: Balance Add / Deduct (galti se add huaa to kaat bhi sako)
✅ Admin: User search by ID or @username
✅ Admin: Balance Adjust inline buttons
✅ All functions working
✅ Hidden 40% Margin | Multi-Platform Refer & Earn
✅ Default prices fallback when API balance = 0
"""
import os, logging, requests, time, math, io, json
from pymongo import MongoClient, DESCENDING
from telebot import types
import telebot
from dotenv import load_dotenv
from threading import Thread
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN          = os.getenv('BOT_TOKEN', '')
MONGO_URI          = os.getenv('MONGO_URI') or os.getenv('MONGO_URL', '')
SMSPOOL_KEY        = os.getenv('SMSPOOL_API_KEY', '')
VAKSMS_KEY         = os.getenv('VAKSMS_API_KEY', '')
OWNER_ID           = int(os.getenv('OWNER_ID', '0'))
SUPPORT_BOT        = os.getenv('SUPPORT_BOT', '@YourHelpBot')
PROOF_CHANNEL_ID   = os.getenv('PROOF_CHANNEL_ID', '@ProofChannel')
PROOF_CHANNEL_LINK = os.getenv('PROOF_CHANNEL_LINK', 'https://t.me/ProofChannel')
GROUP_ID           = os.getenv('GROUP_ID', '@YourGroup')
GROUP_LINK         = os.getenv('GROUP_LINK', 'https://t.me/YourGroup')
BINANCE_ADDRESS    = os.getenv('BINANCE_ADDRESS', '')
UPI_ID             = os.getenv('UPI_ID', '')

USDT_RATE = 85.0
MARGIN    = 1.40   # 40% — admin only
LOW_STOCK = 5

# ── DEFAULT PRICES (INR) — jab API balance 0 ya API fail ho ─────────────────
DEFAULT_PRICES = {
    "whatsapp": {"russia":15,"india":12,"usa":20,"england":25,"ukraine":12,
                 "brazil":10,"indonesia":8,"kenya":8,"nigeria":8,"pakistan":8,
                 "cambodia":8,"myanmar":8,"vietnam":8,"philippines":10,
                 "bangladesh":8,"kazakhstan":10},
    "telegram":  {"russia":12,"india":10,"usa":18,"england":22,"ukraine":10,
                  "cambodia":8,"myanmar":8,"indonesia":8,"kazakhstan":8,
                  "vietnam":8,"bangladesh":8,"philippines":10},
    "instagram": {"russia":18,"india":15,"usa":25,"ukraine":15,"brazil":12,
                  "indonesia":10,"england":28,"nigeria":10},
    "google":    {"russia":20,"india":18,"usa":28,"ukraine":18,"england":30,
                  "indonesia":12},
    "facebook":  {"russia":15,"india":12,"usa":22,"ukraine":12,"indonesia":10,
                  "brazil":10},
    "tiktok":    {"russia":15,"usa":20,"india":12,"indonesia":10,"brazil":10},
    "twitter":   {"russia":15,"india":12,"usa":20,"england":22},
    "snapchat":  {"russia":18,"usa":22,"england":25,"india":15},
    "amazon":    {"russia":20,"india":18,"usa":28,"england":30},
    "linkedin":  {"russia":22,"india":20,"usa":30,"england":32},
}
DEFAULT_STOCK = 50

BAD_WORDS = ["madarchod","mc","bc","bhenchod","gandu","chutiya","randi","harami",
             "bhosdike","loda","lauda","chut","bsdk","fuck","bitch","asshole",
             "bastard","shit","dick","cunt","whore","sala","maderchod","behenchod"]

# ── SmsPool API Codes ─────────────────────────────────────────────────────────
SMSPOOL_CC  = {"russia":"RU","india":"IN","usa":"US","england":"GB","ukraine":"UA",
               "brazil":"BR","indonesia":"ID","kenya":"KE","nigeria":"NG","pakistan":"PK",
               "cambodia":"KH","myanmar":"MM","vietnam":"VN","philippines":"PH",
               "bangladesh":"BD","kazakhstan":"KZ"}
SMSPOOL_SVC = {"whatsapp":"wa","telegram":"tg","instagram":"ig","google":"go",
               "facebook":"fb","tiktok":"tt","twitter":"tw","snapchat":"sc",
               "amazon":"amazon","linkedin":"li"}

# ── Vak-SMS API Codes ─────────────────────────────────────────────────────────
VAKSMS_CC   = {"russia":"ru","india":"in","usa":"us","england":"gb","ukraine":"ua",
               "brazil":"br","indonesia":"id","kenya":"ke","nigeria":"ng","pakistan":"pk",
               "cambodia":"kh","myanmar":"mm","vietnam":"vn","philippines":"ph",
               "bangladesh":"bd","kazakhstan":"kz"}
VAKSMS_SVC  = {"whatsapp":"wh","telegram":"tg","instagram":"ig","google":"go",
               "facebook":"fb","tiktok":"tt","twitter":"tw","snapchat":"sc",
               "amazon":"am","linkedin":"li"}

# ══════════════════════════════════════════════════════════════════════════════
#  SERVICES
# ══════════════════════════════════════════════════════════════════════════════
SERVICES = {
    "📱 WhatsApp": {
        "wa_russia":      {"cc":"russia","api":"whatsapp","flag":"🇷🇺","country":"Russia"},
        "wa_india":       {"cc":"india","api":"whatsapp","flag":"🇮🇳","country":"India"},
        "wa_usa":         {"cc":"usa","api":"whatsapp","flag":"🇺🇸","country":"USA"},
        "wa_uk":          {"cc":"england","api":"whatsapp","flag":"🇬🇧","country":"UK"},
        "wa_ukraine":     {"cc":"ukraine","api":"whatsapp","flag":"🇺🇦","country":"Ukraine"},
        "wa_brazil":      {"cc":"brazil","api":"whatsapp","flag":"🇧🇷","country":"Brazil"},
        "wa_indonesia":   {"cc":"indonesia","api":"whatsapp","flag":"🇮🇩","country":"Indonesia"},
        "wa_kenya":       {"cc":"kenya","api":"whatsapp","flag":"🇰🇪","country":"Kenya"},
        "wa_nigeria":     {"cc":"nigeria","api":"whatsapp","flag":"🇳🇬","country":"Nigeria"},
        "wa_pakistan":    {"cc":"pakistan","api":"whatsapp","flag":"🇵🇰","country":"Pakistan"},
        "wa_cambodia":    {"cc":"cambodia","api":"whatsapp","flag":"🇰🇭","country":"Cambodia"},
        "wa_myanmar":     {"cc":"myanmar","api":"whatsapp","flag":"🇲🇲","country":"Myanmar"},
        "wa_vietnam":     {"cc":"vietnam","api":"whatsapp","flag":"🇻🇳","country":"Vietnam"},
        "wa_philippines": {"cc":"philippines","api":"whatsapp","flag":"🇵🇭","country":"Philippines"},
        "wa_bangladesh":  {"cc":"bangladesh","api":"whatsapp","flag":"🇧🇩","country":"Bangladesh"},
        "wa_kazakhstan":  {"cc":"kazakhstan","api":"whatsapp","flag":"🇰🇿","country":"Kazakhstan"},
    },
    "✈️ Telegram": {
        "tg_russia":      {"cc":"russia","api":"telegram","flag":"🇷🇺","country":"Russia"},
        "tg_india":       {"cc":"india","api":"telegram","flag":"🇮🇳","country":"India"},
        "tg_usa":         {"cc":"usa","api":"telegram","flag":"🇺🇸","country":"USA"},
        "tg_uk":          {"cc":"england","api":"telegram","flag":"🇬🇧","country":"UK"},
        "tg_ukraine":     {"cc":"ukraine","api":"telegram","flag":"🇺🇦","country":"Ukraine"},
        "tg_cambodia":    {"cc":"cambodia","api":"telegram","flag":"🇰🇭","country":"Cambodia"},
        "tg_myanmar":     {"cc":"myanmar","api":"telegram","flag":"🇲🇲","country":"Myanmar"},
        "tg_indonesia":   {"cc":"indonesia","api":"telegram","flag":"🇮🇩","country":"Indonesia"},
        "tg_kazakhstan":  {"cc":"kazakhstan","api":"telegram","flag":"🇰🇿","country":"Kazakhstan"},
        "tg_vietnam":     {"cc":"vietnam","api":"telegram","flag":"🇻🇳","country":"Vietnam"},
        "tg_bangladesh":  {"cc":"bangladesh","api":"telegram","flag":"🇧🇩","country":"Bangladesh"},
        "tg_philippines": {"cc":"philippines","api":"telegram","flag":"🇵🇭","country":"Philippines"},
    },
    "📸 Instagram": {
        "ig_russia":    {"cc":"russia","api":"instagram","flag":"🇷🇺","country":"Russia"},
        "ig_india":     {"cc":"india","api":"instagram","flag":"🇮🇳","country":"India"},
        "ig_usa":       {"cc":"usa","api":"instagram","flag":"🇺🇸","country":"USA"},
        "ig_ukraine":   {"cc":"ukraine","api":"instagram","flag":"🇺🇦","country":"Ukraine"},
        "ig_brazil":    {"cc":"brazil","api":"instagram","flag":"🇧🇷","country":"Brazil"},
        "ig_indonesia": {"cc":"indonesia","api":"instagram","flag":"🇮🇩","country":"Indonesia"},
        "ig_uk":        {"cc":"england","api":"instagram","flag":"🇬🇧","country":"UK"},
        "ig_nigeria":   {"cc":"nigeria","api":"instagram","flag":"🇳🇬","country":"Nigeria"},
    },
    "📧 Gmail": {
        "gm_russia":    {"cc":"russia","api":"google","flag":"🇷🇺","country":"Russia"},
        "gm_india":     {"cc":"india","api":"google","flag":"🇮🇳","country":"India"},
        "gm_usa":       {"cc":"usa","api":"google","flag":"🇺🇸","country":"USA"},
        "gm_ukraine":   {"cc":"ukraine","api":"google","flag":"🇺🇦","country":"Ukraine"},
        "gm_uk":        {"cc":"england","api":"google","flag":"🇬🇧","country":"UK"},
        "gm_indonesia": {"cc":"indonesia","api":"google","flag":"🇮🇩","country":"Indonesia"},
    },
    "📘 Facebook": {
        "fb_russia":    {"cc":"russia","api":"facebook","flag":"🇷🇺","country":"Russia"},
        "fb_india":     {"cc":"india","api":"facebook","flag":"🇮🇳","country":"India"},
        "fb_usa":       {"cc":"usa","api":"facebook","flag":"🇺🇸","country":"USA"},
        "fb_ukraine":   {"cc":"ukraine","api":"facebook","flag":"🇺🇦","country":"Ukraine"},
        "fb_indonesia": {"cc":"indonesia","api":"facebook","flag":"🇮🇩","country":"Indonesia"},
        "fb_brazil":    {"cc":"brazil","api":"facebook","flag":"🇧🇷","country":"Brazil"},
    },
    "🎵 TikTok": {
        "tt_russia":    {"cc":"russia","api":"tiktok","flag":"🇷🇺","country":"Russia"},
        "tt_usa":       {"cc":"usa","api":"tiktok","flag":"🇺🇸","country":"USA"},
        "tt_india":     {"cc":"india","api":"tiktok","flag":"🇮🇳","country":"India"},
        "tt_indonesia": {"cc":"indonesia","api":"tiktok","flag":"🇮🇩","country":"Indonesia"},
        "tt_brazil":    {"cc":"brazil","api":"tiktok","flag":"🇧🇷","country":"Brazil"},
    },
    "🐦 Twitter/X": {
        "tw_russia":    {"cc":"russia","api":"twitter","flag":"🇷🇺","country":"Russia"},
        "tw_india":     {"cc":"india","api":"twitter","flag":"🇮🇳","country":"India"},
        "tw_usa":       {"cc":"usa","api":"twitter","flag":"🇺🇸","country":"USA"},
        "tw_uk":        {"cc":"england","api":"twitter","flag":"🇬🇧","country":"UK"},
    },
    "📷 Snapchat": {
        "sc_russia":    {"cc":"russia","api":"snapchat","flag":"🇷🇺","country":"Russia"},
        "sc_usa":       {"cc":"usa","api":"snapchat","flag":"🇺🇸","country":"USA"},
        "sc_uk":        {"cc":"england","api":"snapchat","flag":"🇬🇧","country":"UK"},
        "sc_india":     {"cc":"india","api":"snapchat","flag":"🇮🇳","country":"India"},
    },
    "🛒 Amazon": {
        "az_russia":    {"cc":"russia","api":"amazon","flag":"🇷🇺","country":"Russia"},
        "az_india":     {"cc":"india","api":"amazon","flag":"🇮🇳","country":"India"},
        "az_usa":       {"cc":"usa","api":"amazon","flag":"🇺🇸","country":"USA"},
        "az_uk":        {"cc":"england","api":"amazon","flag":"🇬🇧","country":"UK"},
    },
    "💼 LinkedIn": {
        "li_russia":    {"cc":"russia","api":"linkedin","flag":"🇷🇺","country":"Russia"},
        "li_india":     {"cc":"india","api":"linkedin","flag":"🇮🇳","country":"India"},
        "li_usa":       {"cc":"usa","api":"linkedin","flag":"🇺🇸","country":"USA"},
        "li_uk":        {"cc":"england","api":"linkedin","flag":"🇬🇧","country":"UK"},
    },
}
ALL_BTNS = set(SERVICES.keys())

# ══════════════════════════════════════════════════════════════════════════════
#  409 FIX
# ══════════════════════════════════════════════════════════════════════════════
def clear_session():
    try:
        requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10)
        time.sleep(5)
        for _ in range(3):
            try:
                requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1&timeout=1",
                    timeout=10)
            except: pass
            time.sleep(2)
        logger.info("✅ Session cleared")
    except Exception as e:
        logger.error(f"Session clear: {e}")

clear_session()

# ══════════════════════════════════════════════════════════════════════════════
#  MONGODB
# ══════════════════════════════════════════════════════════════════════════════
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=10000,
    maxPoolSize=10,
    retryWrites=True,
    w='majority',
)
db            = client['otp_king_pro']
users_col     = db['users']
orders_col    = db['orders']
deposits_col  = db['deposits']
platforms_col = db['earn_platforms']
channels_col  = db['force_channels']
settings_col  = db['bot_settings']
admin_log_col = db['admin_balance_log']  # NEW: balance add/deduct audit log

try:
    users_col.create_index("user_id", unique=True)
    users_col.create_index("username")
    orders_col.create_index("order_id")
    orders_col.create_index("user_id")
    deposits_col.create_index("user_id")
    channels_col.create_index("channel_id", unique=True)
    logger.info("✅ MongoDB indexes created")
except Exception as e:
    logger.warning(f"Index creation: {e}")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown", threaded=False)

# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_setting(key, default):
    try:
        doc = settings_col.find_one({"key": key})
        return doc["value"] if doc else default
    except: return default

def set_setting(key, value):
    try:
        settings_col.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)
    except: pass

def get_margin():
    return float(get_setting("margin", MARGIN))

def get_usdt_rate():
    return float(get_setting("usdt_rate", USDT_RATE))

# ══════════════════════════════════════════════════════════════════════════════
#  DUAL PRICE ENGINE — Live API + Fallback Default Prices
# ══════════════════════════════════════════════════════════════════════════════
_pc = {}  # price cache

def _get_default_price(cc, api):
    margin = get_margin()
    svc_prices = DEFAULT_PRICES.get(api, {})
    base = svc_prices.get(cc)
    if base:
        sell = math.ceil(base * (margin / MARGIN))
        return sell, DEFAULT_STOCK
    return None, 0

def _smspool_price(cc, api):
    try:
        if not SMSPOOL_KEY: return None, 0
        country = SMSPOOL_CC.get(cc)
        service = SMSPOOL_SVC.get(api)
        if not country or not service: return None, 0
        r = requests.get(
            "https://api.smspool.net/service/price",
            params={"key": SMSPOOL_KEY, "country": country, "service": service},
            timeout=8).json()
        price = float(r.get("price", 0))
        stock = int(r.get("stock", 0))
        if price > 0 and stock > 0:
            margin = get_margin()
            usdt_rate = get_usdt_rate()
            return math.ceil(price * usdt_rate * margin), stock
    except Exception as e:
        logger.warning(f"SmsPool price [{cc}/{api}]: {e}")
    return None, 0

def _vaksms_price(cc, api):
    try:
        if not VAKSMS_KEY: return None, 0
        country = VAKSMS_CC.get(cc)
        service = VAKSMS_SVC.get(api)
        if not country or not service: return None, 0
        r = requests.get(
            "https://vak-sms.com/api/getCountOperator/",
            params={"apiKey": VAKSMS_KEY, "country": country, "service": service},
            timeout=8).json()
        if isinstance(r, list) and r:
            best_price = None; total_stock = 0
            for op in r:
                p = float(op.get("price", 0)); c = int(op.get("count", 0))
                total_stock += c
                if c > 0 and (best_price is None or p < best_price): best_price = p
            if best_price and total_stock > 0:
                margin = get_margin()
                return math.ceil(best_price * margin), total_stock
    except Exception as e:
        logger.warning(f"Vak-SMS price [{cc}/{api}]: {e}")
    return None, 0

def best_price(cc, api):
    """Returns (sell_price, stock, source, sp_stock, vk_stock)"""
    k = f"{cc}|{api}"
    c = _pc.get(k)
    if c and time.time() - c[4] < 1800:
        return c[0], c[1], c[2], c[3][0], c[3][1]

    psp, ssp = _smspool_price(cc, api)
    pvk, svk = _vaksms_price(cc, api)

    res = None
    if psp and ssp > 0 and pvk and svk > 0:
        if psp <= pvk:
            res = (psp, ssp+svk, 'smspool')
        else:
            res = (pvk, ssp+svk, 'vaksms')
    elif psp and ssp > 0:
        res = (psp, ssp, 'smspool')
    elif pvk and svk > 0:
        res = (pvk, svk, 'vaksms')

    if res:
        _pc[k] = (*res, (ssp, svk), time.time())
        return res[0], res[1], res[2], ssp, svk

    dp, ds = _get_default_price(cc, api)
    if dp:
        return dp, ds, 'default', 0, 0

    return None, 0, None, 0, 0

# ══════════════════════════════════════════════════════════════════════════════
#  FIND SERVICE HELPER
# ══════════════════════════════════════════════════════════════════════════════
def find_svc(key):
    for cat, items in SERVICES.items():
        if key in items:
            return items[key], cat
    return None, None

# ══════════════════════════════════════════════════════════════════════════════
#  BUY ENGINE (SmsPool → VakSMS → Default fallback)
# ══════════════════════════════════════════════════════════════════════════════
def smart_buy(cc, api):
    psp, ssp = _smspool_price(cc, api)
    pvk, svk = _vaksms_price(cc, api)
    if psp and ssp > 0:
        oid, num = _smspool_buy(cc, api)
        if oid and num: return oid, num, 'smspool'
    if pvk and svk > 0:
        oid, num = _vaksms_buy(cc, api)
        if oid and num: return oid, num, 'vaksms'
    return None, None, None

def _smspool_buy(cc, api):
    try:
        country = SMSPOOL_CC.get(cc); service = SMSPOOL_SVC.get(api)
        if not country or not service: return None, None
        r = requests.get("https://api.smspool.net/sms/buy",
            params={"key": SMSPOOL_KEY, "country": country, "service": service},
            timeout=15).json()
        if r.get("success") and r.get("number"):
            return r["orderid"], r["number"]
    except Exception as e: logger.error(f"SmsPool buy: {e}")
    return None, None

def _vaksms_buy(cc, api):
    try:
        country = VAKSMS_CC.get(cc); service = VAKSMS_SVC.get(api)
        if not country or not service: return None, None
        r = requests.get("https://vak-sms.com/api/getNum/",
            params={"apiKey": VAKSMS_KEY, "country": country, "service": service},
            timeout=15).json()
        if r.get("tel") and r.get("idNum"):
            return r["idNum"], r["tel"]
    except Exception as e: logger.error(f"VakSMS buy: {e}")
    return None, None

def check_otp(oid, source):
    try:
        if source == 'smspool':
            r = requests.get("https://api.smspool.net/sms/check",
                params={"key": SMSPOOL_KEY, "orderid": oid}, timeout=10).json()
            if r.get("sms"): return r["sms"]
        elif source == 'vaksms':
            r = requests.get("https://vak-sms.com/api/getSmsCode/",
                params={"apiKey": VAKSMS_KEY, "idNum": oid}, timeout=10).json()
            if r.get("smsCode"): return r["smsCode"]
    except Exception as e: logger.error(f"OTP check: {e}")
    return None

def cancel_order(oid, source):
    try:
        if source == 'smspool':
            requests.get("https://api.smspool.net/sms/cancel",
                params={"key": SMSPOOL_KEY, "orderid": oid}, timeout=10)
        elif source == 'vaksms':
            requests.get("https://vak-sms.com/api/setStatus/",
                params={"apiKey": VAKSMS_KEY, "idNum": oid, "status": "end"}, timeout=10)
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  DYNAMIC FORCE CHANNELS
# ══════════════════════════════════════════════════════════════════════════════
def get_force_channels():
    try:
        return list(channels_col.find({"active": True}))
    except: return []

def is_joined(uid):
    ok = ['member', 'administrator', 'creator']
    channels = get_force_channels()
    for ch in channels:
        try:
            if bot.get_chat_member(ch['channel_id'], uid).status not in ok:
                return False
        except: pass
    return True

def join_markup():
    channels = get_force_channels()
    m = types.InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        icon = "📢" if ch.get('type') == 'channel' else "👥"
        m.add(types.InlineKeyboardButton(
            f"{icon} {ch['name']} Join Karein ✅",
            url=ch['link']))
    m.add(types.InlineKeyboardButton(
        "🔄 Join Kiya — Verify Karein", callback_data="check_join"))
    return m

# ══════════════════════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_user(uid, uname=None, fname=None):
    try:
        users_col.find_one_and_update(
            {"user_id": uid},
            {"$setOnInsert": {
                "user_id": uid, "username": uname or "",
                "full_name": fname or "", "balance": 0.0,
                "total_spent": 0.0, "orders": 0,
                "banned": False, "joined_at": datetime.utcnow()
            }},
            upsert=True, return_document=True)
        if uname or fname:
            updates = {}
            if uname: updates["username"] = uname
            if fname: updates["full_name"] = fname
            if updates: users_col.update_one({"user_id": uid}, {"$set": updates})
        return users_col.find_one({"user_id": uid})
    except Exception as e:
        logger.error(f"get_user: {e}")
        return {"user_id": uid, "balance": 0, "total_spent": 0, "orders": 0, "banned": False}

def find_user_by_username(username):
    """Find user by @username (case insensitive)"""
    uname = username.lstrip('@').lower()
    return users_col.find_one({"username": {"$regex": f"^{uname}$", "$options": "i"}})

def is_banned(uid):
    u = users_col.find_one({"user_id": uid})
    return bool(u and u.get("banned"))

def add_balance(uid, amount):
    try:
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": amount}}, upsert=False)
        return True
    except Exception as e:
        logger.error(f"add_balance: {e}"); return False

def deduct_balance(uid, amount):
    try:
        r = users_col.update_one(
            {"user_id": uid, "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount, "orders": 1, "total_spent": amount}})
        return r.modified_count > 0
    except Exception as e:
        logger.error(f"deduct_balance: {e}"); return False

def log_order(uid, cat, svc, num, oid, sell, source):
    try:
        margin = get_margin()
        orders_col.insert_one({
            "user_id": uid, "category": cat,
            "service": f"{svc['flag']} {svc['country']} {cat}",
            "api": svc['api'], "cc": svc['cc'],
            "number": num, "order_id": str(oid),
            "amount": sell, "source": source,
            "profit": round(sell * (1 - 1/margin), 2),
            "status": "pending", "otp": None,
            "created_at": datetime.utcnow()
        })
    except Exception as e: logger.error(f"log_order: {e}")

def log_admin_balance_action(admin_id, uid, amount, action_type, note=""):
    """Audit log for admin balance changes"""
    try:
        admin_log_col.insert_one({
            "admin_id": admin_id,
            "user_id": uid,
            "amount": amount,
            "type": action_type,  # 'add' or 'deduct'
            "note": note,
            "created_at": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"admin_log: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  DECORATORS
# ══════════════════════════════════════════════════════════════════════════════
def ban_check(fn):
    def w(msg):
        if is_banned(msg.from_user.id):
            bot.send_message(msg.chat.id, f"🚫 *Aap ban hain!*\nSupport: {SUPPORT_BOT}"); return
        fn(msg)
    return w

def join_check(fn):
    def w(msg):
        uid = msg.from_user.id
        if uid == OWNER_ID: fn(msg); return
        if get_force_channels() and not is_joined(uid):
            bot.send_message(msg.chat.id,
                "⚠️ *Pehle join karein:*", reply_markup=join_markup()); return
        fn(msg)
    return w

def gaali_check(fn):
    def w(msg):
        if msg.from_user.id == OWNER_ID: fn(msg); return
        if any(x in (msg.text or "").lower() for x in BAD_WORDS):
            uid = msg.from_user.id
            users_col.update_one({"user_id": uid}, {"$set": {"banned": True}})
            bot.send_message(uid, f"🚫 *Block!* Gaali=ban.\nAppeal: {SUPPORT_BOT}")
            try: bot.send_message(OWNER_ID,
                f"⚠️ Auto-Ban\n👤{msg.from_user.first_name}\n🆔`{uid}`\n💬`{msg.text}`")
            except: pass
            return
        fn(msg)
    return w

def oo(fn):
    def w(msg):
        if msg.from_user.id != OWNER_ID: return
        fn(msg)
    return w

# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════════════════════
def main_menu(uid):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("📲 Buy Number", "💰 Wallet")
    m.add("📋 My Orders", "👥 Refer & Earn")
    m.add("📊 Proof", "🆘 Help")
    m.add("📞 Support")
    if uid == OWNER_ID: m.add("⚙️ Admin Panel")
    return m

def buy_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for svc in SERVICES: m.add(svc)
    m.add("🔙 Back")
    return m

def admin_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("📊 Stats", "👥 Users")
    m.add("📋 Pending Dep", "💹 API Balances")
    m.add("🔑 API Keys", "📡 Channels")
    m.add("📢 Broadcast", "🏆 Top Buyers")
    m.add("📦 Orders", "📈 Stock")
    m.add("➕ Platform Add", "💾 Export")
    m.add("📡 Force Ch Manage", "⚙️ Bot Settings")
    m.add("💰 Balance Adjust", "🔍 User Search")
    m.add("📜 Balance Log", "💵 Quick Balance")   # NEW: Quick balance add/deduct
    m.add("📊 Live Price Check")                   # NEW: Live price checker
    m.add("🔙 Back")
    return m

ADMIN_BTNS = {
    "📊 Stats","👥 Users","📋 Pending Dep","💹 API Balances","🔑 API Keys",
    "📡 Channels","📢 Broadcast","🏆 Top Buyers","📦 Orders","📈 Stock",
    "➕ Platform Add","💾 Export","📡 Force Ch Manage","⚙️ Bot Settings",
    "💰 Balance Adjust","🔍 User Search","📜 Balance Log",
    "💵 Quick Balance","📊 Live Price Check",  # NEW
    "🔙 Back","⚙️ Admin Panel",
    "📲 Buy Number","💰 Wallet","📋 My Orders","👥 Refer & Earn",
    "📊 Proof","🆘 Help","📞 Support",
}

# ══════════════════════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    # Referral support
    args = msg.text.split()
    if len(args) > 1:
        try:
            ref_uid = int(args[1])
            if ref_uid != uid:
                users_col.update_one(
                    {"user_id": uid},
                    {"$setOnInsert": {"referred_by": ref_uid}},
                    upsert=True)
        except: pass
    get_user(uid, msg.from_user.username, msg.from_user.first_name)
    if uid != OWNER_ID and get_force_channels() and not is_joined(uid):
        bot.send_message(uid, "⚠️ *OtpKing Bot*\n\nPehle join karein 👇",
            reply_markup=join_markup()); return
    _greet(uid, msg.from_user.first_name or "Dost")

def _greet(uid, name):
    bot.send_message(uid,
        f"👑 *OtpKing Bot*\n"
        f"Welcome *{name}* ji! 🙏\n\n"
        "✅ 10 Services | 50+ Countries\n"
        "💎 USDT + 🇮🇳 UPI Deposit\n\n"
        "👇 Kya karna hai?",
        reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def cb_check_join(call):
    if is_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified!")
        _greet(call.from_user.id, call.from_user.first_name or "Dost")
    else:
        bot.answer_callback_query(call.id,
            "❌ Sabhi channels join nahi kiye!", show_alert=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BUY NUMBER — Live price + stock (dono API ka dikhega)
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📲 Buy Number")
@ban_check
@join_check
def buy_number(msg):
    bot.send_message(msg.chat.id, "📲 *Service chunein:*", reply_markup=buy_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def go_back(msg):
    bot.send_message(msg.chat.id, "🏠", reply_markup=main_menu(msg.from_user.id))

@bot.message_handler(func=lambda m: m.text in ALL_BTNS)
@ban_check
@join_check
def show_countries(msg):
    cat = msg.text; items = SERVICES.get(cat, {})
    lm = bot.send_message(msg.chat.id, f"⏳ *{cat}* — Live prices load ho rahi hain...")
    mk = types.InlineKeyboardMarkup(row_width=1)
    has_available = False

    for key, info in items.items():
        sell, total_stock, src, ssp, svk = best_price(info['cc'], info['api'])

        if sell and total_stock > 0:
            has_available = True
            # Stock indicator
            if total_stock <= LOW_STOCK:
                stock_ic = "🔴"
            elif total_stock <= 20:
                stock_ic = "🟡"
            else:
                stock_ic = "🟢"

            # Source indicator (hidden from users but useful for admin insight)
            # User sees: flag + country + price + stock count
            btn_text = f"{info['flag']} {info['country']}  ·  ₹{sell}  ·  {stock_ic}{total_stock}"
            mk.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{key}"))
        # If no price/stock → skip (don't show button)

    mk.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{cat.replace(' ','_')}"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="go_back_menu"))

    txt = f"*{cat}* — Country & Stock chunein:"
    if not has_available:
        txt = (f"*{cat}*\n\n❌ Abhi koi stock available nahi.\n"
               f"APIs recharge karni hogi ya thodi der baad try karein.")
    try:
        bot.edit_message_text(txt, lm.chat.id, lm.message_id, reply_markup=mk)
    except Exception as e:
        logger.error(f"edit_message: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("refresh_"))
def cb_refresh(call):
    cat_raw = call.data.replace("refresh_", "").replace("_", " ")
    # Find matching service
    matched_cat = None
    for svc_name in SERVICES.keys():
        if svc_name.replace(" ", "_") == call.data.replace("refresh_", "") or svc_name == cat_raw:
            matched_cat = svc_name
            break
    if not matched_cat:
        bot.answer_callback_query(call.id, "❌ Service nahi mili", show_alert=True)
        return
    bot.answer_callback_query(call.id, "⏳ Refreshing...")
    # Clear cache for this service
    items = SERVICES.get(matched_cat, {})
    for key, info in items.items():
        _pc.pop(f"{info['cc']}|{info['api']}", None)
    # Rebuild inline keyboard
    mk = types.InlineKeyboardMarkup(row_width=1)
    has_available = False
    for key, info in items.items():
        sell, total_stock, src, ssp, svk = best_price(info['cc'], info['api'])
        if sell and total_stock > 0:
            has_available = True
            if total_stock <= LOW_STOCK: stock_ic = "🔴"
            elif total_stock <= 20:      stock_ic = "🟡"
            else:                         stock_ic = "🟢"
            btn_text = f"{info['flag']} {info['country']}  ·  ₹{sell}  ·  {stock_ic}{total_stock}"
            mk.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{key}"))
    mk.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=call.data))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="go_back_menu"))
    txt = f"*{matched_cat}* — Country & Stock chunein:"
    if not has_available:
        txt = f"*{matched_cat}*\n\n❌ Abhi koi stock nahi.\nThodi der baad try karein."
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mk)
    except: pass

@bot.callback_query_handler(func=lambda c: c.data == "go_back_menu")
def cb_back(call):
    bot.send_message(call.message.chat.id, "🏠", reply_markup=main_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def cb_buy(call):
    uid = call.from_user.id
    if is_banned(uid): return bot.answer_callback_query(call.id, "🚫 Ban.", show_alert=True)
    if not is_joined(uid) and uid != OWNER_ID and get_force_channels():
        return bot.answer_callback_query(call.id, "⚠️ Pehle join karein!", show_alert=True)
    key = call.data[4:]
    svc, cat = find_svc(key)
    if not svc: return bot.answer_callback_query(call.id, "❌ Invalid.", show_alert=True)
    sell, cnt, src, ssp, svk = best_price(svc['cc'], svc['api'])
    if not sell or cnt == 0:
        return bot.answer_callback_query(call.id,
            "❌ Abhi stock nahi!\nThodi der mein try karein.", show_alert=True)
    u = get_user(uid)
    if u.get('balance', 0) < sell:
        short = sell - u.get('balance', 0)
        return bot.answer_callback_query(call.id,
            f"❌ Balance kam hai!\n"
            f"Chahiye: ₹{sell:.0f}\n"
            f"Hai: ₹{u.get('balance',0):.0f}\n"
            f"Aur chahiye: ₹{short:.0f}\n\n"
            f"💰 Wallet → Deposit karein!", show_alert=True)
    bot.answer_callback_query(call.id, "⏳ Number dhundh rahe hain...")
    sm = bot.send_message(call.message.chat.id,
        f"🔄 *Processing...*\n{svc['flag']} {svc['country']} {cat}\n"
        f"💵 ₹{sell:.0f} balance se katega")
    oid, num, used_src = smart_buy(svc['cc'], svc['api'])
    if oid and num:
        success = deduct_balance(uid, sell)
        if not success:
            cancel_order(str(oid), used_src)
            bot.edit_message_text("❌ Balance deduct failed. Try again.",
                call.message.chat.id, sm.message_id); return
        u2 = users_col.find_one({"user_id": uid}) or {}
        nb = u2.get('balance', 0)
        log_order(uid, cat, svc, num, oid, sell, used_src)
        bot.edit_message_text(
            f"✅ *Number Mila!*\n\n"
            f"📞 `{num}`\n{svc['flag']} {svc['country']} {cat}\n"
            f"💵 ₹{sell:.0f} kata | Remaining: ₹{nb:.0f}\n\n"
            f"⏳ *OTP aa raha hai...* _(max 5 min)_\n"
            f"_Nahi aaya to Auto Refund_",
            call.message.chat.id, sm.message_id)
        Thread(target=_otp_wait,
            args=(call.message.chat.id, uid, str(oid), sell, num, svc, cat, nb, used_src),
            daemon=True).start()
    else:
        bot.edit_message_text(
            f"❌ *Number Nahi Mila*\n\n"
            f"APIs ka balance recharge karna hai.\n"
            f"Admin se contact karein: {SUPPORT_BOT}\n\n"
            f"_Aapka balance safe hai._",
            call.message.chat.id, sm.message_id)

def _otp_wait(cid, uid, oid, refund, num, svc, cat, rbal, source):
    for _ in range(30):
        time.sleep(10)
        otp = check_otp(oid, source)
        if otp:
            orders_col.update_one({"order_id": oid}, {"$set": {"status": "done", "otp": otp}})
            bot.send_message(cid,
                f"🎉 *OTP Aa Gaya!*\n\n"
                f"📞 `{num}`\n{svc['flag']} {svc['country']} {cat}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔑 *OTP Code:* `{otp}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Balance: ₹{rbal:.0f}\n✅ Done! 🙏")
            Thread(target=_post_proof,
                args=(uid, num, svc, cat, refund, otp, source), daemon=True).start()
            return
    cancel_order(oid, source)
    orders_col.update_one({"order_id": oid}, {"$set": {"status": "cancelled"}})
    add_balance(uid, refund)
    bot.send_message(cid,
        f"❌ *OTP Timeout*\n📞 `{num}`\n5 min mein OTP nahi aaya.\n\n"
        f"💰 *₹{refund:.0f} Auto Refund!*")

def _post_proof(uid, num, svc, cat, amt, otp, source):
    u = users_col.find_one({"user_id": uid}) or {}
    name = u.get('full_name') or f"User{str(uid)[-4:]}"
    masked = num[:4] + "****" + num[-2:] if len(num) > 6 else num
    src_n = "SmsPool" if source == 'smspool' else "Vak-SMS"
    text = (f"✅ *OTP Delivered!*\n\n📞 `{masked}`\n"
            f"📍{svc['flag']} {svc['country']} {cat}\n"
            f"💵 ₹{amt:.0f} | 🔗 {src_n}\n🔑 OTP: `{otp}`\n👤{name}\n"
            f"🕐{datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC\n👑 *OtpKing*")
    for dest in [PROOF_CHANNEL_ID, GROUP_ID]:
        try: bot.send_message(dest, text)
        except Exception as e: logger.warning(f"Proof to {dest}: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  WALLET
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "💰 Wallet")
@ban_check
@join_check
def wallet(msg):
    u = get_user(msg.from_user.id)
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("💎 USDT Deposit (Binance TRC20)", callback_data="d_usdt"),
        types.InlineKeyboardButton("🇮🇳 UPI / QR Code Deposit",       callback_data="d_upi"),
        types.InlineKeyboardButton("📊 Transaction History",           callback_data="d_hist"),
    )
    bot.send_message(msg.chat.id,
        f"💳 *Your Wallet*\n\n"
        f"🆔 `{msg.from_user.id}`\n"
        f"💵 Balance: *₹{u.get('balance',0):.0f}*\n"
        f"🛒 Orders: `{u.get('orders',0)}`\n"
        f"💸 Spent: `₹{u.get('total_spent',0):.0f}`\n\n"
        f"👇 Deposit karein:", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "d_usdt")
def cb_usdt(call):
    addr = BINANCE_ADDRESS or "⚠️ Admin ne address set nahi kiya — Contact: " + SUPPORT_BOT
    m = types.InlineKeyboardMarkup(row_width=1)
    if not BINANCE_ADDRESS:
        m.add(types.InlineKeyboardButton("💬 Admin se Address Maangein",
            url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    m.add(types.InlineKeyboardButton("✅ Screenshot Bheja — Submit Karo",
        callback_data="d_proof_usdt"))
    m.add(types.InlineKeyboardButton("🔙 Back", callback_data="d_back"))
    bot.send_message(call.message.chat.id,
        "💎 *USDT Deposit — TRC20 (Binance)*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *Wallet Address:*\n"
        f"`{addr}`\n"
        "_(Tap karke copy karein)_\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Steps:*\n"
        "1️⃣ Upar address copy karein\n"
        "2️⃣ Crypto app kholen\n"
        "3️⃣ *Network: TRC20 ONLY* chunein ⚠️\n"
        "4️⃣ Amount transfer karein\n"
        "5️⃣ Screenshot le ke yahan bhejein 📸\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ ERC20/BEP20 mat bhejein!\n"
        "💡 Min: ₹100 | 1 USDT = ₹85\n"
        "⏱ 10-30 min mein add hoga", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "d_upi")
def cb_upi(call):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton(
        "📲 Step 1 — Admin se QR Code Maangein 👈",
        url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    m.add(types.InlineKeyboardButton(
        "✅ Payment Ho Gayi — Screenshot Bhejein",
        callback_data="d_proof_upi"))
    m.add(types.InlineKeyboardButton("🔙 Back", callback_data="d_back"))
    upi_line = f"\n🆔 UPI ID: `{UPI_ID}`" if UPI_ID else ""
    bot.send_message(call.message.chat.id,
        "🇮🇳 *UPI / QR Code Deposit*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *JARURI: Pehle Admin se QR Maangein!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *Steps:*\n"
        f"1️⃣ Admin se QR Code maangein: {SUPPORT_BOT}{upi_line}\n"
        "2️⃣ Admin QR code bhejega\n"
        "3️⃣ QR scan karke payment karein\n"
        "4️⃣ Screenshot yahan bhejein 📸\n"
        "5️⃣ Admin verify → Balance add!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Min: ₹50 | ⏱ 5-15 min\n"
        "⚠️ Bina QR maange payment mat karein!", reply_markup=m)

_dep_method = {}

@bot.callback_query_handler(func=lambda c: c.data in ["d_proof_usdt","d_proof_upi"])
def cb_set_proof_method(call):
    _dep_method[call.from_user.id] = "USDT" if call.data == "d_proof_usdt" else "UPI"
    bot.answer_callback_query(call.id)
    icon = "💎" if _dep_method[call.from_user.id] == "USDT" else "🇮🇳"
    bot.send_message(call.message.chat.id,
        f"📸 *{icon} Screenshot Bhejein!*\n\n"
        "Is chat mein payment screenshot send karein.\n"
        "_Admin verify karke balance add kar dega._")

@bot.callback_query_handler(func=lambda c: c.data == "d_back")
def cb_dep_back(call):
    u = get_user(call.from_user.id)
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("💎 USDT (Binance TRC20)", callback_data="d_usdt"),
        types.InlineKeyboardButton("🇮🇳 UPI / QR Code",       callback_data="d_upi"),
        types.InlineKeyboardButton("📊 History",               callback_data="d_hist"))
    bot.send_message(call.message.chat.id,
        f"💳 Balance: *₹{u.get('balance',0):.0f}*", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "d_hist")
def cb_hist(call):
    uid = call.from_user.id
    orders = list(orders_col.find({"user_id": uid}).sort("created_at", DESCENDING).limit(8))
    deps   = list(deposits_col.find({"user_id": uid}).sort("created_at", DESCENDING).limit(5))
    t = "📊 *Transaction History*\n\n"
    if deps:
        t += "💰 *Deposits:*\n"
        for d in deps:
            ic = "✅" if d['status'] == "approved" else ("❌" if d['status'] == "rejected" else "⏳")
            t += f"{ic} {d.get('method','?')} ₹{d.get('amount',0):.0f} — {d['created_at'].strftime('%d %b %H:%M')}\n"
        t += "\n"
    if orders:
        t += "🛒 *Orders:*\n"
        for o in orders:
            ic = "✅" if o['status'] == "done" else ("❌" if o['status'] == "cancelled" else "⏳")
            t += f"{ic} {o['service']} ₹{o.get('amount',0):.0f} — {o['created_at'].strftime('%d %b %H:%M')}\n"
    else: t += "📭 Koi order nahi."
    bot.send_message(call.message.chat.id, t)

# ── Screenshot Handler ─────────────────────────────────────────────────────────
@bot.message_handler(content_types=['photo'])
def on_photo(msg):
    if msg.from_user.id == OWNER_ID: return
    uid = msg.from_user.id
    method = _dep_method.pop(uid, "USDT/UPI")
    deposits_col.insert_one({
        "user_id": uid, "username": msg.from_user.username or "",
        "full_name": msg.from_user.first_name or "", "amount": 0.0,
        "status": "pending", "method": method,
        "message_id": msg.message_id, "created_at": datetime.utcnow()
    })
    try: bot.forward_message(OWNER_ID, msg.chat.id, msg.message_id)
    except: pass
    method_icon = "💎" if method == "USDT" else "🇮🇳"
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("✅ ₹100",  callback_data=f"qadd_{uid}_100"),
        types.InlineKeyboardButton("✅ ₹200",  callback_data=f"qadd_{uid}_200"),
        types.InlineKeyboardButton("✅ ₹500",  callback_data=f"qadd_{uid}_500"),
        types.InlineKeyboardButton("✅ ₹1000", callback_data=f"qadd_{uid}_1000"),
        types.InlineKeyboardButton("✅ ₹2000", callback_data=f"qadd_{uid}_2000"),
        types.InlineKeyboardButton("✅ Custom", callback_data=f"qcustom_{uid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"qreject_{uid}"),
    )
    try:
        bot.send_message(OWNER_ID,
            f"📩 *Naya Deposit!*\n\n"
            f"{method_icon} Method: *{method}*\n"
            f"👤 {msg.from_user.first_name} (@{msg.from_user.username or 'N/A'})\n"
            f"🆔 `{uid}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Manual: `/add {uid} AMOUNT`\n"
            f"Reject: `/reject {uid}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 Quick buttons:", reply_markup=mk)
    except Exception as e: logger.error(f"Admin notify: {e}")
    try:
        bot.forward_message(PROOF_CHANNEL_ID, msg.chat.id, msg.message_id)
        bot.send_message(PROOF_CHANNEL_ID,
            f"💰 *Deposit Request*\n{method_icon} {method}\n"
            f"👤 {msg.from_user.first_name}\n⏳ Pending...\n👑 OtpKing")
    except: pass
    bot.reply_to(msg,
        "✅ *Screenshot mila!*\n\n"
        "⏳ Admin verify kar raha hai.\n"
        "_10-30 min mein balance add hoga._\n\n"
        f"📞 Help: {SUPPORT_BOT}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("qadd_"))
def cb_quick_add(call):
    if call.from_user.id != OWNER_ID: return
    try:
        parts = call.data.split("_")
        uid = int(parts[1]); amount = float(parts[2])
        _do_approve(uid, amount, "USDT/UPI", call)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("qreject_"))
def cb_quick_reject(call):
    if call.from_user.id != OWNER_ID: return
    try:
        uid = int(call.data.replace("qreject_", ""))
        deposits_col.update_one(
            {"user_id": uid, "status": "pending"},
            {"$set": {"status": "rejected"}}, sort=[("created_at", -1)])
        bot.send_message(uid,
            f"❌ *Deposit Reject Hua.*\nScreenshot unclear tha.\nRetry: {SUPPORT_BOT}")
        bot.answer_callback_query(call.id, f"❌ Rejected {uid}")
        try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except: pass
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {e}", show_alert=True)

_custom_add_state = {}

@bot.callback_query_handler(func=lambda c: c.data.startswith("qcustom_"))
def cb_quick_custom(call):
    if call.from_user.id != OWNER_ID: return
    uid = int(call.data.replace("qcustom_", ""))
    _custom_add_state[OWNER_ID] = {"uid": uid, "type": "deposit"}
    bot.answer_callback_query(call.id)
    bot.send_message(OWNER_ID,
        f"💬 User `{uid}` ko kitna add karna hai?\n"
        f"Amount bhejein (e.g. `850`)\n"
        f"Cancel: `/cancel`")

def _do_approve(uid, amount, method, call=None):
    success = add_balance(uid, amount)
    if not success:
        if call: bot.answer_callback_query(call.id, f"❌ User {uid} nahi mila!", show_alert=True)
        return
    deposits_col.update_one(
        {"user_id": uid, "status": "pending"},
        {"$set": {"status": "approved", "amount": amount, "method": method}},
        sort=[("created_at", -1)])
    log_admin_balance_action(OWNER_ID, uid, amount, "add", f"deposit:{method}")
    u = users_col.find_one({"user_id": uid}) or {}
    new_bal = u.get('balance', amount)
    icon = "💎" if "usdt" in method.lower() else "🇮🇳"
    bot.send_message(uid,
        f"🎉 *Deposit Approved!*\n\n"
        f"{icon} *{method.upper()}* → ₹{amount:.0f} add!\n\n"
        f"💵 *Naya Balance: ₹{new_bal:.0f}*\n\n"
        f"Ab number khareedein 👇\n📲 *Buy Number* dabayein 🛒")
    try:
        bot.send_message(PROOF_CHANNEL_ID,
            f"✅ *Deposit Approved!*\n{icon} {method} → ₹{amount:.0f}\n"
            f"👤 `{uid}` | Balance: ₹{new_bal:.0f}\n"
            f"🕐 {datetime.utcnow().strftime('%d %b %H:%M')} UTC\n👑 OtpKing")
    except: pass
    if call:
        bot.answer_callback_query(call.id, f"✅ ₹{amount:.0f} added! Bal: ₹{new_bal:.0f}")
        try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except: pass
        bot.send_message(OWNER_ID, f"✅ *Done!* `{uid}` → ₹{amount:.0f}\nBal: ₹{new_bal:.0f}")

# ══════════════════════════════════════════════════════════════════════════════
#  MY ORDERS
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📋 My Orders")
@ban_check
@join_check
def my_orders(msg):
    orders = list(orders_col.find({"user_id": msg.from_user.id})
                  .sort("created_at", DESCENDING).limit(7))
    if not orders:
        bot.send_message(msg.chat.id, "📭 Koi order nahi.\nBuy Number dabayein!"); return
    t = "📋 *Your Orders*\n\n"
    for o in orders:
        ic = "✅" if o['status'] == "done" else ("❌" if o['status'] == "cancelled" else "⏳")
        t += f"{ic} `{o['number']}`\n   {o['service']} ₹{o.get('amount',0):.0f}\n   {o['created_at'].strftime('%d %b %H:%M')}\n\n"
    bot.send_message(msg.chat.id, t)

# ══════════════════════════════════════════════════════════════════════════════
#  REFER & EARN
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "👥 Refer & Earn")
@ban_check
@join_check
def refer(msg):
    platforms = list(platforms_col.find())
    if not platforms:
        bot.send_message(msg.chat.id,
            "👥 *Refer & Earn*\n\n⚠️ Abhi koi platform add nahi hua.\n"
            f"Admin se contact: {SUPPORT_BOT}",
            reply_markup=main_menu(msg.from_user.id)); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for p in platforms:
        mk.add(types.InlineKeyboardButton(
            f"💰 {p['name']}", callback_data=f"earn_plat_{str(p['_id'])}"))
    bot.send_message(msg.chat.id,
        "👥 *Refer & Earn*\n\n👇 Platform chunein:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("earn_plat_"))
def cb_earn_platform(call):
    from bson import ObjectId
    plat_id = call.data.replace("earn_plat_", "")
    try: p = platforms_col.find_one({"_id": ObjectId(plat_id)})
    except: p = None
    if not p:
        bot.answer_callback_query(call.id, "❌ Platform nahi mila!", show_alert=True); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("🔗 Register Karein", url=p['link']))
    if p.get('video'):
        mk.add(types.InlineKeyboardButton("🎥 Video Tutorial", url=p['video']))
    mk.add(types.InlineKeyboardButton("🔙 Wapas List", callback_data="earn_back"))
    bot.send_message(call.message.chat.id,
        f"💰 *{p['name']}*\n\n"
        f"👇 Register karein aur earn karein!\n🔗 {p['link']}\n\n"
        f"_Pura tutorial video mein hai!_", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "earn_back")
def cb_earn_back(call):
    platforms = list(platforms_col.find())
    if not platforms:
        bot.send_message(call.message.chat.id, "📭 Koi platform nahi.",
            reply_markup=main_menu(call.from_user.id)); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for p in platforms:
        mk.add(types.InlineKeyboardButton(
            f"💰 {p['name']}", callback_data=f"earn_plat_{str(p['_id'])}"))
    bot.send_message(call.message.chat.id, "👥 *Refer & Earn*\n\n👇 Platform chunein:", reply_markup=mk)

# ══════════════════════════════════════════════════════════════════════════════
#  PROOF
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📊 Proof")
@ban_check
@join_check
def proof(msg):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📢 Proof Channel", url=PROOF_CHANNEL_LINK))
    mk.add(types.InlineKeyboardButton("👥 Group", url=GROUP_LINK))
    bot.send_message(msg.chat.id,
        "📊 *OtpKing Proof*\n\nHumari successful deliveries dekho! 👇",
        reply_markup=mk)

# ══════════════════════════════════════════════════════════════════════════════
#  HELP & SUPPORT
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "🆘 Help")
@ban_check
@join_check
def help_msg(msg):
    bot.send_message(msg.chat.id,
        "🆘 *OtpKing — Help*\n\n"
        "📲 *Buy Number* → Service select karo → Country select karo → Number milega → OTP aayega!\n\n"
        "💰 *Wallet* → USDT ya UPI se deposit karo\n\n"
        "📋 *My Orders* → Apne orders dekho\n\n"
        "👥 *Refer & Earn* → Earning platforms dekho\n\n"
        "🔑 OTP nahi aaya? → 5 min mein auto-refund ho jaata hai\n\n"
        f"📞 Support: {SUPPORT_BOT}")

@bot.message_handler(func=lambda m: m.text == "📞 Support")
@ban_check
def support(msg):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("💬 Admin se Contact", url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    bot.send_message(msg.chat.id,
        f"📞 *Support*\n\n{SUPPORT_BOT} pe message karein!", reply_markup=mk)

# ══════════════════════════════════════════════════════════════════════════════
#  FORCE CHANNEL MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
_ch_add_state = {}

@bot.message_handler(func=lambda m: m.text == "📡 Force Ch Manage" and m.from_user.id == OWNER_ID)
def ab_force_ch(msg):
    channels = get_force_channels()
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("➕ Channel Add Karein", callback_data="fch_add_channel"))
    mk.add(types.InlineKeyboardButton("➕ Group Add Karein",   callback_data="fch_add_group"))
    for ch in channels:
        icon = "📢" if ch.get('type') == 'channel' else "👥"
        mk.add(types.InlineKeyboardButton(
            f"🗑 Remove: {icon} {ch['name']}",
            callback_data=f"fch_del_{str(ch['_id'])}"))
    if not channels:
        txt = "📡 *Force Channel/Group*\n\nAbhi koi channel add nahi hua."
    else:
        txt = f"📡 *Force Channel/Group*\n\n{len(channels)} channel(s) active hain."
    bot.send_message(msg.chat.id, txt, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ["fch_add_channel","fch_add_group"])
def cb_fch_add(call):
    if call.from_user.id != OWNER_ID: return
    ch_type = "channel" if call.data == "fch_add_channel" else "group"
    _ch_add_state[OWNER_ID] = {"step": 1, "type": ch_type}
    bot.answer_callback_query(call.id)
    icon = "📢" if ch_type == "channel" else "👥"
    bot.send_message(OWNER_ID,
        f"➕ *Naya {icon} {'Channel' if ch_type == 'channel' else 'Group'} Add Karein*\n\n"
        f"*Step 1/3:* {'Channel' if ch_type=='channel' else 'Group'} ka naam?\n"
        f"_Example: OtpKing Official_\n\n/cancel se cancel karein")

@bot.callback_query_handler(func=lambda c: c.data.startswith("fch_del_"))
def cb_fch_del(call):
    if call.from_user.id != OWNER_ID: return
    from bson import ObjectId
    ch_id = call.data.replace("fch_del_", "")
    try:
        ch = channels_col.find_one({"_id": ObjectId(ch_id)})
        channels_col.delete_one({"_id": ObjectId(ch_id)})
        bot.answer_callback_query(call.id, f"✅ {ch['name'] if ch else 'Channel'} removed!")
        bot.send_message(OWNER_ID,
            f"✅ *Channel Remove Ho Gaya!*\n\n"
            f"{'📢' if ch and ch.get('type')=='channel' else '👥'} {ch['name'] if ch else 'Unknown'}\n\n"
            f"Ab users ko yeh join karna zaroori nahi hoga.")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {e}", show_alert=True)

@bot.message_handler(func=lambda m: (
    m.from_user.id == OWNER_ID
    and OWNER_ID in _ch_add_state
    and _ch_add_state.get(OWNER_ID, {}).get("step", 0) > 0
    and m.text not in ADMIN_BTNS
))
def handle_ch_add_steps(msg):
    if msg.text and msg.text.startswith('/'): return
    state = _ch_add_state.get(OWNER_ID, {})
    step = state.get("step", 0)
    ch_type = state.get("type", "channel")
    icon = "📢" if ch_type == "channel" else "👥"
    if step == 1:
        state["name"] = msg.text.strip(); state["step"] = 2
        _ch_add_state[OWNER_ID] = state
        bot.send_message(msg.chat.id,
            f"✅ Naam: *{state['name']}*\n\n"
            f"*Step 2/3:* {icon} {'Channel' if ch_type=='channel' else 'Group'} ka ID bhejein\n"
            f"_Example: @OtpKingOfficial ya -1001234567890_")
    elif step == 2:
        cid = msg.text.strip()
        state["channel_id"] = cid; state["step"] = 3
        _ch_add_state[OWNER_ID] = state
        bot.send_message(msg.chat.id,
            f"✅ ID: `{cid}`\n\n"
            f"*Step 3/3:* {icon} Invite link bhejein\n"
            f"_Example: https://t.me/OtpKingOfficial_")
    elif step == 3:
        link = msg.text.strip()
        if not link.startswith("http"):
            bot.send_message(msg.chat.id, "❌ Valid link chahiye (https:// se shuru ho)"); return
        state_data = _ch_add_state.pop(OWNER_ID, {})
        try:
            channels_col.update_one(
                {"channel_id": state_data["channel_id"]},
                {"$set": {
                    "channel_id": state_data["channel_id"],
                    "name": state_data["name"],
                    "link": link,
                    "type": state_data["type"],
                    "active": True,
                    "added_at": datetime.utcnow()
                }},
                upsert=True)
            icon_str = "📢" if state_data['type'] == 'channel' else "👥"
            bot.send_message(msg.chat.id,
                f"✅ *{icon_str} Add Ho Gaya!*\n\n"
                f"📛 Naam: *{state_data['name']}*\n"
                f"🆔 ID: `{state_data['channel_id']}`\n"
                f"🔗 Link: {link}\n\n"
                f"_Ab users ko yeh join karna zaroori hoga!_ 🎉\n\n"
                f"⚠️ Bot ko is channel/group ka Admin banana na bhoolein!")
        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  BOT SETTINGS (Margin, USDT Rate)
# ══════════════════════════════════════════════════════════════════════════════
_settings_state = {}

@bot.message_handler(func=lambda m: m.text == "⚙️ Bot Settings" and m.from_user.id == OWNER_ID)
def ab_bot_settings(msg):
    margin = get_margin()
    usdt_rate = get_usdt_rate()
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton(f"📈 Margin Set ({int((margin-1)*100)}%)", callback_data="set_margin"),
        types.InlineKeyboardButton(f"💱 USDT Rate Set (₹{usdt_rate})", callback_data="set_usdt_rate"),
        types.InlineKeyboardButton(f"🗑 Price Cache Clear", callback_data="set_clear_cache"),
    )
    bot.send_message(msg.chat.id,
        f"⚙️ *Bot Settings*\n\n"
        f"📈 Current Margin: *{int((margin-1)*100)}%*\n"
        f"💱 USDT Rate: *₹{usdt_rate}*\n\n"
        f"_Change karne ke liye tap karein:_", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ["set_margin","set_usdt_rate","set_clear_cache"])
def cb_settings(call):
    if call.from_user.id != OWNER_ID: return
    if call.data == "set_clear_cache":
        _pc.clear()
        bot.answer_callback_query(call.id, "✅ Price cache cleared!")
        bot.send_message(OWNER_ID, "✅ *Price cache cleared!*\nAb fresh prices fetch honge.")
    elif call.data == "set_margin":
        _settings_state[OWNER_ID] = "margin"
        bot.answer_callback_query(call.id)
        margin = get_margin()
        bot.send_message(OWNER_ID,
            f"📈 *Margin Set Karein*\n\nCurrent: *{int((margin-1)*100)}%*\n\n"
            f"Naya percentage bhejein (e.g. `40` for 40%)\nRange: 10% - 200%\n/cancel se cancel")
    elif call.data == "set_usdt_rate":
        _settings_state[OWNER_ID] = "usdt_rate"
        bot.answer_callback_query(call.id)
        rate = get_usdt_rate()
        bot.send_message(OWNER_ID,
            f"💱 *USDT Rate Set Karein*\n\nCurrent: *₹{rate}*\n\nNaya rate bhejein (e.g. `87.5`)\n/cancel se cancel")

# ══════════════════════════════════════════════════════════════════════════════
#  ★★★ NEW: ADMIN BALANCE ADJUST ★★★
#  Admin kisi bhi user ka balance add/deduct kar sakta hai
#  Galti se add hua to deduct bhi ho sakta hai
# ══════════════════════════════════════════════════════════════════════════════
_bal_adjust_state = {}  # {OWNER_ID: {uid, step, action}}
_user_search_state = {}  # {OWNER_ID: True}

@bot.message_handler(func=lambda m: m.text == "💰 Balance Adjust" and m.from_user.id == OWNER_ID)
def ab_balance_adjust(msg):
    bot.send_message(msg.chat.id,
        "💰 *Balance Adjust*\n\n"
        "User ka ID ya @username bhejein:\n\n"
        "_Example: `12345678` ya `@username`_\n\n"
        "/cancel se cancel karein")
    _bal_adjust_state[OWNER_ID] = {"step": "uid"}

@bot.message_handler(func=lambda m: m.text == "🔍 User Search" and m.from_user.id == OWNER_ID)
def ab_user_search(msg):
    bot.send_message(msg.chat.id,
        "🔍 *User Search*\n\n"
        "User ID ya @username bhejein:\n"
        "_Example: `12345678` ya `@username`_\n\n"
        "/cancel se cancel karein")
    _user_search_state[OWNER_ID] = True

@bot.message_handler(func=lambda m: m.text == "📜 Balance Log" and m.from_user.id == OWNER_ID)
def ab_balance_log(msg):
    logs = list(admin_log_col.find().sort("created_at", DESCENDING).limit(15))
    if not logs:
        bot.send_message(msg.chat.id, "📭 Koi balance log nahi."); return
    t = "📜 *Recent Balance Actions*\n\n"
    for l in logs:
        action_icon = "✅➕" if l['type'] == 'add' else "❌➖"
        t += (f"{action_icon} User `{l['user_id']}` — ₹{l.get('amount',0):.0f}\n"
              f"📝 {l.get('note','manual')}\n"
              f"🕐 {l['created_at'].strftime('%d %b %H:%M')}\n\n")
    bot.send_message(msg.chat.id, t)

def _show_user_for_adjust(cid, u):
    """Show user info with balance add/deduct buttons — minimum ₹100"""
    uid = u['user_id']
    orders_cnt = orders_col.count_documents({"user_id": uid, "status": "done"})
    mk = types.InlineKeyboardMarkup(row_width=3)
    mk.add(
        types.InlineKeyboardButton("➕ ₹100",  callback_data=f"badj_add_{uid}_100"),
        types.InlineKeyboardButton("➕ ₹200",  callback_data=f"badj_add_{uid}_200"),
        types.InlineKeyboardButton("➕ ₹500",  callback_data=f"badj_add_{uid}_500"),
        types.InlineKeyboardButton("➕ ₹1000", callback_data=f"badj_add_{uid}_1000"),
        types.InlineKeyboardButton("➕ ₹2000", callback_data=f"badj_add_{uid}_2000"),
        types.InlineKeyboardButton("➕ Custom", callback_data=f"badj_add_{uid}_custom"),
    )
    mk.add(
        types.InlineKeyboardButton("➖ ₹100",  callback_data=f"badj_ded_{uid}_100"),
        types.InlineKeyboardButton("➖ ₹200",  callback_data=f"badj_ded_{uid}_200"),
        types.InlineKeyboardButton("➖ ₹500",  callback_data=f"badj_ded_{uid}_500"),
        types.InlineKeyboardButton("➖ ₹1000", callback_data=f"badj_ded_{uid}_1000"),
        types.InlineKeyboardButton("➖ ₹2000", callback_data=f"badj_ded_{uid}_2000"),
        types.InlineKeyboardButton("➖ Custom", callback_data=f"badj_ded_{uid}_custom"),
    )
    mk.add(
        types.InlineKeyboardButton("🔄 Balance Set (Exact)", callback_data=f"badj_set_{uid}"),
        types.InlineKeyboardButton("🚫 Ban/Unban",           callback_data=f"badj_ban_{uid}"),
    )
    ban_status = "🚫 BANNED" if u.get('banned') else "✅ Active"
    bot.send_message(cid,
        f"👤 *User Details*\n\n"
        f"🆔 `{uid}`\n"
        f"📛 {u.get('full_name','N/A')} @{u.get('username','N/A')}\n"
        f"💵 Balance: *₹{u.get('balance',0):.0f}*\n"
        f"🛒 Orders (done): `{orders_cnt}`\n"
        f"💸 Total Spent: `₹{u.get('total_spent',0):.0f}`\n"
        f"📅 Joined: {u.get('joined_at', datetime.utcnow()).strftime('%d %b %Y')}\n"
        f"Status: {ban_status}\n\n"
        f"⚠️ Minimum: *₹100* | 👇 Balance adjust karein:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("badj_"))
def cb_balance_adjust(call):
    if call.from_user.id != OWNER_ID: return
    parts = call.data.split("_")
    # badj_add_UID_AMOUNT or badj_ded_UID_AMOUNT or badj_set_UID or badj_ban_UID
    action = parts[1]  # add / ded / set / ban

    if action == "ban":
        uid = int(parts[2])
        u = users_col.find_one({"user_id": uid}) or {}
        new_ban = not u.get("banned", False)
        users_col.update_one({"user_id": uid}, {"$set": {"banned": new_ban}})
        status = "🚫 BANNED" if new_ban else "✅ Unbanned"
        bot.answer_callback_query(call.id, f"{status}")
        bot.send_message(OWNER_ID, f"{status} User `{uid}`")
        try:
            if new_ban:
                bot.send_message(uid, f"🚫 *Aap ban kar diye gaye hain.*\nSupport: {SUPPORT_BOT}")
            else:
                bot.send_message(uid, "✅ *Aapka ban hata diya gaya hai!*\nBot use kar sakte hain.")
        except: pass
        return

    if action == "set":
        uid = int(parts[2])
        _bal_adjust_state[OWNER_ID] = {"step": "amount", "action": "set", "uid": uid}
        bot.answer_callback_query(call.id)
        u = users_col.find_one({"user_id": uid}) or {}
        bot.send_message(OWNER_ID,
            f"🔄 *Balance SET Karein*\n"
            f"User `{uid}` — Current: ₹{u.get('balance',0):.0f}\n\n"
            f"Naya exact balance bhejein (e.g. `500`)\n/cancel se cancel")
        return

    uid = int(parts[2])
    amount_str = parts[3]

    if amount_str == "custom":
        action_name = "add" if action == "add" else "deduct"
        _bal_adjust_state[OWNER_ID] = {"step": "amount", "action": action_name, "uid": uid}
        bot.answer_callback_query(call.id)
        u = users_col.find_one({"user_id": uid}) or {}
        bot.send_message(OWNER_ID,
            f"💬 User `{uid}` — Balance: ₹{u.get('balance',0):.0f}\n"
            f"Kitna {'add' if action=='add' else 'deduct'} karna hai? Amount bhejein:\n/cancel")
        return

    amount = float(amount_str)
    u_before = users_col.find_one({"user_id": uid}) or {}
    bal_before = u_before.get('balance', 0)

    if action == "add":
        add_balance(uid, amount)
        log_admin_balance_action(OWNER_ID, uid, amount, "add", "manual_admin_panel")
        u_after = users_col.find_one({"user_id": uid}) or {}
        bot.answer_callback_query(call.id, f"✅ ₹{amount:.0f} add kiya!")
        bot.send_message(OWNER_ID,
            f"✅ *Balance Add Done!*\n"
            f"👤 `{uid}`\n"
            f"Before: ₹{bal_before:.0f} → After: ₹{u_after.get('balance',0):.0f}\n"
            f"Added: ₹{amount:.0f}")
        try: bot.send_message(uid, f"✅ *₹{amount:.0f} Balance Add Hua!*\n\nNaya Balance: ₹{u_after.get('balance',0):.0f}")
        except: pass
    elif action == "ded":
        add_balance(uid, -amount)
        log_admin_balance_action(OWNER_ID, uid, amount, "deduct", "manual_admin_panel")
        u_after = users_col.find_one({"user_id": uid}) or {}
        bot.answer_callback_query(call.id, f"✅ ₹{amount:.0f} deduct kiya!")
        bot.send_message(OWNER_ID,
            f"✅ *Balance Deduct Done!*\n"
            f"👤 `{uid}`\n"
            f"Before: ₹{bal_before:.0f} → After: ₹{u_after.get('balance',0):.0f}\n"
            f"Deducted: ₹{amount:.0f}")
        try: bot.send_message(uid, f"❕ *₹{amount:.0f} Balance Adjust Hua.*\nNaya Balance: ₹{u_after.get('balance',0):.0f}")
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  PLATFORM ADD STEPS
# ══════════════════════════════════════════════════════════════════════════════
_add_plat_state = {}

@bot.message_handler(commands=['add_platform'])
@oo
def cmd_add_platform(msg):
    _add_plat_state[OWNER_ID] = {"step": 1}
    bot.send_message(msg.chat.id,
        "➕ *Naya Earning Platform Add Karein*\n\n"
        "*Step 1/3:* Platform ka naam?\n/cancel se cancel")

@bot.message_handler(commands=['cancel'])
@oo
def cmd_cancel(msg):
    _add_plat_state.pop(OWNER_ID, None)
    _custom_add_state.pop(OWNER_ID, None)
    _ch_add_state.pop(OWNER_ID, None)
    _settings_state.pop(OWNER_ID, None)
    _bal_adjust_state.pop(OWNER_ID, None)
    _user_search_state.pop(OWNER_ID, None)
    _quick_bal_state.pop(OWNER_ID, None)
    bot.reply_to(msg, "✅ Cancel ho gaya.")

@bot.message_handler(commands=['cancel_add'])
@oo
def cmd_cancel_add(msg):
    _custom_add_state.pop(OWNER_ID, None)
    bot.reply_to(msg, "✅ Cancel ho gaya.")

# ══════════════════════════════════════════════════════════════════════════════
#  UNIFIED ADMIN TEXT HANDLER (all multi-step flows)
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: (
    m.from_user.id == OWNER_ID
    and m.text not in ADMIN_BTNS
    and not (m.text or "").startswith('/')
    and (
        (OWNER_ID in _add_plat_state and _add_plat_state.get(OWNER_ID, {}).get("step", 0) > 0)
        or (OWNER_ID in _ch_add_state and _ch_add_state.get(OWNER_ID, {}).get("step", 0) > 0)
        or OWNER_ID in _custom_add_state
        or OWNER_ID in _settings_state
        or OWNER_ID in _bal_adjust_state
        or OWNER_ID in _user_search_state
        or OWNER_ID in _quick_bal_state
    )
))
def handle_admin_text_states(msg):
    txt = (msg.text or "").strip()

    # 1. User search
    if OWNER_ID in _user_search_state:
        _user_search_state.pop(OWNER_ID, None)
        if txt.startswith('@'):
            u = find_user_by_username(txt)
        else:
            try: u = users_col.find_one({"user_id": int(txt)})
            except: u = None
        if not u:
            bot.send_message(msg.chat.id, f"❌ User `{txt}` nahi mila.")
            return
        _show_user_for_adjust(msg.chat.id, u)
        return

    # 2. Balance adjust — find user by ID/username
    if OWNER_ID in _bal_adjust_state:
        state = _bal_adjust_state[OWNER_ID]

        if state.get("step") == "uid":
            # Get user
            if txt.startswith('@'):
                u = find_user_by_username(txt)
            else:
                try: u = users_col.find_one({"user_id": int(txt)})
                except: u = None
            if not u:
                bot.send_message(msg.chat.id, f"❌ User `{txt}` nahi mila."); return
            _bal_adjust_state.pop(OWNER_ID, None)
            _show_user_for_adjust(msg.chat.id, u)
            return

        elif state.get("step") == "amount":
            uid = state["uid"]
            action = state["action"]
            try:
                amount = float(txt)
            except:
                bot.send_message(msg.chat.id, "❌ Sirf number bhejein! (e.g. `500`)"); return
            _bal_adjust_state.pop(OWNER_ID, None)
            u_before = users_col.find_one({"user_id": uid}) or {}
            bal_before = u_before.get('balance', 0)

            if action == "add":
                add_balance(uid, amount)
                log_admin_balance_action(OWNER_ID, uid, amount, "add", "custom_admin")
                u_after = users_col.find_one({"user_id": uid}) or {}
                bot.send_message(msg.chat.id,
                    f"✅ *Balance Add Done!*\n"
                    f"👤 `{uid}`\n"
                    f"Before: ₹{bal_before:.0f} → After: ₹{u_after.get('balance',0):.0f}\n"
                    f"Added: ₹{amount:.0f}")
                try: bot.send_message(uid, f"✅ *₹{amount:.0f} Balance Add Hua!*\nNaya Balance: ₹{u_after.get('balance',0):.0f}")
                except: pass

            elif action == "deduct":
                add_balance(uid, -amount)
                log_admin_balance_action(OWNER_ID, uid, amount, "deduct", "custom_admin")
                u_after = users_col.find_one({"user_id": uid}) or {}
                bot.send_message(msg.chat.id,
                    f"✅ *Balance Deduct Done!*\n"
                    f"👤 `{uid}`\n"
                    f"Before: ₹{bal_before:.0f} → After: ₹{u_after.get('balance',0):.0f}\n"
                    f"Deducted: ₹{amount:.0f}")
                try: bot.send_message(uid, f"❕ ₹{amount:.0f} balance deduct hua.\nNaya Balance: ₹{u_after.get('balance',0):.0f}")
                except: pass

            elif action == "set":
                # Set exact balance
                users_col.update_one({"user_id": uid}, {"$set": {"balance": amount}})
                log_admin_balance_action(OWNER_ID, uid, amount, "set", "exact_set_admin")
                bot.send_message(msg.chat.id,
                    f"✅ *Balance SET Done!*\n"
                    f"👤 `{uid}`\n"
                    f"Before: ₹{bal_before:.0f} → After: ₹{amount:.0f}")
                try: bot.send_message(uid, f"✅ Balance update hua!\nNaya Balance: ₹{amount:.0f}")
                except: pass
            return

    # 3. Platform add steps
    if OWNER_ID in _add_plat_state and _add_plat_state.get(OWNER_ID, {}).get("step", 0) > 0:
        state = _add_plat_state[OWNER_ID]
        step = state.get("step", 0)
        if step == 1:
            state["name"] = txt; state["step"] = 2
            bot.send_message(msg.chat.id,
                f"✅ Naam: *{txt}*\n\n*Step 2/3:* Registration link bhejein:")
        elif step == 2:
            if not txt.startswith("http"):
                bot.send_message(msg.chat.id, "❌ Valid URL chahiye"); return
            state["link"] = txt; state["step"] = 3
            bot.send_message(msg.chat.id,
                f"✅ Link: {txt}\n\n*Step 3/3:* Video tutorial link? (Skip: `/skip`)")
        elif step == 3:
            video = txt if txt.startswith("http") else None
            state_data = _add_plat_state.pop(OWNER_ID, {})
            platforms_col.insert_one({
                "name": state_data["name"],
                "link": state_data["link"],
                "video": video,
                "added_at": datetime.utcnow()
            })
            bot.send_message(msg.chat.id,
                f"✅ *Platform Add Ho Gaya!*\n\n"
                f"📛 {state_data['name']}\n🔗 {state_data['link']}\n"
                f"🎥 {video or 'No video'}")
        return

    # 4. Channel add
    if OWNER_ID in _ch_add_state and _ch_add_state.get(OWNER_ID, {}).get("step", 0) > 0:
        handle_ch_add_steps(msg); return

    # 5. Custom deposit add
    if OWNER_ID in _custom_add_state:
        state = _custom_add_state.pop(OWNER_ID)
        uid = state["uid"] if isinstance(state, dict) else state
        try:
            amount = float(txt.split()[0])
            method = "USDT" if "usdt" in txt.lower() else "UPI"
            _do_approve(uid, amount, method)
            u = users_col.find_one({"user_id": uid}) or {}
            bot.send_message(msg.chat.id,
                f"✅ ₹{amount:.0f} added to `{uid}`\nNew balance: ₹{u.get('balance',0):.0f}")
        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Error: {e}")
        return

    # 6. Settings
    if OWNER_ID in _settings_state:
        setting = _settings_state.pop(OWNER_ID)
        if setting == "margin":
            try:
                val = float(txt)
                if not (10 <= val <= 200):
                    bot.send_message(msg.chat.id, "❌ Range: 10-200%"); return
                new_margin = 1 + val/100
                set_setting("margin", new_margin)
                _pc.clear()
                bot.send_message(msg.chat.id,
                    f"✅ *Margin updated!*\n{val}% | Cache cleared!\n"
                    f"Ab users ko naye prices dikhenge.")
            except: bot.send_message(msg.chat.id, "❌ Sirf number bhejein!")
        elif setting == "usdt_rate":
            try:
                val = float(txt)
                if not (50 <= val <= 200):
                    bot.send_message(msg.chat.id, "❌ Range: 50-200"); return
                set_setting("usdt_rate", val)
                _pc.clear()
                bot.send_message(msg.chat.id,
                    f"✅ *USDT Rate updated!*\n₹{val} | Cache cleared!")
            except: bot.send_message(msg.chat.id, "❌ Sirf number bhejein!")

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN COMMANDS
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(commands=['add'])
@oo
def cmd_add(msg):
    try:
        parts = msg.text.split()
        uid = int(parts[1]); amount = float(parts[2])
        method = parts[3].upper() if len(parts) > 3 else "MANUAL"
        _do_approve(uid, amount, method)
        u = users_col.find_one({"user_id": uid}) or {}
        bot.reply_to(msg,
            f"✅ ₹{amount:.0f} added to `{uid}` ({method})\n"
            f"New balance: ₹{u.get('balance',0):.0f}")
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}\n\nFormat: `/add USER_ID AMOUNT`")

@bot.message_handler(commands=['deduct'])
@oo
def cmd_deduct(msg):
    try:
        _, uid_s, amt_s = msg.text.split()
        uid = int(uid_s); amount = float(amt_s)
        u_before = users_col.find_one({"user_id": uid}) or {}
        bal_before = u_before.get('balance', 0)
        add_balance(uid, -amount)
        log_admin_balance_action(OWNER_ID, uid, amount, "deduct", "cmd_deduct")
        u_after = users_col.find_one({"user_id": uid}) or {}
        bot.reply_to(msg,
            f"✅ ₹{amount:.0f} deducted from `{uid}`\n"
            f"Before: ₹{bal_before:.0f} → After: ₹{u_after.get('balance',0):.0f}")
        try: bot.send_message(uid, f"❕ ₹{amount:.0f} balance adjust hua. Naya Balance: ₹{u_after.get('balance',0):.0f}")
        except: pass
    except:
        bot.reply_to(msg, "❌ Format: `/deduct USER_ID AMOUNT`")

@bot.message_handler(commands=['setbal'])
@oo
def cmd_setbal(msg):
    """Exact balance set karo"""
    try:
        parts = msg.text.split()
        uid = int(parts[1]); amount = float(parts[2])
        u_before = users_col.find_one({"user_id": uid}) or {}
        bal_before = u_before.get('balance', 0)
        users_col.update_one({"user_id": uid}, {"$set": {"balance": amount}})
        log_admin_balance_action(OWNER_ID, uid, amount, "set", "cmd_setbal")
        bot.reply_to(msg,
            f"✅ Balance SET!\n`{uid}`: ₹{bal_before:.0f} → ₹{amount:.0f}")
    except:
        bot.reply_to(msg, "❌ Format: `/setbal USER_ID AMOUNT`")

@bot.message_handler(commands=['reject'])
@oo
def cmd_reject(msg):
    try:
        uid = int(msg.text.split()[1])
        deposits_col.update_one(
            {"user_id": uid, "status": "pending"},
            {"$set": {"status": "rejected"}}, sort=[("created_at", -1)])
        bot.send_message(uid, f"❌ *Deposit Reject Hua.*\nScreenshot unclear tha.\nRetry: {SUPPORT_BOT}")
        bot.reply_to(msg, f"✅ Rejected `{uid}`")
    except: bot.reply_to(msg, "❌ `/reject USER_ID`")

@bot.message_handler(commands=['ban'])
@oo
def cmd_ban(msg):
    try:
        uid = int(msg.text.split()[1])
        users_col.update_one({"user_id": uid}, {"$set": {"banned": True}})
        try: bot.send_message(uid, f"🚫 Ban. Appeal: {SUPPORT_BOT}")
        except: pass
        bot.reply_to(msg, f"🚫 `{uid}` banned.")
    except: bot.reply_to(msg, "❌ `/ban USER_ID`")

@bot.message_handler(commands=['unban'])
@oo
def cmd_unban(msg):
    try:
        uid = int(msg.text.split()[1])
        users_col.update_one({"user_id": uid}, {"$set": {"banned": False}})
        try: bot.send_message(uid, "✅ Ban hata diya.")
        except: pass
        bot.reply_to(msg, f"✅ `{uid}` unbanned.")
    except: bot.reply_to(msg, "❌ `/unban USER_ID`")

@bot.message_handler(commands=['broadcast'])
@oo
def cmd_bc(msg):
    t = msg.text.replace('/broadcast','',1).strip()
    if not t: bot.reply_to(msg, "❌ `/broadcast MSG`"); return
    _do_broadcast(msg.chat.id, t)

@bot.message_handler(commands=['stats'])
@oo
def cmd_stats(msg): _send_stats(msg.chat.id)

@bot.message_handler(commands=['userinfo'])
@oo
def cmd_uinfo(msg):
    try:
        arg = msg.text.split()[1]
        if arg.startswith('@'):
            u = find_user_by_username(arg)
        else:
            u = users_col.find_one({"user_id": int(arg)})
        if not u: bot.reply_to(msg, "❌ User nahi mila."); return
        _show_user_for_adjust(msg.chat.id, u)
    except: bot.reply_to(msg, "❌ `/userinfo USER_ID` ya `/userinfo @username`")

@bot.message_handler(commands=['balance'])
@oo
def cmd_check_bal(msg):
    try:
        arg = msg.text.split()[1]
        if arg.startswith('@'):
            u = find_user_by_username(arg)
        else:
            u = users_col.find_one({"user_id": int(arg)})
        if not u: bot.reply_to(msg, "❌ User nahi mila."); return
        bot.reply_to(msg,
            f"👤 `{u['user_id']}` @{u.get('username','N/A')}\n"
            f"💵 Balance: ₹{u.get('balance',0):.0f}\n"
            f"🛒 Orders: {u.get('orders',0)}")
    except: bot.reply_to(msg, "❌ `/balance USER_ID` ya `/balance @username`")

@bot.message_handler(commands=['skip'])
@oo
def cmd_skip(msg):
    if OWNER_ID in _add_plat_state:
        state = _add_plat_state.get(OWNER_ID, {})
        if state.get("step") == 3:
            state_data = _add_plat_state.pop(OWNER_ID, {})
            platforms_col.insert_one({
                "name": state_data["name"],
                "link": state_data["link"],
                "video": None,
                "added_at": datetime.utcnow()
            })
            bot.send_message(msg.chat.id,
                f"✅ Platform add ho gaya! (No video)\n📛 {state_data['name']}")

@bot.message_handler(commands=['list_platforms'])
@oo
def cmd_list_platforms(msg):
    platforms = list(platforms_col.find())
    if not platforms: bot.send_message(msg.chat.id, "📭 Koi platform nahi."); return
    t = "📋 *Earning Platforms*\n\n"
    for i, p in enumerate(platforms, 1):
        t += f"{i}. *{p['name']}*\n🔗 {p['link']}\n🎥 {p.get('video','N/A')}\n🗑 `/del_plat_{str(p['_id'])}`\n\n"
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.text and m.text.startswith('/del_plat_'))
def cmd_del_platform(msg):
    from bson import ObjectId
    try:
        platforms_col.delete_one({"_id": ObjectId(msg.text.replace('/del_plat_','').strip())})
        bot.reply_to(msg, "✅ Platform delete ho gaya.")
    except Exception as e: bot.reply_to(msg, f"❌ Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN PANEL BUTTONS
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel")
def admin_panel(msg):
    if msg.from_user.id != OWNER_ID: return
    bot.send_message(msg.chat.id, "⚙️ *Admin Panel*", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📊 Stats" and m.from_user.id == OWNER_ID)
def ab_stats(msg): _send_stats(msg.chat.id)

@bot.message_handler(func=lambda m: m.text == "👥 Users" and m.from_user.id == OWNER_ID)
def ab_users(msg):
    tu = users_col.count_documents({})
    ac = users_col.count_documents({"orders": {"$gt": 0}})
    bn = users_col.count_documents({"banned": True})
    # Show recent users
    recent = list(users_col.find().sort("joined_at", DESCENDING).limit(5))
    t = f"👥 *Users*\nTotal: `{tu}` | Active: `{ac}` | Banned: `{bn}`\n\n*Recent:*\n"
    for u in recent:
        t += f"• `{u['user_id']}` {u.get('full_name','?')} ₹{u.get('balance',0):.0f}\n"
    t += f"\n🔍 User details: `/userinfo USER_ID`"
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "📋 Pending Dep" and m.from_user.id == OWNER_ID)
def ab_pending(msg):
    pds = list(deposits_col.find({"status":"pending"}).sort("created_at",DESCENDING).limit(10))
    if not pds: bot.send_message(msg.chat.id, "📭 Koi pending nahi."); return
    t = "📋 *Pending Deposits*\n\n"
    for d in pds:
        t += (f"👤 {d.get('full_name','?')} @{d.get('username','?')}\n"
              f"🆔 `{d['user_id']}` | {d.get('method','?')}\n"
              f"🕐 {d['created_at'].strftime('%d %b %H:%M')}\n"
              f"✅ `/add {d['user_id']} AMOUNT`  ❌ `/reject {d['user_id']}`\n\n")
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "💹 API Balances" and m.from_user.id == OWNER_ID)
def ab_api_bal(msg):
    results = []
    try:
        r = requests.get(f"https://api.smspool.net/request/balance?key={SMSPOOL_KEY}",timeout=8).json()
        bal = r.get('balance','?')
        warn = " ⚠️ RECHARGE!" if float(str(bal).replace('$','').strip() or 0) < 1 else ""
        results.append(f"{'✅' if not warn else '❌'} SmsPool: ${bal}{warn}")
    except Exception as e: results.append(f"❌ SmsPool: {str(e)[:30]}")
    try:
        r = requests.get(f"https://vak-sms.com/api/getBalance/?apiKey={VAKSMS_KEY}",timeout=8).json()
        bal = r.get('balance','?')
        warn = " ⚠️ RECHARGE!" if float(str(bal).strip() or 0) < 1 else ""
        results.append(f"{'✅' if not warn else '❌'} Vak-SMS: ₽{bal}{warn}")
    except Exception as e: results.append(f"❌ Vak-SMS: {str(e)[:30]}")
    margin = get_margin(); rate = get_usdt_rate()
    bot.send_message(msg.chat.id,
        "💹 *API Balances*\n\n" + "\n".join(results) +
        f"\n\n📈 Margin: {int((margin-1)*100)}%\n💱 USDT Rate: ₹{rate}\n\n"
        f"ℹ️ Balance 0 par bhi default prices dikhenge\n"
        f"Actual buy ke liye balance recharge karein!")

@bot.message_handler(func=lambda m: m.text == "🔑 API Keys" and m.from_user.id == OWNER_ID)
def ab_keys(msg):
    results = [
        f"{'✅' if SMSPOOL_KEY else '❌'} SMSPOOL_API_KEY: {'Set ✅' if SMSPOOL_KEY else 'NOT SET ❌'}",
        f"{'✅' if VAKSMS_KEY else '❌'} VAKSMS_API_KEY: {'Set ✅' if VAKSMS_KEY else 'NOT SET ❌'}",
        f"{'✅' if BINANCE_ADDRESS else '❌'} BINANCE_ADDRESS: {'Set ✅' if BINANCE_ADDRESS else 'NOT SET ❌'}",
        f"{'✅' if UPI_ID else '⚠️'} UPI_ID: `{UPI_ID or 'Not set'}`",
        f"✅ OWNER_ID: `{OWNER_ID}`",
    ]
    try:
        cnt = users_col.count_documents({})
        results.append(f"✅ MongoDB: Connected ({cnt} users)")
    except Exception as e: results.append(f"❌ MongoDB: {str(e)[:40]}")
    ch_cnt = channels_col.count_documents({"active": True})
    results.append(f"📡 Force Channels: {ch_cnt} active")
    bot.send_message(msg.chat.id, "🔑 *Config Status*\n\n" + "\n".join(results))

@bot.message_handler(func=lambda m: m.text == "📡 Channels" and m.from_user.id == OWNER_ID)
def ab_channels(msg):
    channels = get_force_channels()
    t = f"📡 *Force Channels ({len(channels)} active)*\n\n"
    for ch in channels:
        icon = "📢" if ch.get('type') == 'channel' else "👥"
        t += f"{icon} *{ch['name']}*\n🆔 `{ch['channel_id']}`\n🔗 {ch['link']}\n\n"
    if not channels: t += "Koi channel add nahi hua.\n'📡 Force Ch Manage' se add karein."
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.from_user.id == OWNER_ID)
def ab_bc(msg): bot.send_message(msg.chat.id, "📢 `/broadcast Your message here`")

@bot.message_handler(func=lambda m: m.text == "🏆 Top Buyers" and m.from_user.id == OWNER_ID)
def ab_top(msg):
    r = list(orders_col.aggregate([
        {"$match": {"status":"done"}},
        {"$group": {"_id":"$user_id","total":{"$sum":"$amount"},"cnt":{"$sum":1}}},
        {"$sort": {"total":-1}}, {"$limit":10}]))
    if not r: bot.send_message(msg.chat.id,"📭"); return
    t = "🏆 *Top 10 Buyers*\n\n"
    for i, x in enumerate(r,1):
        u = users_col.find_one({"user_id":x['_id']}) or {}
        t += f"{i}. {u.get('full_name','N/A')} `{x['_id']}` — ₹{x['total']:.0f} ({x['cnt']} orders)\n"
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "📦 Orders" and m.from_user.id == OWNER_ID)
def ab_orders(msg):
    orders = list(orders_col.find().sort("created_at",DESCENDING).limit(10))
    if not orders: bot.send_message(msg.chat.id,"📭"); return
    t = "📦 *Recent Orders*\n\n"
    for o in orders:
        ic = "✅" if o['status']=="done" else ("❌" if o['status']=="cancelled" else "⏳")
        src = "🌐" if o.get('source')=='smspool' else ("🔷" if o.get('source')=='vaksms' else "📋")
        t += (f"{ic}{src} `{o['number']}` {o['service']}\n"
              f"👤`{o['user_id']}` ₹{o.get('amount',0):.0f} "
              f"(₹{o.get('profit',0):.0f} profit) "
              f"{o['created_at'].strftime('%d %b %H:%M')}\n\n")
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "📈 Stock" and m.from_user.id == OWNER_ID)
def ab_stock(msg):
    bot.send_message(msg.chat.id,"⏳ Stock check ho raha hai...")
    _stock_report(msg.chat.id)

@bot.message_handler(func=lambda m: m.text == "➕ Platform Add" and m.from_user.id == OWNER_ID)
def ab_add_plat(msg):
    _add_plat_state[OWNER_ID] = {"step": 1}
    bot.send_message(msg.chat.id,
        "➕ *Naya Earning Platform Add Karein*\n\n"
        "*Step 1/3:* Platform ka naam?\n_Example: Amazon Associate_")

# ══════════════════════════════════════════════════════════════════════════════
#  ★★★ NEW: QUICK BALANCE ADD/DEDUCT PANEL ★★★
#  Admin sirf ID daal ke directly balance add ya deduct kar sakta hai
#  Minimum ₹100 enforced | Custom amount bhi possible
# ══════════════════════════════════════════════════════════════════════════════
_quick_bal_state = {}  # {OWNER_ID: {"step": "uid"/"amount", "action": "add"/"deduct", "uid": int}}

@bot.message_handler(func=lambda m: m.text == "💵 Quick Balance" and m.from_user.id == OWNER_ID)
def ab_quick_balance(msg):
    """Admin Panel se directly balance add/deduct karein"""
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("➕ Balance Add Karein",    callback_data="qbal_start_add"),
        types.InlineKeyboardButton("➖ Balance Deduct Karein", callback_data="qbal_start_deduct"),
    )
    mk.add(
        types.InlineKeyboardButton("🔄 Balance Set Karein (Exact)", callback_data="qbal_start_set"),
    )
    bot.send_message(msg.chat.id,
        "💵 *Quick Balance Management*\n\n"
        "👇 Kya karna hai chunein:\n\n"
        "➕ *Add* — User ka balance badhao\n"
        "➖ *Deduct* — User ka balance ghataao\n"
        "🔄 *Set* — Exact balance set karo\n\n"
        "⚠️ Minimum add/deduct: *₹100*",
        reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("qbal_start_"))
def cb_qbal_start(call):
    if call.from_user.id != OWNER_ID: return
    action = call.data.replace("qbal_start_", "")  # add / deduct / set
    _quick_bal_state[OWNER_ID] = {"step": "uid", "action": action}
    bot.answer_callback_query(call.id)
    action_text = "ADD ➕" if action == "add" else ("DEDUCT ➖" if action == "deduct" else "SET 🔄")
    bot.send_message(OWNER_ID,
        f"💵 *Balance {action_text}*\n\n"
        f"User ka *ID* ya *@username* bhejein:\n"
        f"_Example: `12345678` ya `@username`_\n\n"
        f"/cancel se cancel karein")

@bot.message_handler(func=lambda m: (
    m.from_user.id == OWNER_ID
    and OWNER_ID in _quick_bal_state
    and m.text not in ADMIN_BTNS
    and not (m.text or "").startswith('/')
))
def handle_quick_bal_state(msg):
    txt = (msg.text or "").strip()
    state = _quick_bal_state.get(OWNER_ID, {})

    if state.get("step") == "uid":
        # Find user
        if txt.startswith('@'):
            u = find_user_by_username(txt)
        else:
            try: u = users_col.find_one({"user_id": int(txt)})
            except: u = None
        if not u:
            bot.send_message(msg.chat.id, f"❌ User `{txt}` nahi mila. Dobara try karein ya /cancel"); return
        _quick_bal_state[OWNER_ID]["step"] = "amount"
        _quick_bal_state[OWNER_ID]["uid"] = u["user_id"]
        action = state["action"]
        action_text = "ADD ➕" if action == "add" else ("DEDUCT ➖" if action == "deduct" else "SET 🔄")

        # Show quick amount buttons
        uid = u["user_id"]
        mk = types.InlineKeyboardMarkup(row_width=3)
        if action in ("add", "deduct"):
            prefix = "qadd" if action == "add" else "qded"
            mk.add(
                types.InlineKeyboardButton("₹100",  callback_data=f"{prefix}_qb_{uid}_100"),
                types.InlineKeyboardButton("₹200",  callback_data=f"{prefix}_qb_{uid}_200"),
                types.InlineKeyboardButton("₹500",  callback_data=f"{prefix}_qb_{uid}_500"),
                types.InlineKeyboardButton("₹1000", callback_data=f"{prefix}_qb_{uid}_1000"),
                types.InlineKeyboardButton("₹2000", callback_data=f"{prefix}_qb_{uid}_2000"),
                types.InlineKeyboardButton("₹5000", callback_data=f"{prefix}_qb_{uid}_5000"),
            )
            mk.add(types.InlineKeyboardButton("✏️ Custom Amount", callback_data=f"{prefix}_qb_{uid}_custom"))
        else:
            mk.add(types.InlineKeyboardButton("✏️ Amount bhejein", callback_data=f"qset_qb_{uid}_custom"))
        mk.add(types.InlineKeyboardButton("❌ Cancel", callback_data="qbal_cancel"))

        bot.send_message(msg.chat.id,
            f"✅ User mila!\n"
            f"👤 `{uid}` — {u.get('full_name','?')} @{u.get('username','N/A')}\n"
            f"💵 Current Balance: *₹{u.get('balance',0):.0f}*\n\n"
            f"*{action_text}* — Amount chunein 👇\n"
            f"_(Minimum: ₹100)_", reply_markup=mk)

    elif state.get("step") == "custom_amount":
        uid = state.get("uid")
        action = state.get("action")
        try:
            amount = float(txt)
        except:
            bot.send_message(msg.chat.id, "❌ Sirf number bhejein! (e.g. `500`)"); return
        if action in ("add", "deduct") and amount < 100:
            bot.send_message(msg.chat.id, "❌ *Minimum ₹100* chahiye!\nDobara bhejein:"); return
        _quick_bal_state.pop(OWNER_ID, None)
        _execute_quick_balance(msg.chat.id, uid, amount, action)

@bot.callback_query_handler(func=lambda c: c.data.startswith("qadd_qb_") or c.data.startswith("qded_qb_") or c.data.startswith("qset_qb_"))
def cb_qbal_amount(call):
    if call.from_user.id != OWNER_ID: return
    parts = call.data.split("_")
    # qadd_qb_UID_AMOUNT or qded_qb_UID_AMOUNT or qset_qb_UID_custom
    prefix = parts[0]  # qadd / qded / qset
    action = "add" if prefix == "qadd" else ("deduct" if prefix == "qded" else "set")
    uid = int(parts[2])
    amount_str = parts[3]

    if amount_str == "custom":
        _quick_bal_state[OWNER_ID] = {"step": "custom_amount", "action": action, "uid": uid}
        bot.answer_callback_query(call.id)
        u = users_col.find_one({"user_id": uid}) or {}
        bot.send_message(OWNER_ID,
            f"✏️ *Custom Amount*\n\n"
            f"User `{uid}` — Balance: ₹{u.get('balance',0):.0f}\n\n"
            f"Amount bhejein ({'Min ₹100' if action != 'set' else 'Exact amount'}):\n"
            f"/cancel se cancel")
        return

    amount = float(amount_str)
    bot.answer_callback_query(call.id, f"⏳ Processing...")
    _quick_bal_state.pop(OWNER_ID, None)
    _execute_quick_balance(call.message.chat.id, uid, amount, action)

@bot.callback_query_handler(func=lambda c: c.data == "qbal_cancel")
def cb_qbal_cancel(call):
    if call.from_user.id != OWNER_ID: return
    _quick_bal_state.pop(OWNER_ID, None)
    bot.answer_callback_query(call.id, "✅ Cancel ho gaya")
    bot.send_message(OWNER_ID, "✅ Cancel ho gaya.", reply_markup=admin_menu())

def _execute_quick_balance(cid, uid, amount, action):
    """Execute balance add/deduct/set and notify both admin and user"""
    u_before = users_col.find_one({"user_id": uid}) or {}
    bal_before = u_before.get('balance', 0)

    if action == "add":
        add_balance(uid, amount)
        log_admin_balance_action(OWNER_ID, uid, amount, "add", "quick_balance_panel")
        u_after = users_col.find_one({"user_id": uid}) or {}
        new_bal = u_after.get('balance', 0)
        bot.send_message(cid,
            f"✅ *Balance Add Done!*\n\n"
            f"👤 User: `{uid}`\n"
            f"📛 {u_before.get('full_name','?')} @{u_before.get('username','N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 Pehle: ₹{bal_before:.0f}\n"
            f"➕ Add: ₹{amount:.0f}\n"
            f"💰 Naya: *₹{new_bal:.0f}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ User ko notify kar diya!")
        try: bot.send_message(uid,
            f"🎉 *₹{amount:.0f} Balance Add Hua!*\n\n"
            f"💵 Pehle: ₹{bal_before:.0f}\n"
            f"💰 Naya Balance: *₹{new_bal:.0f}*\n\n"
            f"📲 Buy Number dabayein 🛒")
        except: pass

    elif action == "deduct":
        add_balance(uid, -amount)
        log_admin_balance_action(OWNER_ID, uid, amount, "deduct", "quick_balance_panel")
        u_after = users_col.find_one({"user_id": uid}) or {}
        new_bal = u_after.get('balance', 0)
        bot.send_message(cid,
            f"✅ *Balance Deduct Done!*\n\n"
            f"👤 User: `{uid}`\n"
            f"📛 {u_before.get('full_name','?')} @{u_before.get('username','N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 Pehle: ₹{bal_before:.0f}\n"
            f"➖ Deduct: ₹{amount:.0f}\n"
            f"💰 Naya: *₹{new_bal:.0f}*")
        try: bot.send_message(uid,
            f"❕ *Balance Update Hua*\n\n"
            f"₹{amount:.0f} adjust hua.\n"
            f"💰 Naya Balance: *₹{new_bal:.0f}*")
        except: pass

    elif action == "set":
        users_col.update_one({"user_id": uid}, {"$set": {"balance": amount}})
        log_admin_balance_action(OWNER_ID, uid, amount, "set", "quick_balance_panel")
        bot.send_message(cid,
            f"✅ *Balance SET Done!*\n\n"
            f"👤 User: `{uid}`\n"
            f"📛 {u_before.get('full_name','?')} @{u_before.get('username','N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 Pehle: ₹{bal_before:.0f}\n"
            f"🔄 Set: ₹{amount:.0f}")
        try: bot.send_message(uid,
            f"✅ *Balance Update Hua!*\n\n"
            f"💰 Naya Balance: *₹{amount:.0f}*")
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  ★★★ NEW: LIVE PRICE CHECKER ★★★
#  SmsPool raw price + VakSMS raw price + Margin add kara hua price
#  Admin ek button se check kar sakta hai
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📊 Live Price Check" and m.from_user.id == OWNER_ID)
def ab_live_price_check(msg):
    """Show live price checker — service aur country chunein"""
    mk = types.InlineKeyboardMarkup(row_width=2)
    # Most popular services
    services = [
        ("📱 WhatsApp", "whatsapp"),
        ("✈️ Telegram", "telegram"),
        ("📸 Instagram", "instagram"),
        ("📧 Gmail", "google"),
        ("📘 Facebook", "facebook"),
        ("🎵 TikTok", "tiktok"),
        ("🐦 Twitter/X", "twitter"),
        ("📷 Snapchat", "snapchat"),
        ("🛒 Amazon", "amazon"),
        ("💼 LinkedIn", "linkedin"),
    ]
    for label, api in services:
        mk.add(types.InlineKeyboardButton(label, callback_data=f"lpc_svc_{api}"))
    mk.add(types.InlineKeyboardButton("📊 Full Stock Report", callback_data="lpc_full_report"))
    bot.send_message(msg.chat.id,
        "📊 *Live Price Checker*\n\n"
        "Service chunein — dono APIs ka *raw price* aur *margin wala price* dikhega:\n\n"
        "🌐 SmsPool raw → margin price\n"
        "🔷 VakSMS raw → margin price",
        reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lpc_svc_"))
def cb_lpc_service(call):
    if call.from_user.id != OWNER_ID: return
    api = call.data.replace("lpc_svc_", "")
    bot.answer_callback_query(call.id, "⏳ Countries load ho rahi hain...")

    # Get countries for this service
    countries = []
    for svc_label, items in SERVICES.items():
        for key, info in items.items():
            if info['api'] == api and info['cc'] not in [c[0] for c in countries]:
                countries.append((info['cc'], info['flag'], info['country']))

    mk = types.InlineKeyboardMarkup(row_width=2)
    for cc, flag, country in countries:
        mk.add(types.InlineKeyboardButton(
            f"{flag} {country}", callback_data=f"lpc_check_{api}_{cc}"))
    mk.add(types.InlineKeyboardButton("🔄 Sabka Price Dikhao", callback_data=f"lpc_all_{api}"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="lpc_back"))

    api_name = api.title()
    bot.send_message(call.message.chat.id,
        f"📊 *{api_name} — Country Chunein*\n\n"
        f"Ek country select karein ya sabka price ek saath dekho:",
        reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lpc_check_"))
def cb_lpc_check(call):
    if call.from_user.id != OWNER_ID: return
    parts = call.data.replace("lpc_check_", "").split("_", 1)
    api = parts[0]; cc = parts[1]
    bot.answer_callback_query(call.id, "⏳ Live price fetch ho raha hai...")

    margin = get_margin()
    usdt_rate = get_usdt_rate()

    # Force fresh fetch
    _pc.pop(f"{cc}|{api}", None)
    psp_raw = None; pvk_raw = None
    ssp = svk = 0

    # SmsPool raw price
    try:
        if SMSPOOL_KEY:
            country = SMSPOOL_CC.get(cc)
            service = SMSPOOL_SVC.get(api)
            if country and service:
                r = requests.get(
                    "https://api.smspool.net/service/price",
                    params={"key": SMSPOOL_KEY, "country": country, "service": service},
                    timeout=8).json()
                raw_usd = float(r.get("price", 0))
                ssp = int(r.get("stock", 0))
                if raw_usd > 0:
                    psp_raw = raw_usd
    except Exception as e:
        logger.warning(f"LPC SmsPool: {e}")

    # VakSMS raw price
    try:
        if VAKSMS_KEY:
            country = VAKSMS_CC.get(cc)
            service = VAKSMS_SVC.get(api)
            if country and service:
                r = requests.get(
                    "https://vak-sms.com/api/getCountOperator/",
                    params={"apiKey": VAKSMS_KEY, "country": country, "service": service},
                    timeout=8).json()
                if isinstance(r, list) and r:
                    best = None; total_s = 0
                    for op in r:
                        p = float(op.get("price", 0)); c = int(op.get("count", 0))
                        total_s += c
                        if c > 0 and (best is None or p < best): best = p
                    svk = total_s
                    if best:
                        pvk_raw = best
    except Exception as e:
        logger.warning(f"LPC VakSMS: {e}")

    dp, ds = _get_default_price(cc, api)
    margin_pct = int((margin - 1) * 100)

    # Flag and country name
    flag_info = ""
    for _, items in SERVICES.items():
        for key, info in items.items():
            if info['cc'] == cc and info['api'] == api:
                flag_info = f"{info['flag']} {info['country']}"
                break
        if flag_info: break

    t = f"📊 *Live Price — {flag_info} {api.title()}*\n"
    t += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    t += f"📈 Margin: *{margin_pct}%* | USDT Rate: ₹{usdt_rate}\n\n"

    if psp_raw:
        sp_inr_raw = round(psp_raw * usdt_rate, 2)
        sp_margin = math.ceil(psp_raw * usdt_rate * margin)
        t += f"🌐 *SmsPool*\n"
        t += f"  Raw: ${psp_raw:.4f} = ₹{sp_inr_raw:.2f}\n"
        t += f"  +{margin_pct}% margin → *₹{sp_margin}*\n"
        t += f"  📦 Stock: {ssp}\n\n"
    else:
        t += f"🌐 *SmsPool*: ❌ No price/stock\n\n"

    if pvk_raw:
        vk_margin = math.ceil(pvk_raw * margin)
        t += f"🔷 *Vak-SMS*\n"
        t += f"  Raw: ₽{pvk_raw:.2f}\n"
        t += f"  +{margin_pct}% margin → *₹{vk_margin}*\n"
        t += f"  📦 Stock: {svk}\n\n"
    else:
        t += f"🔷 *Vak-SMS*: ❌ No price/stock\n\n"

    if dp:
        t += f"📋 *Default (Fallback)*: ₹{dp} | Stock: {ds}\n\n"

    if psp_raw or pvk_raw:
        best = min([x for x in [
            math.ceil(psp_raw * usdt_rate * margin) if psp_raw else None,
            math.ceil(pvk_raw * margin) if pvk_raw else None
        ] if x], default=dp)
        t += f"✅ *User ko dikha raha hai: ₹{best}*\n"
    else:
        t += f"⚠️ *Koi live stock nahi — Default price: ₹{dp or 'N/A'}*"

    t += f"\n🕐 {datetime.utcnow().strftime('%H:%M')} UTC"

    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=call.data))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"lpc_svc_{api}"))
    bot.send_message(call.message.chat.id, t, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lpc_all_"))
def cb_lpc_all(call):
    if call.from_user.id != OWNER_ID: return
    api = call.data.replace("lpc_all_", "")
    bot.answer_callback_query(call.id, "⏳ Sabka price fetch ho raha hai...")

    margin = get_margin()
    usdt_rate = get_usdt_rate()
    margin_pct = int((margin - 1) * 100)

    # Get all countries for this API
    countries_done = set()
    results = []
    for _, items in SERVICES.items():
        for key, info in items.items():
            if info['api'] == api and info['cc'] not in countries_done:
                countries_done.add(info['cc'])
                cc = info['cc']
                _pc.pop(f"{cc}|{api}", None)  # force refresh
                psp, ssp = _smspool_price(cc, api)
                pvk, svk = _vaksms_price(cc, api)
                dp, ds = _get_default_price(cc, api)
                total_stock = (ssp or 0) + (svk or 0)
                best = psp or pvk or dp

                if best:
                    stock_ic = "🟢" if total_stock > 20 else ("🟡" if total_stock > 5 else "🔴")
                    src_icons = []
                    if psp: src_icons.append(f"🌐₹{psp}")
                    if pvk: src_icons.append(f"🔷₹{pvk}")
                    if not psp and not pvk: src_icons.append(f"📋₹{dp}(def)")
                    results.append(
                        f"{stock_ic}{info['flag']} {info['country']}: "
                        f"{' | '.join(src_icons)} → *₹{best}* 📦{total_stock}")

    t = (f"📊 *{api.title()} — All Countries Live Price*\n"
         f"Margin: {margin_pct}% | {datetime.utcnow().strftime('%H:%M')} UTC\n"
         f"━━━━━━━━━━━━━━━━━━━━━━\n\n")
    t += "\n".join(results) if results else "❌ Koi price nahi mila"

    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=call.data))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"lpc_svc_{api}"))
    bot.send_message(call.message.chat.id, t, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "lpc_back")
def cb_lpc_back(call):
    if call.from_user.id != OWNER_ID: return
    bot.answer_callback_query(call.id)
    ab_live_price_check(call.message)

@bot.callback_query_handler(func=lambda c: c.data == "lpc_full_report")
def cb_lpc_full(call):
    if call.from_user.id != OWNER_ID: return
    bot.answer_callback_query(call.id, "⏳ Full report ban rahi hai...")
    _stock_report(call.message.chat.id)

@bot.message_handler(func=lambda m: m.text == "💾 Export" and m.from_user.id == OWNER_ID)
def ab_export(msg):
    users = list(users_col.find({},{"user_id":1,"username":1,"full_name":1,"balance":1,"orders":1,"banned":1}))
    lines = ["ID|Name|Username|Balance|Orders|Banned"]
    lines += [f"{u['user_id']}|{u.get('full_name','N/A')}|@{u.get('username','N/A')}|₹{u.get('balance',0):.0f}|{u.get('orders',0)}|{u.get('banned',False)}" for u in users]
    f = io.BytesIO("\n".join(lines).encode())
    f.name = f"users_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.txt"
    bot.send_document(msg.chat.id, f, caption=f"📦 Total: {len(users)} users")

@bot.message_handler(func=lambda m: m.text == "🔙 Back" and m.from_user.id == OWNER_ID)
def ab_back(msg):
    bot.send_message(msg.chat.id, "🏠", reply_markup=main_menu(OWNER_ID))

# ══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _send_stats(cid):
    tu = users_col.count_documents({}); bu = users_col.count_documents({"banned":True})
    to = orders_col.count_documents({}); do = orders_col.count_documents({"status":"done"})
    co = orders_col.count_documents({"status":"cancelled"})
    pd = deposits_col.count_documents({"status":"pending"})
    agg = list(orders_col.aggregate([
        {"$match":{"status":"done"}},
        {"$group":{"_id":"$source","rev":{"$sum":"$amount"},"cnt":{"$sum":1}}}]))
    rev_sp=rev_vk=cnt_sp=cnt_vk=0
    for x in agg:
        if x['_id']=='smspool': rev_sp=x['rev']; cnt_sp=x['cnt']
        elif x['_id']=='vaksms': rev_vk=x['rev']; cnt_vk=x['cnt']
    total_rev = rev_sp+rev_vk
    margin = get_margin()
    profit_est = round(total_rev*(1-1/margin),0)
    total_added = sum(l.get('amount',0) for l in admin_log_col.find({"type":"add"}))
    total_deducted = sum(l.get('amount',0) for l in admin_log_col.find({"type":"deduct"}))
    bot.send_message(cid,
        f"📊 *Bot Statistics*\n\n"
        f"👥 Users: `{tu}` (🚫{bu})\n"
        f"🛒 Orders: `{to}` ✅{do} ❌{co}\n"
        f"📥 Pending Dep: `{pd}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 SmsPool: `₹{rev_sp:.0f}` ({cnt_sp} orders)\n"
        f"🔷 Vak-SMS: `₹{rev_vk:.0f}` ({cnt_vk} orders)\n"
        f"💰 Total Revenue: `₹{total_rev:.0f}`\n"
        f"📈 Est. Profit ({int((margin-1)*100)}%): `₹{profit_est:.0f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"➕ Admin Added: `₹{total_added:.0f}`\n"
        f"➖ Admin Deducted: `₹{total_deducted:.0f}`")

def _do_broadcast(cid, text):
    all_u = list(users_col.find({"banned":{"$ne":True}}))
    pm = bot.send_message(cid, f"📢 {len(all_u)} users ko bhej rahe hain...")
    s=f=0
    for u in all_u:
        try: bot.send_message(u['user_id'], f"📢 *Announcement*\n\n{text}"); s+=1
        except: f+=1
        time.sleep(0.05)
    bot.edit_message_text(f"✅ Sent:`{s}` Failed:`{f}`", cid, pm.message_id)

def _stock_report(cid):
    """Admin-only full stock report — live + default indicator, both APIs"""
    checks = [
        ("WhatsApp","russia","whatsapp","🇷🇺"),("WhatsApp","india","whatsapp","🇮🇳"),
        ("WhatsApp","usa","whatsapp","🇺🇸"),("WhatsApp","uk","england","🇬🇧"),
        ("WhatsApp","ukraine","ukraine","🇺🇦"),("WhatsApp","indonesia","indonesia","🇮🇩"),
        ("Telegram","russia","telegram","🇷🇺"),("Telegram","india","telegram","🇮🇳"),
        ("Instagram","russia","instagram","🇷🇺"),("Instagram","india","instagram","🇮🇳"),
        ("Gmail","russia","google","🇷🇺"),("Gmail","india","google","🇮🇳"),
        ("Facebook","russia","facebook","🇷🇺"),("Facebook","india","facebook","🇮🇳")]
    t = "📈 *Live Stock Report*\n🌐=SmsPool 🔷=VakSMS 📋=Default\n\n"
    for svc_name, cc_name, api, flag in checks:
        cc = cc_name
        _pc.pop(f"{cc}|{api}", None)  # force refresh
        psp, ssp = _smspool_price(cc, api)
        pvk, svk = _vaksms_price(cc, api)
        dp, ds = _get_default_price(cc, api)
        if (psp and ssp > 0) or (pvk and svk > 0):
            total_live = (ssp or 0) + (svk or 0)
            best_p = min([x for x in [psp, pvk] if x], default=dp)
            if total_live <= LOW_STOCK: ic = "🔴"
            elif total_live <= 20:      ic = "🟡"
            else:                        ic = "🟢"
            sp_part = f"🌐{ssp}" if ssp else "🌐0"
            vk_part = f"🔷{svk}" if svk else "🔷0"
            t += f"{ic}{flag} {cc.title()} {svc_name}: {sp_part}+{vk_part}={total_live} | ₹{best_p}\n"
        elif dp:
            t += f"📋{flag} {cc.title()} {svc_name}: No live | ₹{dp} (APIs recharge needed)\n"
        else:
            t += f"⚫{flag} {cc.title()} {svc_name}: No data\n"
    margin = get_margin()
    t += f"\n📈 Margin: {int((margin-1)*100)}% | {datetime.utcnow().strftime('%H:%M')} UTC"
    bot.send_message(cid, t)

def _stock_monitor():
    while True:
        time.sleep(1800)
        try:
            lows = []
            for svc_name, cc, api, flag in [
                ("WhatsApp","russia","whatsapp","🇷🇺"),
                ("WhatsApp","india","whatsapp","🇮🇳"),
                ("Telegram","russia","telegram","🇷🇺"),
                ("Telegram","india","telegram","🇮🇳")]:
                _pc.pop(f"{cc}|{api}", None)
                psp, ssp = _smspool_price(cc, api)
                pvk, svk = _vaksms_price(cc, api)
                total = (ssp or 0) + (svk or 0)
                if total > 0 and total <= LOW_STOCK:
                    lows.append(f"{flag}{cc.title()} {svc_name}: {total} left!")
            if lows:
                bot.send_message(OWNER_ID,
                    "⚠️ *LOW STOCK ALERT!*\n\n" + "\n".join(lows) +
                    "\n\n🌐 https://smspool.net\n🔷 https://vak-sms.com")
        except Exception as e: logger.error(f"Stock monitor: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  FALLBACK
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: True)
@gaali_check
def fallback(msg):
    bot.send_message(msg.chat.id, "❓ Buttons use karein 👇",
        reply_markup=main_menu(msg.from_user.id))

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("👑 OtpKing Pro v5 starting...")
    Thread(target=_stock_monitor, daemon=True).start()
    retry = 0
    while True:
        try:
            logger.info(f"✅ Polling (attempt {retry+1})")
            bot.polling(none_stop=True, interval=0, timeout=20)
            retry = 0
        except Exception as e:
            retry += 1
            logger.error(f"Polling error: {e}")
            if '409' in str(e):
                logger.info("409 conflict — waiting 15s...")
                time.sleep(15)
            else:
                time.sleep(min(retry * 5, 30))
            clear_session()
