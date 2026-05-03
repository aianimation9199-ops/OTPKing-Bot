"""
OTPKING PRO — SmsPool + Vak-SMS DUAL API
Clean UI | Hidden Margin | Multi-Platform Refer & Earn
"""
import os, logging, requests, time, math, io
from pymongo import MongoClient, DESCENDING
from telebot import types
import telebot
from dotenv import load_dotenv
from threading import Thread
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN          = os.getenv('BOT_TOKEN', '')
MONGO_URI          = os.getenv('MONGO_URI') or os.getenv('MONGO_URL', '')
SMSPOOL_KEY        = os.getenv('SMSPOOL_API_KEY', '')      # SmsPool API Key
VAKSMS_KEY         = os.getenv('VAKSMS_API_KEY', '')       # Vak-SMS API Key
OWNER_ID           = int(os.getenv('OWNER_ID', '0'))
SUPPORT_BOT        = os.getenv('SUPPORT_BOT', '@YourHelpBot')
PROOF_CHANNEL_ID   = os.getenv('PROOF_CHANNEL_ID', '@ProofChannel')
PROOF_CHANNEL_LINK = os.getenv('PROOF_CHANNEL_LINK', 'https://t.me/ProofChannel')
GROUP_ID           = os.getenv('GROUP_ID', '@YourGroup')
GROUP_LINK         = os.getenv('GROUP_LINK', 'https://t.me/YourGroup')
UPI_ID             = os.getenv('UPI_ID', 'yourname@upi')

CH = [
    (os.getenv('CHANNEL1_ID','@Ch1'), os.getenv('CHANNEL1_LINK','https://t.me/Ch1'), "Channel 1"),
    (os.getenv('CHANNEL2_ID','@Ch2'), os.getenv('CHANNEL2_LINK','https://t.me/Ch2'), "Channel 2"),
    (os.getenv('CHANNEL3_ID','@Ch3'), os.getenv('CHANNEL3_LINK','https://t.me/Ch3'), "Channel 3"),
    (os.getenv('CHANNEL4_ID','@Ch4'), os.getenv('CHANNEL4_LINK','https://t.me/Ch4'), "Channel 4"),
]

USDT_RATE = 85.0
MARGIN    = 1.40   # 40% margin — admin ko hi dikhega, user ko nahi
LOW_STOCK = 5
UPI_LIST  = [50, 100, 200, 300, 500, 1000, 2000, 3000, 5000]

BAD_WORDS = ["madarchod","mc","bc","bhenchod","gandu","chutiya","randi","harami",
             "bhosdike","loda","lauda","chut","bsdk","fuck","bitch","asshole",
             "bastard","shit","dick","cunt","whore","sala","maderchod","behenchod"]

# ── SmsPool Country/Service Codes ─────────────────────────────────────────────
# SmsPool uses country ISO codes and service names
SMSPOOL_CC = {
    "russia":"RU","india":"IN","usa":"US","england":"GB","ukraine":"UA",
    "brazil":"BR","indonesia":"ID","kenya":"KE","nigeria":"NG","pakistan":"PK",
    "cambodia":"KH","myanmar":"MM","vietnam":"VN","philippines":"PH",
    "bangladesh":"BD","kazakhstan":"KZ",
}
SMSPOOL_SVC = {
    "whatsapp":"wa","telegram":"tg","instagram":"ig","google":"go",
    "facebook":"fb","tiktok":"tt","twitter":"tw","snapchat":"sc",
    "amazon":"amazon","linkedin":"li",
}

# ── Vak-SMS Country/Service Codes ─────────────────────────────────────────────
VAKSMS_CC = {
    "russia":"ru","india":"in","usa":"us","england":"gb","ukraine":"ua",
    "brazil":"br","indonesia":"id","kenya":"ke","nigeria":"ng","pakistan":"pk",
    "cambodia":"kh","myanmar":"mm","vietnam":"vn","philippines":"ph",
    "bangladesh":"bd","kazakhstan":"kz",
}
VAKSMS_SVC = {
    "whatsapp":"wh","telegram":"tg","instagram":"ig","google":"go",
    "facebook":"fb","tiktok":"tt","twitter":"tw","snapchat":"sc",
    "amazon":"am","linkedin":"li",
}

# ── FIX 409 ───────────────────────────────────────────────────────────────────
def clear_session():
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
        time.sleep(2)
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1&timeout=1", timeout=10)
        time.sleep(1)
        logger.info("✅ Session cleared")
    except Exception as e:
        logger.error(f"Session clear: {e}")

clear_session()

# ── MONGODB ────────────────────────────────────────────────────────────────────
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=10000,
    maxPoolSize=10,
    retryWrites=True,
    w='majority',
)
db           = client['otp_king_pro']
users_col    = db['users']
orders_col   = db['orders']
deposits_col = db['deposits']
platforms_col= db['earn_platforms']   # Refer & Earn platforms store

try:
    users_col.create_index("user_id", unique=True)
    orders_col.create_index("order_id")
    orders_col.create_index("user_id")
    deposits_col.create_index("user_id")
    logger.info("✅ MongoDB indexes created")
except Exception as e:
    logger.warning(f"Index creation: {e}")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown", threaded=False)

# ── SERVICES ──────────────────────────────────────────────────────────────────
SERVICES = {
    "📱 WhatsApp": {
        "wa_russia":      {"cc":"russia",      "api":"whatsapp","flag":"🇷🇺","country":"Russia"},
        "wa_india":       {"cc":"india",       "api":"whatsapp","flag":"🇮🇳","country":"India"},
        "wa_usa":         {"cc":"usa",         "api":"whatsapp","flag":"🇺🇸","country":"USA"},
        "wa_uk":          {"cc":"england",     "api":"whatsapp","flag":"🇬🇧","country":"UK"},
        "wa_ukraine":     {"cc":"ukraine",     "api":"whatsapp","flag":"🇺🇦","country":"Ukraine"},
        "wa_brazil":      {"cc":"brazil",      "api":"whatsapp","flag":"🇧🇷","country":"Brazil"},
        "wa_indonesia":   {"cc":"indonesia",   "api":"whatsapp","flag":"🇮🇩","country":"Indonesia"},
        "wa_kenya":       {"cc":"kenya",       "api":"whatsapp","flag":"🇰🇪","country":"Kenya"},
        "wa_nigeria":     {"cc":"nigeria",     "api":"whatsapp","flag":"🇳🇬","country":"Nigeria"},
        "wa_pakistan":    {"cc":"pakistan",    "api":"whatsapp","flag":"🇵🇰","country":"Pakistan"},
        "wa_cambodia":    {"cc":"cambodia",    "api":"whatsapp","flag":"🇰🇭","country":"Cambodia"},
        "wa_myanmar":     {"cc":"myanmar",     "api":"whatsapp","flag":"🇲🇲","country":"Myanmar"},
        "wa_vietnam":     {"cc":"vietnam",     "api":"whatsapp","flag":"🇻🇳","country":"Vietnam"},
        "wa_philippines": {"cc":"philippines", "api":"whatsapp","flag":"🇵🇭","country":"Philippines"},
        "wa_bangladesh":  {"cc":"bangladesh",  "api":"whatsapp","flag":"🇧🇩","country":"Bangladesh"},
        "wa_kazakhstan":  {"cc":"kazakhstan",  "api":"whatsapp","flag":"🇰🇿","country":"Kazakhstan"},
    },
    "✈️ Telegram": {
        "tg_russia":      {"cc":"russia",      "api":"telegram","flag":"🇷🇺","country":"Russia"},
        "tg_india":       {"cc":"india",       "api":"telegram","flag":"🇮🇳","country":"India"},
        "tg_usa":         {"cc":"usa",         "api":"telegram","flag":"🇺🇸","country":"USA"},
        "tg_uk":          {"cc":"england",     "api":"telegram","flag":"🇬🇧","country":"UK"},
        "tg_ukraine":     {"cc":"ukraine",     "api":"telegram","flag":"🇺🇦","country":"Ukraine"},
        "tg_cambodia":    {"cc":"cambodia",    "api":"telegram","flag":"🇰🇭","country":"Cambodia"},
        "tg_myanmar":     {"cc":"myanmar",     "api":"telegram","flag":"🇲🇲","country":"Myanmar"},
        "tg_indonesia":   {"cc":"indonesia",   "api":"telegram","flag":"🇮🇩","country":"Indonesia"},
        "tg_kazakhstan":  {"cc":"kazakhstan",  "api":"telegram","flag":"🇰🇿","country":"Kazakhstan"},
        "tg_vietnam":     {"cc":"vietnam",     "api":"telegram","flag":"🇻🇳","country":"Vietnam"},
        "tg_bangladesh":  {"cc":"bangladesh",  "api":"telegram","flag":"🇧🇩","country":"Bangladesh"},
        "tg_philippines": {"cc":"philippines", "api":"telegram","flag":"🇵🇭","country":"Philippines"},
    },
    "📸 Instagram": {
        "ig_russia":      {"cc":"russia",      "api":"instagram","flag":"🇷🇺","country":"Russia"},
        "ig_india":       {"cc":"india",       "api":"instagram","flag":"🇮🇳","country":"India"},
        "ig_usa":         {"cc":"usa",         "api":"instagram","flag":"🇺🇸","country":"USA"},
        "ig_ukraine":     {"cc":"ukraine",     "api":"instagram","flag":"🇺🇦","country":"Ukraine"},
        "ig_brazil":      {"cc":"brazil",      "api":"instagram","flag":"🇧🇷","country":"Brazil"},
        "ig_indonesia":   {"cc":"indonesia",   "api":"instagram","flag":"🇮🇩","country":"Indonesia"},
        "ig_uk":          {"cc":"england",     "api":"instagram","flag":"🇬🇧","country":"UK"},
        "ig_nigeria":     {"cc":"nigeria",     "api":"instagram","flag":"🇳🇬","country":"Nigeria"},
    },
    "📧 Gmail": {
        "gm_russia":      {"cc":"russia",      "api":"google","flag":"🇷🇺","country":"Russia"},
        "gm_india":       {"cc":"india",       "api":"google","flag":"🇮🇳","country":"India"},
        "gm_usa":         {"cc":"usa",         "api":"google","flag":"🇺🇸","country":"USA"},
        "gm_ukraine":     {"cc":"ukraine",     "api":"google","flag":"🇺🇦","country":"Ukraine"},
        "gm_uk":          {"cc":"england",     "api":"google","flag":"🇬🇧","country":"UK"},
        "gm_indonesia":   {"cc":"indonesia",   "api":"google","flag":"🇮🇩","country":"Indonesia"},
    },
    "📘 Facebook": {
        "fb_russia":      {"cc":"russia",      "api":"facebook","flag":"🇷🇺","country":"Russia"},
        "fb_india":       {"cc":"india",       "api":"facebook","flag":"🇮🇳","country":"India"},
        "fb_usa":         {"cc":"usa",         "api":"facebook","flag":"🇺🇸","country":"USA"},
        "fb_ukraine":     {"cc":"ukraine",     "api":"facebook","flag":"🇺🇦","country":"Ukraine"},
        "fb_indonesia":   {"cc":"indonesia",   "api":"facebook","flag":"🇮🇩","country":"Indonesia"},
        "fb_brazil":      {"cc":"brazil",      "api":"facebook","flag":"🇧🇷","country":"Brazil"},
    },
    "🎵 TikTok": {
        "tt_russia":      {"cc":"russia",      "api":"tiktok","flag":"🇷🇺","country":"Russia"},
        "tt_usa":         {"cc":"usa",         "api":"tiktok","flag":"🇺🇸","country":"USA"},
        "tt_india":       {"cc":"india",       "api":"tiktok","flag":"🇮🇳","country":"India"},
        "tt_indonesia":   {"cc":"indonesia",   "api":"tiktok","flag":"🇮🇩","country":"Indonesia"},
        "tt_brazil":      {"cc":"brazil",      "api":"tiktok","flag":"🇧🇷","country":"Brazil"},
    },
    "🐦 Twitter/X": {
        "tw_russia":      {"cc":"russia",      "api":"twitter","flag":"🇷🇺","country":"Russia"},
        "tw_india":       {"cc":"india",       "api":"twitter","flag":"🇮🇳","country":"India"},
        "tw_usa":         {"cc":"usa",         "api":"twitter","flag":"🇺🇸","country":"USA"},
        "tw_uk":          {"cc":"england",     "api":"twitter","flag":"🇬🇧","country":"UK"},
    },
    "📷 Snapchat": {
        "sc_russia":      {"cc":"russia",      "api":"snapchat","flag":"🇷🇺","country":"Russia"},
        "sc_usa":         {"cc":"usa",         "api":"snapchat","flag":"🇺🇸","country":"USA"},
        "sc_uk":          {"cc":"england",     "api":"snapchat","flag":"🇬🇧","country":"UK"},
        "sc_india":       {"cc":"india",       "api":"snapchat","flag":"🇮🇳","country":"India"},
    },
    "🛒 Amazon": {
        "az_russia":      {"cc":"russia",      "api":"amazon","flag":"🇷🇺","country":"Russia"},
        "az_india":       {"cc":"india",       "api":"amazon","flag":"🇮🇳","country":"India"},
        "az_usa":         {"cc":"usa",         "api":"amazon","flag":"🇺🇸","country":"USA"},
        "az_uk":          {"cc":"england",     "api":"amazon","flag":"🇬🇧","country":"UK"},
    },
    "💼 LinkedIn": {
        "li_russia":      {"cc":"russia",      "api":"linkedin","flag":"🇷🇺","country":"Russia"},
        "li_india":       {"cc":"india",       "api":"linkedin","flag":"🇮🇳","country":"India"},
        "li_usa":         {"cc":"usa",         "api":"linkedin","flag":"🇺🇸","country":"USA"},
        "li_uk":          {"cc":"england",     "api":"linkedin","flag":"🇬🇧","country":"UK"},
    },
}
ALL_BTNS = set(SERVICES.keys())

# ══════════════════════════════════════════════════════════════════════════════
#  DUAL API ENGINE — SmsPool + Vak-SMS
# ══════════════════════════════════════════════════════════════════════════════
_pc = {}

def _smspool_price(cc, api):
    """SmsPool API — get price and stock"""
    try:
        country = SMSPOOL_CC.get(cc)
        service = SMSPOOL_SVC.get(api)
        if not country or not service: return None, 0
        r = requests.get(
            f"https://api.smspool.net/service/price",
            params={"key": SMSPOOL_KEY, "country": country, "service": service},
            timeout=8
        ).json()
        # SmsPool returns: {"price": 0.5, "stock": 100, ...}
        price  = float(r.get("price", 0))
        stock  = int(r.get("stock", 0))
        if price > 0 and stock > 0:
            sell = math.ceil(price * USDT_RATE * MARGIN)
            return sell, stock
    except Exception as e:
        logger.warning(f"SmsPool price: {e}")
    return None, 0

def _vaksms_price(cc, api):
    """Vak-SMS API — get price and stock"""
    try:
        country = VAKSMS_CC.get(cc)
        service = VAKSMS_SVC.get(api)
        if not country or not service: return None, 0
        r = requests.get(
            f"https://vak-sms.com/api/getCountOperator/",
            params={"apiKey": VAKSMS_KEY, "country": country, "service": service},
            timeout=8
        ).json()
        # Vak-SMS returns list of operators with price and count
        if isinstance(r, list) and len(r) > 0:
            best_price = None
            total_stock = 0
            for op in r:
                p = float(op.get("price", 0))
                c = int(op.get("count", 0))
                total_stock += c
                if c > 0 and (best_price is None or p < best_price):
                    best_price = p
            if best_price and total_stock > 0:
                # Vak-SMS prices are in RUB, convert: 1 RUB ≈ 1 INR (approx), apply margin
                sell = math.ceil(best_price * MARGIN)
                return sell, total_stock
    except Exception as e:
        logger.warning(f"Vak-SMS price: {e}")
    return None, 0

def best_price(cc, api):
    """Returns (sell_price, stock, source) — cheapest available, margin hidden"""
    k = f"{cc}|{api}"
    c = _pc.get(k)
    if c and time.time() - c[3] < 1800:
        return c[0], c[1], c[2]
    psp, ssp = _smspool_price(cc, api)
    pvk, svk = _vaksms_price(cc, api)
    res = None
    if psp and ssp > 0 and pvk and svk > 0:
        res = (psp, ssp, 'smspool') if psp <= pvk else (pvk, svk, 'vaksms')
    elif psp and ssp > 0:
        res = (psp, ssp, 'smspool')
    elif pvk and svk > 0:
        res = (pvk, svk, 'vaksms')
    if res:
        _pc[k] = (*res, time.time())
        return res
    return None, 0, None

def find_svc(key):
    for cat, items in SERVICES.items():
        if key in items:
            return items[key], cat
    return None, None

# ── DUAL BUY ──────────────────────────────────────────────────────────────────
def _buy_smspool(cc, api):
    try:
        country = SMSPOOL_CC.get(cc)
        service = SMSPOOL_SVC.get(api)
        if not country or not service: return None, None
        r = requests.get(
            "https://api.smspool.net/purchase/sms",
            params={"key": SMSPOOL_KEY, "country": country, "service": service},
            timeout=15
        ).json()
        if r.get("success"):
            return r.get("order_id"), r.get("phonenumber")
    except Exception as e:
        logger.error(f"SmsPool buy: {e}")
    return None, None

def _buy_vaksms(cc, api):
    try:
        country = VAKSMS_CC.get(cc)
        service = VAKSMS_SVC.get(api)
        if not country or not service: return None, None
        r = requests.get(
            "https://vak-sms.com/api/getSim/",
            params={"apiKey": VAKSMS_KEY, "service": service, "country": country},
            timeout=15
        ).json()
        if r.get("idNum"):
            return r.get("idNum"), r.get("tel")
    except Exception as e:
        logger.error(f"Vak-SMS buy: {e}")
    return None, None

def smart_buy(cc, api):
    """Try SmsPool first, fallback to Vak-SMS"""
    if SMSPOOL_KEY:
        oid, num = _buy_smspool(cc, api)
        if oid and num:
            return oid, num, 'smspool'
    if VAKSMS_KEY:
        oid, num = _buy_vaksms(cc, api)
        if oid and num:
            return oid, num, 'vaksms'
    return None, None, None

# ── OTP CHECK ─────────────────────────────────────────────────────────────────
def check_otp(oid, source):
    try:
        if source == 'smspool':
            r = requests.get(
                "https://api.smspool.net/sms/check",
                params={"key": SMSPOOL_KEY, "orderid": oid},
                timeout=10
            ).json()
            if r.get("sms"): return r["sms"]
        elif source == 'vaksms':
            r = requests.get(
                "https://vak-sms.com/api/getSmsCode/",
                params={"apiKey": VAKSMS_KEY, "idNum": oid},
                timeout=10
            ).json()
            if r.get("smsCode"): return r["smsCode"]
    except Exception as e:
        logger.error(f"OTP check: {e}")
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

# ── DB HELPERS ─────────────────────────────────────────────────────────────────
def get_user(uid, uname=None, fname=None):
    try:
        users_col.find_one_and_update(
            {"user_id": uid},
            {"$setOnInsert": {
                "user_id":     uid,
                "username":    uname or "",
                "full_name":   fname or "",
                "balance":     0.0,
                "total_spent": 0.0,
                "orders":      0,
                "banned":      False,
                "joined_at":   datetime.utcnow()
            }},
            upsert=True,
            return_document=True
        )
        if uname or fname:
            updates = {}
            if uname: updates["username"]  = uname
            if fname: updates["full_name"] = fname
            if updates:
                users_col.update_one({"user_id": uid}, {"$set": updates})
        return users_col.find_one({"user_id": uid})
    except Exception as e:
        logger.error(f"get_user error: {e}")
        return {"user_id":uid,"balance":0,"total_spent":0,"orders":0,"banned":False}

def is_banned(uid):
    u = users_col.find_one({"user_id": uid})
    return bool(u and u.get("banned"))

def add_balance(uid, amount):
    try:
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": amount}}, upsert=False)
        return True
    except Exception as e:
        logger.error(f"add_balance error: {e}")
        return False

def deduct_balance(uid, amount):
    try:
        result = users_col.update_one(
            {"user_id": uid, "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount, "orders": 1, "total_spent": amount}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"deduct_balance error: {e}")
        return False

def log_order(uid, cat, svc, num, oid, sell, source):
    try:
        orders_col.insert_one({
            "user_id":uid,"category":cat,
            "service":f"{svc['flag']} {svc['country']} {cat}",
            "api":svc['api'],"cc":svc['cc'],
            "number":num,"order_id":str(oid),
            "amount":sell,"source":source,
            "profit": round(sell * (1 - 1/MARGIN), 2),
            "status":"pending","otp":None,
            "created_at":datetime.utcnow()
        })
    except Exception as e: logger.error(f"log_order: {e}")

# ── FORCE JOIN ────────────────────────────────────────────────────────────────
def is_joined(uid):
    ok = ['member','administrator','creator']
    for ch_id, _, _ in CH:
        try:
            if bot.get_chat_member(ch_id, uid).status not in ok: return False
        except: pass
    try:
        if bot.get_chat_member(GROUP_ID, uid).status not in ok: return False
    except: pass
    return True

def join_markup():
    m = types.InlineKeyboardMarkup(row_width=1)
    for ch_id, ch_link, ch_name in CH:
        m.add(types.InlineKeyboardButton(f"📢 {ch_name} Join Karein ✅", url=ch_link))
    m.add(types.InlineKeyboardButton("👥 Group Join Karein ✅", url=GROUP_LINK))
    m.add(types.InlineKeyboardButton("🔄 Join Kiya — Verify Karein", callback_data="check_join"))
    return m

# ── DECORATORS ────────────────────────────────────────────────────────────────
def ban_check(fn):
    def w(msg):
        if is_banned(msg.from_user.id):
            bot.send_message(msg.chat.id, "🚫 *Aap ban hain!*\n" + SUPPORT_BOT); return
        fn(msg)
    return w

def join_check(fn):
    def w(msg):
        uid = msg.from_user.id
        if uid == OWNER_ID: fn(msg); return
        if not is_joined(uid):
            bot.send_message(msg.chat.id, "⚠️ *Pehle join karein:*", reply_markup=join_markup()); return
        fn(msg)
    return w

def gaali_check(fn):
    def w(msg):
        if msg.from_user.id == OWNER_ID: fn(msg); return
        if any(x in (msg.text or "").lower() for x in BAD_WORDS):
            uid = msg.from_user.id
            users_col.update_one({"user_id": uid}, {"$set": {"banned": True}})
            bot.send_message(uid, f"🚫 *Block!*\nGaali=ban.\nAppeal: {SUPPORT_BOT}")
            try: bot.send_message(OWNER_ID, f"⚠️ Auto-Ban\n👤{msg.from_user.first_name}\n🆔`{uid}`\n💬`{msg.text}`")
            except: pass
            return
        fn(msg)
    return w

def oo(fn):
    def w(msg):
        if msg.from_user.id != OWNER_ID: return
        fn(msg)
    return w

# ── KEYBOARDS ─────────────────────────────────────────────────────────────────
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
    m.add("🔙 Back")
    return m

# ══════════════════════════════════════════════════════════════════════════════
#  /start  —  CLEAN WELCOME (no margin/api info leaked)
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    get_user(uid, msg.from_user.username, msg.from_user.first_name)
    if uid != OWNER_ID and not is_joined(uid):
        bot.send_message(uid, "⚠️ *OtpKing Bot*\n\nPehle join karein 👇", reply_markup=join_markup()); return
    _greet(uid, msg.from_user.first_name or "Dost")

def _greet(uid, name):
    """Clean welcome — only basic info, no platform/margin details"""
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
        bot.answer_callback_query(call.id, "❌ Sabhi join nahi kiye!", show_alert=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BUY NUMBER — Clean flow, no margin shown
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📲 Buy Number")
@ban_check
@join_check
def buy_number(msg):
    """Direct to service selection — no API info shown"""
    bot.send_message(msg.chat.id, "📲 *Service chunein:*", reply_markup=buy_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def go_back(msg):
    bot.send_message(msg.chat.id, "🏠", reply_markup=main_menu(msg.from_user.id))

@bot.message_handler(func=lambda m: m.text in ALL_BTNS)
@ban_check
@join_check
def show_countries(msg):
    """Show countries — only flag+name+price, no stock count/source shown to user"""
    cat = msg.text; items = SERVICES.get(cat, {})
    lm = bot.send_message(msg.chat.id, f"⏳ *{cat}*\nCountry chunein...")
    mk = types.InlineKeyboardMarkup(row_width=1)
    for key, info in items.items():
        sell, cnt, src = best_price(info['cc'], info['api'])
        if sell and cnt > 0:
            # User ko sirf flag + country + price dikhao, koi bhi extra info nahi
            mk.add(types.InlineKeyboardButton(
                f"{info['flag']} {info['country']}  ·  ₹{sell}",
                callback_data=f"buy_{key}"))
        else:
            mk.add(types.InlineKeyboardButton(
                f"{info['flag']} {info['country']}  ·  ❌ Unavailable",
                callback_data="oos"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="go_back_menu"))
    bot.edit_message_text(f"*{cat}* — Country chunein:", lm.chat.id, lm.message_id, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "oos")
def cb_oos(call):
    bot.answer_callback_query(call.id, "❌ Is country mein abhi stock nahi!\nThodi der baad try karein.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "go_back_menu")
def cb_back(call):
    bot.send_message(call.message.chat.id, "🏠", reply_markup=main_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def cb_buy(call):
    uid = call.from_user.id
    if is_banned(uid): return bot.answer_callback_query(call.id, "🚫 Ban.", show_alert=True)
    if not is_joined(uid) and uid != OWNER_ID:
        return bot.answer_callback_query(call.id, "⚠️ Pehle join karein!", show_alert=True)
    key = call.data[4:]
    svc, cat = find_svc(key)
    if not svc: return bot.answer_callback_query(call.id, "❌ Invalid.", show_alert=True)
    sell, cnt, src = best_price(svc['cc'], svc['api'])
    if not sell or cnt == 0:
        return bot.answer_callback_query(call.id, "❌ Abhi stock nahi!\nThodi der mein try karein.", show_alert=True)
    u = get_user(uid)
    if u.get('balance', 0) < sell:
        short = sell - u.get('balance', 0)
        return bot.answer_callback_query(call.id,
            f"❌ Balance kam hai!\nChahiye: ₹{sell:.0f}\nHai: ₹{u.get('balance',0):.0f}\nAur chahiye: ₹{short:.0f}\n\nWallet → Deposit karein!",
            show_alert=True)
    bot.answer_callback_query(call.id, "⏳ Number dhundh rahe hain...")
    sm = bot.send_message(call.message.chat.id,
        f"🔄 *Processing...*\n{svc['flag']} {svc['country']} {cat}\n💵 ₹{sell:.0f} balance se katega")
    oid, num, used_src = smart_buy(svc['cc'], svc['api'])
    if oid and num:
        success = deduct_balance(uid, sell)
        if not success:
            cancel_order(str(oid), used_src)
            bot.edit_message_text("❌ Balance deduct failed. Try again.", call.message.chat.id, sm.message_id); return
        u2 = users_col.find_one({"user_id": uid}) or {}
        nb = u2.get('balance', 0)
        log_order(uid, cat, svc, num, oid, sell, used_src)
        bot.edit_message_text(
            f"✅ *Number Mila!*\n\n📞 `{num}`\n{svc['flag']} {svc['country']} {cat}\n"
            f"💵 ₹{sell:.0f} kata | Remaining: ₹{nb:.0f}\n\n"
            f"⏳ *OTP aa raha hai...* _(max 5 min)_\n_Nahi aaya to Auto Refund_",
            call.message.chat.id, sm.message_id)
        Thread(target=_otp_wait,
            args=(call.message.chat.id, uid, str(oid), sell, num, svc, cat, nb, used_src),
            daemon=True).start()
    else:
        bot.edit_message_text(
            f"❌ *Number Nahi Mila*\nAbhi stock available nahi.\n_Balance safe hai._",
            call.message.chat.id, sm.message_id)

def _otp_wait(cid, uid, oid, refund, num, svc, cat, rbal, source):
    for _ in range(30):
        time.sleep(10)
        otp = check_otp(oid, source)
        if otp:
            orders_col.update_one({"order_id": oid}, {"$set": {"status": "done", "otp": otp}})
            bot.send_message(cid,
                f"🎉 *OTP Aa Gaya!*\n\n📞 `{num}`\n{svc['flag']} {svc['country']} {cat}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n🔑 *OTP Code:* `{otp}`\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Balance: ₹{rbal:.0f}\n✅ Done! 🙏")
            Thread(target=_post_proof, args=(uid, num, svc, cat, refund, otp, source), daemon=True).start()
            return
    cancel_order(oid, source)
    orders_col.update_one({"order_id": oid}, {"$set": {"status": "cancelled"}})
    add_balance(uid, refund)
    bot.send_message(cid,
        f"❌ *OTP Timeout*\n📞 `{num}`\n5 min mein OTP nahi aaya.\n\n💰 *₹{refund:.0f} Auto Refund!*")

def _post_proof(uid, num, svc, cat, amt, otp, source):
    u = users_col.find_one({"user_id": uid}) or {}
    name = u.get('full_name') or f"User{str(uid)[-4:]}"
    masked = num[:4] + "****" + num[-2:] if len(num) > 6 else num
    src_n = "SmsPool" if source == 'smspool' else "Vak-SMS"
    text = (f"✅ *OTP Delivered!*\n\n📞 `{masked}`\n📍{svc['flag']} {svc['country']} {cat}\n"
            f"💵 ₹{amt:.0f}\n🔑 OTP: `{otp}`\n🔗 {src_n}\n👤{name}\n"
            f"🕐{datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC\n\n👑 *OtpKing Store*")
    for dest in [PROOF_CHANNEL_ID, GROUP_ID]:
        try: bot.send_message(dest, text)
        except Exception as e: logger.warning(f"Proof to {dest}: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  WALLET — Deposit flow with QR-first approach
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "💰 Wallet")
@ban_check
@join_check
def wallet(msg):
    u = get_user(msg.from_user.id)
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("💎 USDT Deposit", callback_data="d_usdt"),
        types.InlineKeyboardButton("🇮🇳 UPI / QR Deposit", callback_data="d_upi"),
        types.InlineKeyboardButton("📊 Transaction History", callback_data="d_hist"),
    )
    bot.send_message(msg.chat.id,
        f"💳 *Your Wallet*\n\n"
        f"🆔 `{msg.from_user.id}`\n"
        f"💵 Balance: *₹{u.get('balance',0):.0f}*\n"
        f"🛒 Orders: `{u.get('orders',0)}`\n"
        f"💸 Spent: `₹{u.get('total_spent',0):.0f}`\n\n"
        f"_Deposit karein → Number khareedein_", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "d_usdt")
def cb_usdt(call):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("💬 Admin se QR/Address Maangein",
        url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    m.add(types.InlineKeyboardButton("🔙 Back", callback_data="d_back"))
    bot.send_message(call.message.chat.id,
        "💎 *USDT Deposit*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "*Step 1:* Admin se pehle wallet address maangein 👇\n"
        f"   👉 {SUPPORT_BOT}\n\n"
        "*Step 2:* USDT bhejein (TRC20 network)\n\n"
        "*Step 3:* Screenshot yahan bhejein\n\n"
        "*Step 4:* Admin verify → Balance add!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⏱ 5-30 min | ⚠️ Bina confirm mat bhejein!", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "d_upi")
def cb_upi(call):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("💬 Admin se QR Code Maangein",
        url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    m.add(types.InlineKeyboardButton("🔙 Back", callback_data="d_back"))
    bot.send_message(call.message.chat.id,
        "🇮🇳 *UPI / QR Deposit*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "*Step 1:* Admin se pehle QR Code maangein 👇\n"
        f"   👉 {SUPPORT_BOT}\n\n"
        "*Step 2:* QR scan karke payment karein\n\n"
        "*Step 3:* Payment screenshot yahan bhejein\n\n"
        "*Step 4:* Admin verify → Balance add!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⏱ 5-15 min | Minimum: ₹50", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "d_back")
def cb_dep_back(call):
    u = get_user(call.from_user.id)
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("💎 USDT", callback_data="d_usdt"),
          types.InlineKeyboardButton("🇮🇳 UPI/QR", callback_data="d_upi"),
          types.InlineKeyboardButton("📊 History", callback_data="d_hist"))
    bot.send_message(call.message.chat.id,
        f"💳 Balance: *₹{u.get('balance',0):.0f}*", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "d_hist")
def cb_hist(call):
    orders = list(orders_col.find({"user_id": call.from_user.id}).sort("created_at", DESCENDING).limit(8))
    deps   = list(deposits_col.find({"user_id": call.from_user.id}).sort("created_at", DESCENDING).limit(5))
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
    else:
        t += "📭 Koi order nahi."
    bot.send_message(call.message.chat.id, t)

# ── Screenshot Handler ─────────────────────────────────────────────────────────
@bot.message_handler(content_types=['photo'])
def on_photo(msg):
    if msg.from_user.id == OWNER_ID: return
    deposits_col.insert_one({
        "user_id": msg.from_user.id, "username": msg.from_user.username or "",
        "full_name": msg.from_user.first_name or "", "amount": 0.0,
        "status": "pending", "method": "USDT/UPI",
        "message_id": msg.message_id, "created_at": datetime.utcnow()
    })
    bot.forward_message(OWNER_ID, msg.chat.id, msg.message_id)
    bot.send_message(OWNER_ID,
        f"📩 *Naya Deposit!*\n\n"
        f"👤 {msg.from_user.first_name} @{msg.from_user.username or 'N/A'}\n"
        f"🆔 `{msg.from_user.id}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ UPI approve:\n`/add {msg.from_user.id} AMOUNT`\n\n"
        f"✅ USDT approve:\n`/add {msg.from_user.id} AMOUNT usdt`\n\n"
        f"❌ Reject:\n`/reject {msg.from_user.id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━")
    bot.reply_to(msg,
        "✅ *Screenshot mila!*\n⏳ Admin verify karega.\n_15-30 min mein balance add hoga._")

# ══════════════════════════════════════════════════════════════════════════════
#  MY ORDERS
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📋 My Orders")
@ban_check
@join_check
def my_orders(msg):
    orders = list(orders_col.find({"user_id": msg.from_user.id}).sort("created_at", DESCENDING).limit(7))
    if not orders:
        bot.send_message(msg.chat.id, "📭 Koi order nahi.\nBuy Number button dabayein!"); return
    t = "📋 *Your Orders*\n\n"
    for o in orders:
        ic = "✅" if o['status'] == "done" else ("❌" if o['status'] == "cancelled" else "⏳")
        t += f"{ic} `{o['number']}`\n   {o['service']} ₹{o.get('amount',0):.0f}\n   {o['created_at'].strftime('%d %b %H:%M')}\n\n"
    bot.send_message(msg.chat.id, t)

# ══════════════════════════════════════════════════════════════════════════════
#  REFER & EARN — Multi-Platform System
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "👥 Refer & Earn")
@ban_check
@join_check
def refer(msg):
    """Show all earning platforms as buttons"""
    platforms = list(platforms_col.find())
    if not platforms:
        bot.send_message(msg.chat.id,
            "👥 *Refer & Earn*\n\n"
            "⚠️ Abhi koi platform add nahi hua.\n"
            "Admin se contact karein.", reply_markup=main_menu(msg.from_user.id))
        return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for p in platforms:
        mk.add(types.InlineKeyboardButton(
            f"💰 {p['name']}", callback_data=f"earn_plat_{str(p['_id'])}"))
    bot.send_message(msg.chat.id,
        "👥 *Refer & Earn*\n\n"
        "👇 Platform chunein — Registration link + Video tutorial milega:",
        reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("earn_plat_"))
def cb_earn_platform(call):
    """Show platform details with link and video"""
    from bson import ObjectId
    plat_id = call.data.replace("earn_plat_", "")
    try:
        p = platforms_col.find_one({"_id": ObjectId(plat_id)})
    except: p = None
    if not p:
        bot.answer_callback_query(call.id, "❌ Platform nahi mila!", show_alert=True); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("🔗 Register / Join Karein", url=p['link']))
    if p.get('video'):
        mk.add(types.InlineKeyboardButton("🎥 Video Tutorial Dekhein", url=p['video']))
    mk.add(types.InlineKeyboardButton("🔙 Wapas List Mein", callback_data="earn_back"))
    bot.send_message(call.message.chat.id,
        f"💰 *{p['name']}*\n\n"
        f"👇 Register karein aur earn karein!\n\n"
        f"🔗 Link: {p['link']}\n\n"
        f"_Platform details — Pura tutorial video mein hai!_",
        reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "earn_back")
def cb_earn_back(call):
    """Back to platform list"""
    platforms = list(platforms_col.find())
    if not platforms:
        bot.send_message(call.message.chat.id, "📭 Koi platform nahi.", reply_markup=main_menu(call.from_user.id)); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for p in platforms:
        mk.add(types.InlineKeyboardButton(f"💰 {p['name']}", callback_data=f"earn_plat_{str(p['_id'])}"))
    bot.send_message(call.message.chat.id,
        "👥 *Refer & Earn*\n\n👇 Platform chunein:",
        reply_markup=mk)

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — Multi-Step Platform Adder (/add_platform)
# ══════════════════════════════════════════════════════════════════════════════
_add_plat_state = {}  # {admin_id: {step: 1, name: None, link: None, video: None}}

@bot.message_handler(commands=['add_platform'])
@oo
def cmd_add_platform(msg):
    """Step-by-step platform adder"""
    _add_plat_state[OWNER_ID] = {"step": 1}
    bot.send_message(msg.chat.id,
        "➕ *Naya Earning Platform Add Karein*\n\n"
        "*Step 1/3:* Platform ka naam kya hai?\n\n"
        "_Example: WhatsApp Business, Amazon Associate_\n\n"
        "(/cancel - cancel karne ke liye)")

@bot.message_handler(commands=['cancel'])
@oo
def cmd_cancel(msg):
    _add_plat_state.pop(OWNER_ID, None)
    bot.reply_to(msg, "✅ Cancel ho gaya.")

@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and OWNER_ID in _add_plat_state)
def handle_platform_add_steps(msg):
    """Handle multi-step platform adding"""
    if msg.text and msg.text.startswith('/'): return  # skip commands
    state = _add_plat_state.get(OWNER_ID, {})
    step = state.get("step", 0)

    if step == 1:
        state["name"] = msg.text.strip()
        state["step"] = 2
        _add_plat_state[OWNER_ID] = state
        bot.send_message(msg.chat.id,
            f"✅ Naam: *{state['name']}*\n\n"
            "*Step 2/3:* Registration / Joining link bhejein:\n\n"
            "_Example: https://wa.me/91XXXXXXXXXX_")

    elif step == 2:
        link = msg.text.strip()
        if not link.startswith("http"):
            bot.send_message(msg.chat.id, "❌ Valid URL chahiye (https:// se shuru ho)")
            return
        state["link"] = link
        state["step"] = 3
        _add_plat_state[OWNER_ID] = state
        bot.send_message(msg.chat.id,
            f"✅ Link: `{link}`\n\n"
            "*Step 3/3:* Video tutorial link bhejein:\n\n"
            "_Example: https://youtu.be/xxxxx_\n"
            "_Video nahi hai to 'skip' likho_")

    elif step == 3:
        video = msg.text.strip()
        if video.lower() == "skip":
            video = None
        elif not video.startswith("http"):
            bot.send_message(msg.chat.id, "❌ Valid URL chahiye ya 'skip' likho")
            return
        state["video"] = video
        # Save to MongoDB
        result = platforms_col.insert_one({
            "name":       state["name"],
            "link":       state["link"],
            "video":      state.get("video"),
            "added_at":   datetime.utcnow(),
        })
        _add_plat_state.pop(OWNER_ID, None)
        bot.send_message(msg.chat.id,
            f"✅ *Platform Add Ho Gaya!*\n\n"
            f"📛 Naam: *{state['name']}*\n"
            f"🔗 Link: `{state['link']}`\n"
            f"🎥 Video: {state.get('video') or 'N/A'}\n\n"
            f"_Ab users 'Refer & Earn' mein dekh sakte hain!_")

# Admin: View all platforms
@bot.message_handler(commands=['list_platforms'])
@oo
def cmd_list_platforms(msg):
    platforms = list(platforms_col.find())
    if not platforms:
        bot.send_message(msg.chat.id, "📭 Koi platform nahi.")
        return
    t = "📋 *Earning Platforms*\n\n"
    for i, p in enumerate(platforms, 1):
        t += f"{i}. *{p['name']}*\n🔗 {p['link']}\n🎥 {p.get('video','N/A')}\n🗑 `/del_plat_{str(p['_id'])}`\n\n"
    bot.send_message(msg.chat.id, t)

# Admin: Delete platform by command
@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.text and m.text.startswith('/del_plat_'))
def cmd_del_platform(msg):
    from bson import ObjectId
    plat_id = msg.text.replace('/del_plat_', '').strip()
    try:
        platforms_col.delete_one({"_id": ObjectId(plat_id)})
        bot.reply_to(msg, "✅ Platform delete ho gaya.")
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  HELP / PROOF / SUPPORT
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text in ["🆘 Help", "❓ Help"])
def help_btn(msg):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton(f"🤖 {SUPPORT_BOT}", url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"),
          types.InlineKeyboardButton("📢 Proof Channel", url=PROOF_CHANNEL_LINK),
          types.InlineKeyboardButton("👥 Group", url=GROUP_LINK))
    bot.send_message(msg.chat.id,
        "❓ *Help*\n\n"
        "🔹 *Number kaise khareedein?*\n   Buy Number → Service → Country\n\n"
        "🔹 *Balance kaise add karein?*\n   Wallet → USDT/UPI → Admin se QR maangein → Screenshot bhejein\n\n"
        "🔹 *OTP nahi aaya?*\n   5 min wait → Auto Refund\n\n"
        f"🆘 {SUPPORT_BOT} 👇", reply_markup=m)

@bot.message_handler(func=lambda m: m.text == "📊 Proof")
def proof_btn(msg):
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("📢 Proof Channel", url=PROOF_CHANNEL_LINK))
    bot.send_message(msg.chat.id,
        "📊 *Proof*\n\n✅ Har OTP aur deposit automatically post hota hai!", reply_markup=m)

@bot.message_handler(func=lambda m: m.text == "📞 Support")
def support_btn(msg):
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton(f"💬 {SUPPORT_BOT}", url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    bot.send_message(msg.chat.id, f"📞 *Support*\n{SUPPORT_BOT}\n⏰ 10AM-10PM IST", reply_markup=m)

# ══════════════════════════════════════════════════════════════════════════════
#  OWNER COMMANDS
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(commands=['add'])
@oo
def cmd_add(msg):
    try:
        parts = msg.text.split()
        uid = int(parts[1]); amount = float(parts[2])
        method = parts[3].upper() if len(parts) > 3 else "UPI"
        success = add_balance(uid, amount)
        if not success:
            bot.reply_to(msg, f"❌ User `{uid}` exist nahi karta!"); return
        deposits_col.update_one(
            {"user_id": uid, "status": "pending"},
            {"$set": {"status": "approved", "amount": amount, "method": method}},
            sort=[("created_at", -1)])
        u = users_col.find_one({"user_id": uid}) or {}
        new_bal = u.get('balance', amount)
        bot.send_message(uid,
            f"🎉 *Deposit Approved!*\n\n"
            f"{'💎 USDT' if method=='USDT' else '🇮🇳 UPI'} → *₹{amount:.0f}* wallet mein add!\n\n"
            f"💵 *Naya Balance: ₹{new_bal:.0f}*\n\n"
            f"Ab number khareedein 👇\nBuy Number button dabayein 🛒")
        try:
            bot.send_message(PROOF_CHANNEL_ID,
                f"✅ *Deposit Approved!*\n{method} → ₹{amount:.0f}\n"
                f"👤 User `{uid}`\n🕐{datetime.utcnow().strftime('%d %b %H:%M')} UTC\n👑 OtpKing")
        except: pass
        bot.reply_to(msg, f"✅ ₹{amount:.0f} added to `{uid}`\nNew balance: ₹{new_bal:.0f}")
    except Exception as e:
        bot.reply_to(msg,
            f"❌ Error: {e}\n\nFormat:\n`/add USER_ID AMOUNT`\n`/add USER_ID AMOUNT usdt`")

@bot.message_handler(commands=['reject'])
@oo
def cmd_reject(msg):
    try:
        uid = int(msg.text.split()[1])
        deposits_col.update_one({"user_id": uid, "status": "pending"},
            {"$set": {"status": "rejected"}}, sort=[("created_at", -1)])
        bot.send_message(uid, f"❌ *Deposit Reject.*\nScreenshot unclear tha.\nRetry: {SUPPORT_BOT}")
        bot.reply_to(msg, f"✅ Rejected `{uid}`")
    except: bot.reply_to(msg, "❌ `/reject USER_ID`")

@bot.message_handler(commands=['deduct'])
@oo
def cmd_deduct(msg):
    try:
        _, uid, amt = msg.text.split()
        add_balance(int(uid), -float(amt))
        bot.reply_to(msg, f"✅ ₹{amt} deducted from `{uid}`")
    except: bot.reply_to(msg, "❌ `/deduct USER_ID AMOUNT`")

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
    t = msg.text.replace('/broadcast', '', 1).strip()
    if not t: bot.reply_to(msg, "❌ `/broadcast MSG`"); return
    _do_broadcast(msg.chat.id, t)

@bot.message_handler(commands=['stats'])
@oo
def cmd_stats(msg): _send_stats(msg.chat.id)

@bot.message_handler(commands=['userinfo'])
@oo
def cmd_uinfo(msg):
    try: _send_uinfo(msg.chat.id, int(msg.text.split()[1]))
    except: bot.reply_to(msg, "❌ `/userinfo USER_ID`")

@bot.message_handler(commands=['balance'])
@oo
def cmd_check_bal(msg):
    try:
        uid = int(msg.text.split()[1])
        u = users_col.find_one({"user_id": uid}) or {}
        bot.reply_to(msg,
            f"👤 User `{uid}`\n"
            f"💵 Balance: ₹{u.get('balance',0):.0f}\n"
            f"🛒 Orders: {u.get('orders',0)}")
    except: bot.reply_to(msg, "❌ `/balance USER_ID`")

# ── Admin Panel ───────────────────────────────────────────────────────────────
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
    bot.send_message(msg.chat.id,
        f"👥 *Users*\nTotal: `{tu}` | Active: `{ac}` | Banned: `{bn}`")

@bot.message_handler(func=lambda m: m.text == "📋 Pending Dep" and m.from_user.id == OWNER_ID)
def ab_pending(msg):
    pds = list(deposits_col.find({"status": "pending"}).sort("created_at", DESCENDING).limit(10))
    if not pds: bot.send_message(msg.chat.id, "📭 Koi pending nahi."); return
    t = "📋 *Pending Deposits*\n\n"
    for d in pds:
        t += (f"👤 {d.get('full_name','?')} @{d.get('username','?')}\n"
              f"🆔 `{d['user_id']}`\n"
              f"🕐 {d['created_at'].strftime('%d %b %H:%M')}\n"
              f"✅ `/add {d['user_id']} AMOUNT`\n"
              f"❌ `/reject {d['user_id']}`\n\n")
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "💹 API Balances" and m.from_user.id == OWNER_ID)
def ab_api_bal(msg):
    results = []
    # SmsPool balance
    try:
        r = requests.get(f"https://api.smspool.net/request/balance?key={SMSPOOL_KEY}", timeout=8).json()
        bal = r.get("balance", "?")
        results.append(f"✅ SmsPool: ${bal}")
    except Exception as e:
        results.append(f"❌ SmsPool: {str(e)[:30]}")
    # Vak-SMS balance
    try:
        r = requests.get(f"https://vak-sms.com/api/getBalance/?apiKey={VAKSMS_KEY}", timeout=8).json()
        bal = r.get("balance", "?")
        results.append(f"✅ Vak-SMS: ₽{bal}")
    except Exception as e:
        results.append(f"❌ Vak-SMS: {str(e)[:30]}")
    bot.send_message(msg.chat.id, "💹 *API Balances*\n\n" + "\n".join(results))

@bot.message_handler(func=lambda m: m.text == "🔑 API Keys" and m.from_user.id == OWNER_ID)
def ab_keys(msg):
    results = []
    results.append(f"{'✅' if SMSPOOL_KEY else '❌'} SMSPOOL_API_KEY → {'Set ✅' if SMSPOOL_KEY else 'NOT SET ❌'}")
    results.append(f"{'✅' if VAKSMS_KEY else '❌'} VAKSMS_API_KEY → {'Set ✅' if VAKSMS_KEY else 'NOT SET ❌'}")
    results.append(f"✅ OWNER_ID → `{OWNER_ID}`")
    try:
        users_col.find_one()
        results.append(f"✅ MONGO_URI → Connected ({users_col.count_documents({})} users)")
    except Exception as e:
        results.append(f"❌ MONGO_URI → {str(e)[:40]}")
    bot.send_message(msg.chat.id, "🔑 *API Keys Status*\n\n" + "\n".join(results))

@bot.message_handler(func=lambda m: m.text == "📡 Channels" and m.from_user.id == OWNER_ID)
def ab_channels(msg):
    bid = bot.get_me().id; results = []
    for i, (ch_id, ch_link, ch_name) in enumerate(CH, 1):
        try:
            c = bot.get_chat(ch_id); bm = bot.get_chat_member(ch_id, bid)
            adm = bm.status in ['administrator', 'creator']
            results.append(f"{'✅' if adm else '⚠️'} {ch_name}:`{ch_id}`\n   📛{c.title}\n   🤖{'Admin✅' if adm else 'NO ADMIN❌'}")
        except Exception as e:
            results.append(f"❌ {ch_name}: {str(e)[:40]}")
    bot.send_message(msg.chat.id, "📡 *Channels*\n\n" + "\n\n".join(results))

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.from_user.id == OWNER_ID)
def ab_bc(msg): bot.send_message(msg.chat.id, "📢 `/broadcast Your message`")

@bot.message_handler(func=lambda m: m.text == "🏆 Top Buyers" and m.from_user.id == OWNER_ID)
def ab_top(msg):
    r = list(orders_col.aggregate([
        {"$match": {"status": "done"}},
        {"$group": {"_id": "$user_id", "total": {"$sum": "$amount"}, "cnt": {"$sum": 1}}},
        {"$sort": {"total": -1}}, {"$limit": 10}]))
    if not r: bot.send_message(msg.chat.id, "📭"); return
    t = "🏆 *Top 10*\n\n"
    for i, x in enumerate(r, 1):
        u = users_col.find_one({"user_id": x['_id']}) or {}
        t += f"{i}. {u.get('full_name','N/A')} — ₹{x['total']:.0f} ({x['cnt']} orders)\n"
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "📦 Orders" and m.from_user.id == OWNER_ID)
def ab_orders(msg):
    orders = list(orders_col.find().sort("created_at", DESCENDING).limit(10))
    if not orders: bot.send_message(msg.chat.id, "📭"); return
    t = "📦 *Recent Orders*\n\n"
    for o in orders:
        ic = "✅" if o['status'] == "done" else ("❌" if o['status'] == "cancelled" else "⏳")
        src = "🌐" if o.get('source') == 'smspool' else "🔷"
        t += f"{ic}{src} `{o['number']}` {o['service']}\n👤`{o['user_id']}` ₹{o.get('amount',0):.0f} {o['created_at'].strftime('%d %b %H:%M')}\n\n"
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "📈 Stock" and m.from_user.id == OWNER_ID)
def ab_stock(msg):
    bot.send_message(msg.chat.id, "⏳ Stock check ho raha hai..."); _stock_report(msg.chat.id)

@bot.message_handler(func=lambda m: m.text == "➕ Platform Add" and m.from_user.id == OWNER_ID)
def ab_add_plat(msg):
    _add_plat_state[OWNER_ID] = {"step": 1}
    bot.send_message(msg.chat.id,
        "➕ *Naya Earning Platform Add Karein*\n\n"
        "*Step 1/3:* Platform ka naam kya hai?\n\n"
        "_Example: Amazon Associate, Meesho_")

@bot.message_handler(func=lambda m: m.text == "💾 Export" and m.from_user.id == OWNER_ID)
def ab_export(msg):
    users = list(users_col.find({}, {"user_id":1,"username":1,"full_name":1,"balance":1,"orders":1,"banned":1}))
    lines = ["ID|Name|Username|Balance|Orders|Banned"]
    lines += [f"{u['user_id']}|{u.get('full_name','N/A')}|@{u.get('username','N/A')}|₹{u.get('balance',0):.0f}|{u.get('orders',0)}|{u.get('banned',False)}" for u in users]
    f = io.BytesIO("\n".join(lines).encode()); f.name = f"users_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.txt"
    bot.send_document(msg.chat.id, f, caption=f"📦 Total: {len(users)} users")

@bot.message_handler(func=lambda m: m.text == "🔙 Back" and m.from_user.id == OWNER_ID)
def ab_back(msg): bot.send_message(msg.chat.id, "🏠", reply_markup=main_menu(OWNER_ID))

# ── Internal helpers ───────────────────────────────────────────────────────────
def _send_stats(cid):
    tu = users_col.count_documents({}); bu = users_col.count_documents({"banned": True})
    to = orders_col.count_documents({}); do = orders_col.count_documents({"status": "done"})
    co = orders_col.count_documents({"status": "cancelled"})
    pd = deposits_col.count_documents({"status": "pending"})
    agg = list(orders_col.aggregate([
        {"$match": {"status": "done"}},
        {"$group": {"_id": "$source", "rev": {"$sum": "$amount"}, "cnt": {"$sum": 1}}}]))
    rev_sp = rev_vk = 0; cnt_sp = cnt_vk = 0
    for x in agg:
        if x['_id'] == 'smspool': rev_sp = x['rev']; cnt_sp = x['cnt']
        elif x['_id'] == 'vaksms': rev_vk = x['rev']; cnt_vk = x['cnt']
    # Admin ko margin/profit bhi dikhao
    total_rev = rev_sp + rev_vk
    profit_est = round(total_rev * (1 - 1/MARGIN), 0)
    bot.send_message(cid,
        f"📊 *Bot Statistics*\n\n"
        f"👥 Users:         `{tu}` (🚫{bu})\n"
        f"🛒 Total Orders:  `{to}` ✅{do} ❌{co}\n"
        f"📥 Pending Dep:   `{pd}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 SmsPool:       `₹{rev_sp:.0f}` ({cnt_sp} orders)\n"
        f"🔷 Vak-SMS:       `₹{rev_vk:.0f}` ({cnt_vk} orders)\n"
        f"💰 Total Revenue: `₹{total_rev:.0f}`\n"
        f"📈 Est. Profit:   `₹{profit_est:.0f}` (40% margin)")

def _send_uinfo(cid, uid):
    u = get_user(uid); uo = orders_col.count_documents({"user_id": uid, "status": "done"})
    bot.send_message(cid,
        f"👤 *User Info*\n🆔`{u['user_id']}`\n"
        f"📛{u.get('full_name','N/A')} @{u.get('username','N/A')}\n"
        f"💵 Balance: `₹{u.get('balance',0):.0f}`\n"
        f"🛒 Orders: `{uo}` | 💸 Spent: `₹{u.get('total_spent',0):.0f}`\n"
        f"🚫 Banned: `{u.get('banned',False)}`\n"
        f"📅 Joined: `{str(u.get('joined_at',''))[:10]}`")

def _do_broadcast(cid, text):
    all_u = list(users_col.find({"banned": {"$ne": True}}))
    pm = bot.send_message(cid, f"📢 {len(all_u)} users ko bhej rahe hain...")
    s = f = 0
    for u in all_u:
        try: bot.send_message(u['user_id'], f"📢 *Announcement*\n\n{text}"); s += 1
        except: f += 1
        time.sleep(0.05)
    bot.edit_message_text(f"✅ Sent:`{s}` Failed:`{f}`", cid, pm.message_id)

def _stock_report(cid):
    """Admin-only — shows full details including stock count"""
    checks = [
        ("WhatsApp","russia","whatsapp","🇷🇺"),("WhatsApp","india","whatsapp","🇮🇳"),
        ("WhatsApp","usa","whatsapp","🇺🇸"),("WhatsApp","uk","whatsapp","🇬🇧"),
        ("Telegram","russia","telegram","🇷🇺"),("Telegram","india","telegram","🇮🇳"),
        ("Instagram","russia","instagram","🇷🇺"),("Gmail","russia","google","🇷🇺")]
    t = "📈 *Dual API Stock (Admin Only)*\n\n"; lows = []
    for svc, cc, api, flag in checks:
        _pc.pop(f"{cc}|{api}", None)
        psp, ssp = _smspool_price(cc, api)
        pvk, svk = _vaksms_price(cc, api)
        total = ssp + svk
        ic = "🔴" if total <= LOW_STOCK else ("🟡" if total <= 20 else "🟢")
        best = min([x for x in [psp, pvk] if x], default=None)
        if total > 0:
            t += f"{ic}{flag} {cc.title()} {svc}: 🌐{ssp}+🔷{svk}={total} | ₹{best or '?'}\n"
            if total <= LOW_STOCK: lows.append(f"{flag}{cc.title()} {svc}: {total} left!")
        else:
            t += f"⚫{flag} {cc.title()} {svc}: Both APIs Out!\n"
    t += f"\n🌐=SmsPool 🔷=VakSMS\n_{datetime.utcnow().strftime('%H:%M')} UTC_"
    bot.send_message(cid, t)
    if lows:
        bot.send_message(OWNER_ID,
            "⚠️ *LOW STOCK!*\n\n" + "\n".join(lows) +
            "\n\nSmsPool: https://smspool.net\nVak-SMS: https://vak-sms.com")

def _stock_monitor():
    while True:
        time.sleep(1800)
        try:
            lows = []
            for svc, cc, api, flag in [
                ("WhatsApp","russia","whatsapp","🇷🇺"),("WhatsApp","india","whatsapp","🇮🇳"),
                ("Telegram","russia","telegram","🇷🇺"),("Telegram","india","telegram","🇮🇳")]:
                _pc.pop(f"{cc}|{api}", None)
                psp, ssp = _smspool_price(cc, api)
                pvk, svk = _vaksms_price(cc, api)
                if ssp + svk <= LOW_STOCK:
                    lows.append(f"{flag}{cc.title()} {svc}: {ssp+svk} left!")
            if lows:
                bot.send_message(OWNER_ID,
                    "⚠️ *LOW STOCK!*\n\n" + "\n".join(lows) +
                    "\n\nSmsPool: https://smspool.net\nVak-SMS: https://vak-sms.com")
        except Exception as e: logger.error(f"Stock monitor: {e}")

# ── Fallback ────────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True)
@gaali_check
def fallback(msg):
    bot.send_message(msg.chat.id, "❓ Buttons use karein 👇", reply_markup=main_menu(msg.from_user.id))

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("👑 OtpKing Pro (SmsPool + Vak-SMS) starting...")
    Thread(target=_stock_monitor, daemon=True).start()
    retry = 0
    while True:
        try:
            logger.info(f"✅ Polling (attempt {retry+1})")
            bot.polling(none_stop=True, interval=0, timeout=20)
            retry = 0
        except Exception as e:
            retry += 1; wait = min(retry * 5, 30)
            logger.error(f"Polling error: {e}")
            time.sleep(wait); clear_session()
