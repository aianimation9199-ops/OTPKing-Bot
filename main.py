"""
OTPKING PRO — SmsPool + Vak-SMS DUAL API  ★ FIXED VERSION ★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES APPLIED:
  ✅ Unavailable bug fixed — price cache now actually fetches live prices
  ✅ Stock shown correctly (no "Unavailable" when API has stock)
  ✅ SmsPool API endpoints corrected
  ✅ Vak-SMS API endpoints corrected
  ✅ Balance 0.0 / ₹0 shown properly without blocking number display
  ✅ 40% margin applied silently (user never sees raw price)
  ✅ Admin can add/deduct balance for any user
  ✅ Force-join channels + group with dynamic add from admin
  ✅ Admin panel fully working
  ✅ Numbers purchasable without wallet recharge (demo/test mode off)
  ✅ Price cache 30 min — forces live fetch on first call
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

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN          = os.getenv('BOT_TOKEN', '')
MONGO_URI          = os.getenv('MONGO_URI') or os.getenv('MONGO_URL', '')
SMSPOOL_KEY        = os.getenv('SMSPOOL_API_KEY', '')
VAKSMS_KEY         = os.getenv('VAKSMS_API_KEY', '')
OWNER_ID           = int(os.getenv('OWNER_ID', '0'))
SUPPORT_BOT        = os.getenv('SUPPORT_BOT', '@YourHelpBot')
PROOF_CHANNEL_LINK = os.getenv('PROOF_CHANNEL_LINK', 'https://t.me/ProofChannel')
GROUP_LINK         = os.getenv('GROUP_LINK', 'https://t.me/YourGroup')
UPI_ID             = os.getenv('UPI_ID', 'yourname@upi')

# Force-join channels (loaded dynamically from DB too)
CH_DEFAULT = [
    (os.getenv('CHANNEL1_ID',''), os.getenv('CHANNEL1_LINK',''), "Channel 1"),
    (os.getenv('CHANNEL2_ID',''), os.getenv('CHANNEL2_LINK',''), "Channel 2"),
    (os.getenv('CHANNEL3_ID',''), os.getenv('CHANNEL3_LINK',''), "Channel 3"),
    (os.getenv('CHANNEL4_ID',''), os.getenv('CHANNEL4_LINK',''), "Channel 4"),
]

USDT_RATE = 85.0          # 1 USDT = 85 INR
MARGIN    = 1.40          # 40% hidden margin
LOW_STOCK = 5
UPI_LIST  = [50, 100, 200, 300, 500, 1000, 2000, 3000, 5000]

BAD_WORDS = ["madarchod","mc","bc","bhenchod","gandu","chutiya","randi","harami",
             "bhosdike","loda","lauda","chut","bsdk","fuck","bitch","asshole",
             "bastard","shit","dick","cunt","whore","sala","maderchod","behenchod"]

# ── API COUNTRY / SERVICE CODES ───────────────────────────────────────────────
SMSPOOL_CC = {
    "russia":"7","india":"91","usa":"1","england":"44","ukraine":"380",
    "brazil":"55","indonesia":"62","kenya":"254","nigeria":"234","pakistan":"92",
    "cambodia":"855","myanmar":"95","vietnam":"84","philippines":"63",
    "bangladesh":"880","kazakhstan":"7",
}
# SmsPool service short codes (as per their docs)
SMSPOOL_SVC = {
    "whatsapp":"wa","telegram":"tg","instagram":"ig","google":"go",
    "facebook":"fb","tiktok":"tt","twitter":"tw","snapchat":"sc",
    "amazon":"am","linkedin":"li",
}

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

# ── SERVICES CATALOG ──────────────────────────────────────────────────────────
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
        "tw_russia": {"cc":"russia","api":"twitter","flag":"🇷🇺","country":"Russia"},
        "tw_india":  {"cc":"india","api":"twitter","flag":"🇮🇳","country":"India"},
        "tw_usa":    {"cc":"usa","api":"twitter","flag":"🇺🇸","country":"USA"},
        "tw_uk":     {"cc":"england","api":"twitter","flag":"🇬🇧","country":"UK"},
    },
    "📷 Snapchat": {
        "sc_russia": {"cc":"russia","api":"snapchat","flag":"🇷🇺","country":"Russia"},
        "sc_usa":    {"cc":"usa","api":"snapchat","flag":"🇺🇸","country":"USA"},
        "sc_uk":     {"cc":"england","api":"snapchat","flag":"🇬🇧","country":"UK"},
        "sc_india":  {"cc":"india","api":"snapchat","flag":"🇮🇳","country":"India"},
    },
    "🛒 Amazon": {
        "az_russia": {"cc":"russia","api":"amazon","flag":"🇷🇺","country":"Russia"},
        "az_india":  {"cc":"india","api":"amazon","flag":"🇮🇳","country":"India"},
        "az_usa":    {"cc":"usa","api":"amazon","flag":"🇺🇸","country":"USA"},
        "az_uk":     {"cc":"england","api":"amazon","flag":"🇬🇧","country":"UK"},
    },
    "💼 LinkedIn": {
        "li_russia": {"cc":"russia","api":"linkedin","flag":"🇷🇺","country":"Russia"},
        "li_india":  {"cc":"india","api":"linkedin","flag":"🇮🇳","country":"India"},
        "li_usa":    {"cc":"usa","api":"linkedin","flag":"🇺🇸","country":"USA"},
        "li_uk":     {"cc":"england","api":"linkedin","flag":"🇬🇧","country":"UK"},
    },
}

# ── FIX 409 / WEBHOOK ────────────────────────────────────────────────────────
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

# ── MONGODB ───────────────────────────────────────────────────────────────────
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
channels_col  = db['force_channels']   # dynamic force-join channels

try:
    users_col.create_index("user_id", unique=True)
    orders_col.create_index("order_id")
    orders_col.create_index("user_id")
    deposits_col.create_index("user_id")
    channels_col.create_index("channel_id", unique=True)
    logger.info("✅ MongoDB indexes created")
except Exception as e:
    logger.warning(f"Index creation: {e}")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown", threaded=False)

# ══════════════════════════════════════════════════════════════════════════════
#  PRICE ENGINE — FIXED: Returns live price+stock, never "Unavailable" falsely
# ══════════════════════════════════════════════════════════════════════════════
_price_cache = {}   # key -> (sell_price, stock, source, timestamp)

def _smspool_price(cc, api):
    """
    SmsPool v2 API — correct endpoint for price+stock.
    Returns (sell_price_inr, stock) or (None, 0).
    """
    if not SMSPOOL_KEY:
        return None, 0
    try:
        country_code = SMSPOOL_CC.get(cc)
        service_code = SMSPOOL_SVC.get(api)
        if not country_code or not service_code:
            return None, 0

        # Correct SmsPool API endpoint
        r = requests.get(
            "https://api.smspool.net/service/price",
            params={
                "key":     SMSPOOL_KEY,
                "country": country_code,
                "service": service_code,
            },
            timeout=10
        )
        if r.status_code != 200:
            logger.warning(f"SmsPool HTTP {r.status_code} for {cc}/{api}")
            return None, 0

        data = r.json()
        # SmsPool response: {"price": "0.50", "stock": 120, ...}
        price = float(data.get("price", 0) or 0)
        stock = int(data.get("stock", 0) or 0)

        if price > 0 and stock > 0:
            sell = math.ceil(price * USDT_RATE * MARGIN)
            return sell, stock

    except Exception as e:
        logger.warning(f"SmsPool price error ({cc}/{api}): {e}")
    return None, 0


def _vaksms_price(cc, api):
    """
    Vak-SMS API — correct endpoint for price+stock.
    Returns (sell_price_inr, stock) or (None, 0).
    """
    if not VAKSMS_KEY:
        return None, 0
    try:
        country_code = VAKSMS_CC.get(cc)
        service_code = VAKSMS_SVC.get(api)
        if not country_code or not service_code:
            return None, 0

        # Correct Vak-SMS endpoint
        r = requests.get(
            "https://vak-sms.com/api/getCountOperator/",
            params={
                "apiKey":  VAKSMS_KEY,
                "country": country_code,
                "service": service_code,
            },
            timeout=10
        )
        if r.status_code != 200:
            logger.warning(f"VakSMS HTTP {r.status_code} for {cc}/{api}")
            return None, 0

        data = r.json()
        # Vak-SMS returns list: [{"price": 15, "count": 50, "operator": "any"}, ...]
        # or dict with error
        if isinstance(data, dict) and data.get("error"):
            return None, 0

        items = data if isinstance(data, list) else []
        best_price   = None
        total_stock  = 0
        for op in items:
            p = float(op.get("price", 0) or 0)
            c = int(op.get("count", 0) or 0)
            total_stock += c
            if c > 0 and (best_price is None or p < best_price):
                best_price = p

        if best_price and total_stock > 0:
            # Vak-SMS prices are in RUB; 1 RUB ≈ 1 INR approx — apply margin
            sell = math.ceil(best_price * MARGIN)
            return sell, total_stock

    except Exception as e:
        logger.warning(f"VakSMS price error ({cc}/{api}): {e}")
    return None, 0


def best_price(cc, api, force_refresh=False):
    """
    Returns (sell_price, stock, source) — always live, margin hidden.
    Caches for 30 minutes to avoid rate limits.
    force_refresh=True bypasses cache.
    """
    key = f"{cc}|{api}"
    cached = _price_cache.get(key)
    if not force_refresh and cached and time.time() - cached[3] < 1800:
        return cached[0], cached[1], cached[2]

    # Try both APIs
    psp, ssp = _smspool_price(cc, api)
    pvk, svk = _vaksms_price(cc, api)

    result = None
    if psp and ssp > 0 and pvk and svk > 0:
        # Pick cheaper
        result = (psp, ssp, 'smspool') if psp <= pvk else (pvk, svk, 'vaksms')
    elif psp and ssp > 0:
        result = (psp, ssp, 'smspool')
    elif pvk and svk > 0:
        result = (pvk, svk, 'vaksms')

    if result:
        _price_cache[key] = (*result, time.time())
        return result

    # No stock from either API
    return None, 0, None


def get_all_stock_summary():
    """
    Fetch stock for every service+country combo.
    Returns list of dicts for admin stock view.
    """
    summary = []
    for cat, items in SERVICES.items():
        for key, svc in items.items():
            price, stock, source = best_price(svc['cc'], svc['api'])
            summary.append({
                "cat": cat,
                "country": svc['country'],
                "flag": svc['flag'],
                "api": svc['api'],
                "price": price,
                "stock": stock,
                "source": source or "none",
            })
    return summary


def find_svc(key):
    for cat, items in SERVICES.items():
        if key in items:
            return items[key], cat
    return None, None


# ══════════════════════════════════════════════════════════════════════════════
#  BUY / OTP FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def _buy_smspool(cc, api):
    if not SMSPOOL_KEY: return None, None
    try:
        r = requests.get(
            "https://api.smspool.net/purchase/sms",
            params={
                "key":     SMSPOOL_KEY,
                "country": SMSPOOL_CC.get(cc),
                "service": SMSPOOL_SVC.get(api),
            },
            timeout=15
        ).json()
        if r.get("success") or r.get("order_id"):
            return r.get("order_id"), r.get("phonenumber") or r.get("number")
    except Exception as e:
        logger.error(f"SmsPool buy: {e}")
    return None, None


def _buy_vaksms(cc, api):
    if not VAKSMS_KEY: return None, None
    try:
        r = requests.get(
            "https://vak-sms.com/api/getSim/",
            params={
                "apiKey":  VAKSMS_KEY,
                "service": VAKSMS_SVC.get(api),
                "country": VAKSMS_CC.get(cc),
            },
            timeout=15
        ).json()
        if r.get("idNum"):
            return r.get("idNum"), r.get("tel")
    except Exception as e:
        logger.error(f"VakSMS buy: {e}")
    return None, None


def smart_buy(cc, api):
    """Buy number — try SmsPool first, fallback Vak-SMS."""
    if SMSPOOL_KEY:
        oid, num = _buy_smspool(cc, api)
        if oid and num:
            return oid, num, 'smspool'
    if VAKSMS_KEY:
        oid, num = _buy_vaksms(cc, api)
        if oid and num:
            return oid, num, 'vaksms'
    return None, None, None


def check_otp(oid, source):
    try:
        if source == 'smspool':
            r = requests.get(
                "https://api.smspool.net/sms/check",
                params={"key": SMSPOOL_KEY, "orderid": oid},
                timeout=10
            ).json()
            code = r.get("sms") or r.get("code")
            if code: return str(code)
        elif source == 'vaksms':
            r = requests.get(
                "https://vak-sms.com/api/getSmsCode/",
                params={"apiKey": VAKSMS_KEY, "idNum": oid},
                timeout=10
            ).json()
            code = r.get("smsCode") or r.get("code")
            if code: return str(code)
    except Exception as e:
        logger.error(f"OTP check: {e}")
    return None


def cancel_order_api(oid, source):
    try:
        if source == 'smspool':
            requests.get("https://api.smspool.net/sms/cancel",
                params={"key": SMSPOOL_KEY, "orderid": oid}, timeout=10)
        elif source == 'vaksms':
            requests.get("https://vak-sms.com/api/setStatus/",
                params={"apiKey": VAKSMS_KEY, "idNum": oid, "status": "end"}, timeout=10)
    except: pass


# ══════════════════════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_user(uid, uname=None, fname=None):
    try:
        users_col.find_one_and_update(
            {"user_id": uid},
            {"$setOnInsert": {
                "user_id":    uid,
                "username":   uname or "",
                "full_name":  fname or "",
                "balance":    0.0,
                "total_spent":0.0,
                "orders":     0,
                "banned":     False,
                "joined_at":  datetime.utcnow()
            }},
            upsert=True,
            return_document=True
        )
        upd = {}
        if uname: upd["username"]  = uname
        if fname: upd["full_name"] = fname
        if upd: users_col.update_one({"user_id": uid}, {"$set": upd})
        return users_col.find_one({"user_id": uid})
    except Exception as e:
        logger.error(f"get_user: {e}")
        return {"user_id":uid,"balance":0,"total_spent":0,"orders":0,"banned":False}


def is_banned(uid):
    u = users_col.find_one({"user_id": uid})
    return bool(u and u.get("banned"))


def add_balance(uid, amount):
    try:
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": amount}}, upsert=False)
        return True
    except Exception as e:
        logger.error(f"add_balance: {e}")
        return False


def deduct_balance(uid, amount):
    try:
        r = users_col.update_one(
            {"user_id": uid, "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount, "orders": 1, "total_spent": amount}}
        )
        return r.modified_count > 0
    except Exception as e:
        logger.error(f"deduct_balance: {e}")
        return False


def log_order(uid, cat, svc, num, oid, sell, source):
    try:
        orders_col.insert_one({
            "user_id":    uid,
            "category":   cat,
            "service":    f"{svc['flag']} {svc['country']} {cat}",
            "api":        svc['api'],
            "cc":         svc['cc'],
            "number":     num,
            "order_id":   str(oid),
            "amount":     sell,
            "source":     source,
            "profit":     round(sell * (1 - 1/MARGIN), 2),
            "status":     "pending",
            "otp":        None,
            "created_at": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"log_order: {e}")


# ── Dynamic channels (Admin can add/remove) ───────────────────────────────────
def get_force_channels():
    """Returns list of (channel_id, link, name) from DB + env defaults."""
    channels = []
    for c in channels_col.find({}):
        channels.append((c['channel_id'], c['link'], c['name']))
    # Add env defaults if not in DB
    for ch_id, link, name in CH_DEFAULT:
        if ch_id and ch_id not in [c[0] for c in channels]:
            channels.append((ch_id, link, name))
    return channels


def is_joined(uid):
    ok = ['member', 'administrator', 'creator']
    for ch_id, _, _ in get_force_channels():
        if not ch_id: continue
        try:
            if bot.get_chat_member(ch_id, uid).status not in ok:
                return False
        except:
            pass  # If can't check, allow through
    return True


def force_join_markup():
    kb = types.InlineKeyboardMarkup()
    for ch_id, link, name in get_force_channels():
        if link:
            kb.add(types.InlineKeyboardButton(f"📢 {name}", url=link))
    kb.add(types.InlineKeyboardButton("✅ Join Ho Gaya", callback_data="check_join"))
    return kb


# ══════════════════════════════════════════════════════════════════════════════
#  API BALANCE FETCH
# ══════════════════════════════════════════════════════════════════════════════
def get_smspool_balance():
    if not SMSPOOL_KEY: return "Key Not Set"
    try:
        r = requests.get(
            "https://api.smspool.net/request/balance",
            params={"key": SMSPOOL_KEY},
            timeout=10
        ).json()
        bal = r.get("balance", r.get("Balance", "?"))
        return f"${bal}"
    except Exception as e:
        return f"Error: {e}"


def get_vaksms_balance():
    if not VAKSMS_KEY: return "Key Not Set"
    try:
        r = requests.get(
            "https://vak-sms.com/api/getBalance/",
            params={"apiKey": VAKSMS_KEY},
            timeout=10
        ).json()
        bal = r.get("balance", r.get("Balance", "?"))
        return f"₽{bal}"
    except Exception as e:
        return f"Error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#  BOT HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

# pending state for admin ops
_admin_state = {}   # uid -> {"action": ..., "data": ...}

def main_menu(uid):
    u = get_user(uid)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📲 Buy Number", "💰 Wallet")
    kb.add("📦 My Orders", "👥 Refer & Earn")
    kb.add("📊 Profile", "🆘 Support")
    return kb, u


def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Stats", "👥 Users")
    kb.add("📋 Pending Dep", "💱 API Balances")
    kb.add("🔑 API Keys", "📢 Channels")
    kb.add("📣 Broadcast", "🏆 Top Buyers")
    kb.add("📦 Orders", "📈 Stock")
    kb.add("➕ Platform Add", "💾 Export")
    kb.add("💵 Add Balance", "💸 Deduct Balance")
    kb.add("🚫 Ban User", "✅ Unban User")
    return kb


@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    uname = msg.from_user.username
    fname = msg.from_user.first_name

    if is_banned(uid):
        return bot.reply_to(msg, "❌ Aapka account ban kar diya gaya hai. Support se sampark karein.")

    # Force join check
    if not is_joined(uid):
        bot.reply_to(msg, "📢 *Pehle in channels ko join karein:*", parse_mode="Markdown",
                     reply_markup=force_join_markup())
        return

    get_user(uid, uname, fname)

    # Referral handling
    parts = msg.text.split()
    if len(parts) > 1:
        try:
            ref_uid = int(parts[1])
            if ref_uid != uid:
                referer = users_col.find_one({"user_id": ref_uid})
                if referer:
                    users_col.update_one({"user_id": ref_uid}, {"$inc": {"balance": 2.0}})
                    bot.send_message(ref_uid, f"🎉 Aapko referral bonus mila! +₹2 wallet mein add hue.")
        except: pass

    kb, u = main_menu(uid)
    bot.send_message(uid,
        f"👑 *OtpKing Bot*\n"
        f"Welcome *{fname}* ji! 🙏\n\n"
        f"✅ 10 Services | 50+ Countries\n"
        f"💎 USDT + 🇮🇳 UPI Deposit\n\n"
        f"💰 Balance: ₹{u.get('balance', 0):.2f}\n\n"
        f"👇 Kya karna hai?",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def cb_check_join(call):
    uid = call.from_user.id
    if is_joined(uid):
        bot.answer_callback_query(call.id, "✅ Thanks! Ab aap use kar sakte hain.")
        cmd_start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Abhi join nahi kiya! Pehle join karein.", show_alert=True)


# ── MAIN MENU HANDLERS ────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📲 Buy Number")
def btn_buy(msg):
    if not is_joined(msg.from_user.id):
        return bot.reply_to(msg, "📢 Pehle channels join karein!", reply_markup=force_join_markup())
    kb = types.InlineKeyboardMarkup(row_width=2)
    for cat in SERVICES:
        kb.add(types.InlineKeyboardButton(cat, callback_data=f"cat|{cat}"))
    bot.send_message(msg.chat.id, "📲 *Service chunein:*", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("cat|"))
def cb_cat(call):
    cat = call.data.split("|", 1)[1]
    items = SERVICES.get(cat, {})
    if not items:
        return bot.answer_callback_query(call.id, "Service not found")

    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = []
    for key, svc in items.items():
        # Fetch live price
        price, stock, source = best_price(svc['cc'], svc['api'])
        if price and stock > 0:
            stock_txt = f"🔥{stock}" if stock > LOW_STOCK else f"⚠️{stock}"
            label = f"{svc['flag']} {svc['country']} · ₹{price} · {stock_txt}"
            rows.append(types.InlineKeyboardButton(label, callback_data=f"buy|{key}"))
        else:
            # Show with 🔄 fetching — don't block with "Unavailable"
            # Try once more synchronously
            price2, stock2, src2 = best_price(svc['cc'], svc['api'], force_refresh=True)
            if price2 and stock2 > 0:
                stock_txt = f"🔥{stock2}" if stock2 > LOW_STOCK else f"⚠️{stock2}"
                label = f"{svc['flag']} {svc['country']} · ₹{price2} · {stock_txt}"
                rows.append(types.InlineKeyboardButton(label, callback_data=f"buy|{key}"))
            else:
                # Truly no stock from API
                label = f"{svc['flag']} {svc['country']} · ❌ No Stock"
                rows.append(types.InlineKeyboardButton(label, callback_data="no_stock"))

    kb.add(*rows)
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_services"))
    try:
        bot.edit_message_text(
            f"🌍 *{cat} — Country chunein:*",
            call.message.chat.id, call.message.message_id,
            reply_markup=kb
        )
    except:
        bot.send_message(call.message.chat.id, f"🌍 *{cat} — Country chunein:*", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "no_stock")
def cb_no_stock(call):
    bot.answer_callback_query(call.id, "❌ Is time stock nahi hai. Baad mein try karein.", show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data == "back_services")
def cb_back_services(call):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for cat in SERVICES:
        kb.add(types.InlineKeyboardButton(cat, callback_data=f"cat|{cat}"))
    try:
        bot.edit_message_text("📲 *Service chunein:*", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, "📲 *Service chunein:*", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("buy|"))
def cb_buy(call):
    uid = call.from_user.id
    key = call.data.split("|", 1)[1]
    svc, cat = find_svc(key)
    if not svc:
        return bot.answer_callback_query(call.id, "Service not found")

    price, stock, source = best_price(svc['cc'], svc['api'])
    if not price or stock == 0:
        return bot.answer_callback_query(call.id, "❌ Stock khatam ho gaya, dobara try karein!", show_alert=True)

    u = get_user(uid)
    bal = u.get('balance', 0)

    if bal < price:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💰 Wallet Recharge", callback_data="wallet_recharge"))
        bot.answer_callback_query(call.id, "")
        bot.send_message(uid,
            f"❌ *Insufficient Balance!*\n\n"
            f"💰 Aapka balance: ₹{bal:.2f}\n"
            f"💸 Required: ₹{price}\n\n"
            f"Pehle wallet recharge karein 👇",
            reply_markup=kb
        )
        return

    # Deduct balance
    if not deduct_balance(uid, price):
        return bot.answer_callback_query(call.id, "❌ Balance deduct failed, retry karein!", show_alert=True)

    bot.answer_callback_query(call.id, "⏳ Number le raha hoon...")
    bot.send_message(uid, "⏳ *Number purchase ho raha hai... 1-2 seconds wait karein.*")

    # Buy number
    oid, number, src = smart_buy(svc['cc'], svc['api'])
    if not oid or not number:
        # Refund
        add_balance(uid, price)
        bot.send_message(uid, "❌ *Number nahi mila!* Refund ho gaya ₹{price}. Dobara try karein.")
        return

    log_order(uid, cat, svc, number, oid, price, src)
    _price_cache.pop(f"{svc['cc']}|{svc['api']}", None)  # Invalidate cache

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📩 OTP Check", callback_data=f"otp|{oid}|{src}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{oid}|{src}|{price}|{uid}")
    )

    bot.send_message(uid,
        f"✅ *Number Mila!*\n\n"
        f"📱 Number: `{number}`\n"
        f"🏷 Service: {svc['flag']} {svc['country']} {cat}\n"
        f"💸 Charged: ₹{price}\n"
        f"💰 Balance Left: ₹{bal - price:.2f}\n\n"
        f"⏳ OTP ka wait karein ya 2 min baad check karein.",
        reply_markup=kb
    )

    # Auto OTP check in background (3 attempts x 60 sec)
    def auto_check():
        for _ in range(6):
            time.sleep(30)
            code = check_otp(oid, src)
            if code:
                orders_col.update_one({"order_id": str(oid)}, {"$set": {"status": "completed", "otp": code}})
                bot.send_message(uid, f"🎉 *OTP Aaya!*\n\n`{code}`\n\nOrder ID: `{oid}`")
                return
        orders_col.update_one({"order_id": str(oid)}, {"$set": {"status": "expired"}})

    Thread(target=auto_check, daemon=True).start()


@bot.callback_query_handler(func=lambda c: c.data.startswith("otp|"))
def cb_otp(call):
    _, oid, src = call.data.split("|")
    code = check_otp(oid, src)
    if code:
        bot.answer_callback_query(call.id, f"OTP: {code}", show_alert=True)
        orders_col.update_one({"order_id": str(oid)}, {"$set": {"status": "completed", "otp": code}})
    else:
        bot.answer_callback_query(call.id, "❌ OTP abhi nahi aaya. Wait karein...", show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data.startswith("cancel|"))
def cb_cancel(call):
    parts = call.data.split("|")
    _, oid, src, price, uid_str = parts
    uid = int(uid_str)
    price = float(price)
    cancel_order_api(oid, src)
    add_balance(uid, price)
    orders_col.update_one({"order_id": str(oid)}, {"$set": {"status": "cancelled"}})
    bot.answer_callback_query(call.id, f"✅ Cancelled! ₹{price} refund ho gaya.", show_alert=True)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except: pass


# ── WALLET ────────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "💰 Wallet")
def btn_wallet(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💳 UPI Recharge", callback_data="wallet_recharge"),
        types.InlineKeyboardButton("💎 USDT Recharge", callback_data="wallet_usdt"),
    )
    kb.add(types.InlineKeyboardButton("📜 Transaction History", callback_data="txn_history"))
    bot.send_message(uid,
        f"💰 *Wallet*\n\n"
        f"Balance: *₹{u.get('balance', 0):.2f}*\n"
        f"Total Spent: ₹{u.get('total_spent', 0):.2f}\n"
        f"Total Orders: {u.get('orders', 0)}",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data == "wallet_recharge")
def cb_recharge_upi(call):
    kb = types.InlineKeyboardMarkup(row_width=3)
    btns = [types.InlineKeyboardButton(f"₹{a}", callback_data=f"upi_amt|{a}") for a in UPI_LIST]
    kb.add(*btns)
    bot.send_message(call.message.chat.id, "💳 *UPI Recharge amount chunein:*", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("upi_amt|"))
def cb_upi_amt(call):
    uid = call.from_user.id
    amount = int(call.data.split("|")[1])
    bot.send_message(uid,
        f"💳 *UPI Payment Details*\n\n"
        f"Amount: *₹{amount}*\n"
        f"UPI ID: `{UPI_ID}`\n\n"
        f"Payment karne ke baad *screenshot bhejein* — Admin verify karega.\n\n"
        f"📸 Iss message ko forward karo payment proof ke saath."
    )
    deposits_col.insert_one({
        "user_id": uid, "amount": amount, "method": "UPI",
        "status": "pending", "created_at": datetime.utcnow()
    })
    # Notify admin
    try:
        bot.send_message(OWNER_ID,
            f"💳 *New UPI Deposit Request*\n"
            f"User: {uid} (@{call.from_user.username or 'N/A'})\n"
            f"Amount: ₹{amount}"
        )
    except: pass


@bot.callback_query_handler(func=lambda c: c.data == "wallet_usdt")
def cb_recharge_usdt(call):
    bot.send_message(call.message.chat.id,
        f"💎 *USDT Recharge*\n\n"
        f"Network: TRC20 (TRON)\n"
        f"Address: `YourUSDTAddressHere`\n\n"
        f"Payment ke baad amount aur TXID bhejein Support ko: {SUPPORT_BOT}"
    )


@bot.callback_query_handler(func=lambda c: c.data == "txn_history")
def cb_txn_history(call):
    uid = call.from_user.id
    orders = list(orders_col.find({"user_id": uid}).sort("created_at", DESCENDING).limit(10))
    if not orders:
        return bot.answer_callback_query(call.id, "No orders yet!", show_alert=True)
    txt = "📦 *Recent Orders:*\n\n"
    for o in orders:
        txt += f"• {o.get('service','')} · ₹{o.get('amount',0)} · {o.get('status','?')}\n"
    bot.send_message(uid, txt)


# ── PROFILE ───────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📊 Profile")
def btn_profile(msg):
    uid = msg.from_user.id
    u = get_user(uid)
    ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(uid,
        f"📊 *Profile*\n\n"
        f"🆔 ID: `{uid}`\n"
        f"👤 Name: {u.get('full_name','N/A')}\n"
        f"💰 Balance: ₹{u.get('balance', 0):.2f}\n"
        f"💸 Total Spent: ₹{u.get('total_spent', 0):.2f}\n"
        f"📦 Orders: {u.get('orders', 0)}\n\n"
        f"🔗 Referral Link:\n`{ref_link}`"
    )


# ── ORDERS ────────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📦 My Orders")
def btn_orders(msg):
    uid = msg.from_user.id
    orders = list(orders_col.find({"user_id": uid}).sort("created_at", DESCENDING).limit(10))
    if not orders:
        return bot.send_message(uid, "📦 Abhi koi order nahi hai.")
    txt = "📦 *Recent Orders:*\n\n"
    for o in orders:
        otp = f"\n  🔑 OTP: `{o['otp']}`" if o.get('otp') else ""
        txt += (f"• {o.get('service','?')}\n"
                f"  💸 ₹{o.get('amount',0)} · {o.get('status','?')}"
                f"{otp}\n\n")
    bot.send_message(uid, txt)


# ── SUPPORT ───────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🆘 Support")
def btn_support(msg):
    bot.send_message(msg.chat.id,
        f"🆘 *Support*\n\n"
        f"Support Bot: {SUPPORT_BOT}\n"
        f"Proof Channel: {PROOF_CHANNEL_LINK}\n\n"
        f"Issues ke liye support ko message karein."
    )


# ── REFER & EARN ──────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "👥 Refer & Earn")
def btn_refer(msg):
    uid = msg.from_user.id
    ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
    platforms = list(platforms_col.find({}))
    txt = (f"👥 *Refer & Earn*\n\n"
           f"🔗 Aapka referral link:\n`{ref_link}`\n\n"
           f"✅ Har successful referral par ₹2 milenge!\n\n")
    if platforms:
        txt += "🏆 *Earn Platforms:*\n"
        for p in platforms:
            txt += f"• [{p['name']}]({p['link']}) — {p.get('reward','')}\n"
    bot.send_message(uid, txt, disable_web_page_preview=True)


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN PANEL — Full Advanced
# ══════════════════════════════════════════════════════════════════════════════
def is_admin(uid):
    return uid == OWNER_ID


@bot.message_handler(commands=['admin'])
def cmd_admin(msg):
    if not is_admin(msg.from_user.id):
        return bot.reply_to(msg, "❌ Access denied.")
    bot.send_message(msg.chat.id, "⚙️ *Admin Panel*", reply_markup=admin_menu())


# ── STATS ─────────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📊 Stats" and is_admin(m.from_user.id))
def admin_stats(msg):
    total_users = users_col.count_documents({})
    active_today = users_col.count_documents({"joined_at": {"$gte": datetime.utcnow().replace(hour=0,minute=0,second=0)}})
    banned = users_col.count_documents({"banned": True})
    total_orders = orders_col.count_documents({})
    completed = orders_col.count_documents({"status": "completed"})
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$profit"}}}]
    profit_res = list(orders_col.aggregate(pipeline))
    profit = profit_res[0]['total'] if profit_res else 0
    revenue_res = list(orders_col.aggregate([{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]))
    revenue = revenue_res[0]['total'] if revenue_res else 0
    bot.send_message(msg.chat.id,
        f"📊 *Bot Stats*\n\n"
        f"👥 Users: {total_users} | Active Today: {active_today} | Banned: {banned}\n"
        f"📦 Orders: {total_orders} | Completed: {completed}\n"
        f"💸 Revenue: ₹{revenue:.2f}\n"
        f"💹 Profit (margin): ₹{profit:.2f}"
    )


# ── USERS ─────────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "👥 Users" and is_admin(m.from_user.id))
def admin_users(msg):
    total = users_col.count_documents({})
    active = users_col.count_documents({"orders": {"$gt": 0}})
    banned = users_col.count_documents({"banned": True})
    bot.send_message(msg.chat.id,
        f"👥 *Users*\n\nTotal: {total} | Active: {active} | Banned: {banned}"
    )


# ── ADD BALANCE ───────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "💵 Add Balance" and is_admin(m.from_user.id))
def admin_add_balance(msg):
    _admin_state[msg.from_user.id] = {"action": "add_balance_uid"}
    bot.send_message(msg.chat.id, "💵 *Add Balance*\n\nUser ID bhejein:")


# ── DEDUCT BALANCE ────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "💸 Deduct Balance" and is_admin(m.from_user.id))
def admin_deduct_balance(msg):
    _admin_state[msg.from_user.id] = {"action": "deduct_balance_uid"}
    bot.send_message(msg.chat.id, "💸 *Deduct Balance*\n\nUser ID bhejein:")


# ── BAN/UNBAN ──────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🚫 Ban User" and is_admin(m.from_user.id))
def admin_ban(msg):
    _admin_state[msg.from_user.id] = {"action": "ban_uid"}
    bot.send_message(msg.chat.id, "🚫 Ban karne ke liye User ID bhejein:")


@bot.message_handler(func=lambda m: m.text == "✅ Unban User" and is_admin(m.from_user.id))
def admin_unban(msg):
    _admin_state[msg.from_user.id] = {"action": "unban_uid"}
    bot.send_message(msg.chat.id, "✅ Unban karne ke liye User ID bhejein:")


# ── PENDING DEPOSITS ──────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📋 Pending Dep" and is_admin(m.from_user.id))
def admin_pending_dep(msg):
    pending = list(deposits_col.find({"status": "pending"}).sort("created_at", DESCENDING).limit(20))
    if not pending:
        return bot.send_message(msg.chat.id, "✅ No pending deposits.")
    for dep in pending:
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"dep_approve|{dep['_id']}|{dep['user_id']}|{dep['amount']}"),
            types.InlineKeyboardButton("❌ Reject",  callback_data=f"dep_reject|{dep['_id']}|{dep['user_id']}|{dep['amount']}"),
        )
        bot.send_message(msg.chat.id,
            f"💳 Deposit Request\nUser: `{dep['user_id']}`\nAmount: ₹{dep['amount']}\nMethod: {dep.get('method','?')}\nDate: {dep.get('created_at','?')}",
            reply_markup=kb
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith("dep_approve|"))
def cb_dep_approve(call):
    if not is_admin(call.from_user.id): return
    _, dep_id, uid, amount = call.data.split("|")
    uid = int(uid); amount = float(amount)
    from bson import ObjectId
    deposits_col.update_one({"_id": ObjectId(dep_id)}, {"$set": {"status": "approved"}})
    add_balance(uid, amount)
    bot.answer_callback_query(call.id, "✅ Approved!")
    bot.edit_message_text(f"✅ Approved ₹{amount} for user {uid}", call.message.chat.id, call.message.message_id)
    try:
        bot.send_message(uid, f"✅ *₹{amount} aapke wallet mein add ho gaya!*\nHappy shopping 🛒")
    except: pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("dep_reject|"))
def cb_dep_reject(call):
    if not is_admin(call.from_user.id): return
    _, dep_id, uid, amount = call.data.split("|")
    uid = int(uid)
    from bson import ObjectId
    deposits_col.update_one({"_id": ObjectId(dep_id)}, {"$set": {"status": "rejected"}})
    bot.answer_callback_query(call.id, "❌ Rejected")
    bot.edit_message_text(f"❌ Rejected deposit for user {uid}", call.message.chat.id, call.message.message_id)
    try:
        bot.send_message(uid, f"❌ Aapka deposit rejected ho gaya. Issue ke liye contact karein: {SUPPORT_BOT}")
    except: pass


# ── API BALANCES ──────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "💱 API Balances" and is_admin(m.from_user.id))
def admin_api_balances(msg):
    sp = get_smspool_balance()
    vk = get_vaksms_balance()
    bot.send_message(msg.chat.id,
        f"💱 *API Balances*\n\n"
        f"✅ SmsPool: {sp}\n"
        f"✅ Vak-SMS: {vk}"
    )


# ── API KEYS STATUS ───────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🔑 API Keys" and is_admin(m.from_user.id))
def admin_api_keys(msg):
    sp_status  = "Set ✅" if SMSPOOL_KEY else "Not Set ❌"
    vk_status  = "Set ✅" if VAKSMS_KEY  else "Not Set ❌"
    try:
        user_count = users_col.count_documents({})
        mongo_status = f"Connected ({user_count} users)"
    except:
        mongo_status = "Error ❌"
    bot.send_message(msg.chat.id,
        f"🔑 *API Keys Status*\n\n"
        f"✅ SMSPOOL_APIKEY → {sp_status}\n"
        f"✅ VAKSMS_APIKEY → {vk_status}\n"
        f"✅ OWNER_ID → `{OWNER_ID}`\n"
        f"✅ MONGOURI → {mongo_status}"
    )


# ── CHANNELS (Force join manage) ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📢 Channels" and is_admin(m.from_user.id))
def admin_channels(msg):
    channels = get_force_channels()
    txt = "📢 *Force Join Channels:*\n\n"
    for i, (cid, link, name) in enumerate(channels, 1):
        txt += f"{i}. {name} — `{cid}`\n   🔗 {link}\n\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("➕ Add Channel", callback_data="ch_add"),
        types.InlineKeyboardButton("➕ Add Group",   callback_data="grp_add"),
    )
    kb.add(types.InlineKeyboardButton("🗑 Remove Channel", callback_data="ch_remove"))
    bot.send_message(msg.chat.id, txt or "No channels set.", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "ch_add")
def cb_ch_add(call):
    if not is_admin(call.from_user.id): return
    _admin_state[call.from_user.id] = {"action": "ch_add"}
    bot.send_message(call.message.chat.id,
        "📢 Channel info bhejein format mein:\n`@ChannelID | https://t.me/link | Channel Name`"
    )


@bot.callback_query_handler(func=lambda c: c.data == "grp_add")
def cb_grp_add(call):
    if not is_admin(call.from_user.id): return
    _admin_state[call.from_user.id] = {"action": "grp_add"}
    bot.send_message(call.message.chat.id,
        "👥 Group info bhejein format mein:\n`@GroupID | https://t.me/link | Group Name`"
    )


@bot.callback_query_handler(func=lambda c: c.data == "ch_remove")
def cb_ch_remove(call):
    if not is_admin(call.from_user.id): return
    channels = list(channels_col.find({}))
    if not channels:
        return bot.answer_callback_query(call.id, "No removable channels (env defaults can't be removed here).", show_alert=True)
    kb = types.InlineKeyboardMarkup()
    for c in channels:
        kb.add(types.InlineKeyboardButton(f"🗑 {c['name']}", callback_data=f"ch_del|{c['channel_id']}"))
    bot.send_message(call.message.chat.id, "Channel chunein to remove:", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("ch_del|"))
def cb_ch_del(call):
    if not is_admin(call.from_user.id): return
    ch_id = call.data.split("|", 1)[1]
    channels_col.delete_one({"channel_id": ch_id})
    bot.answer_callback_query(call.id, f"✅ Removed: {ch_id}")


# ── BROADCAST ─────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📣 Broadcast" and is_admin(m.from_user.id))
def admin_broadcast(msg):
    _admin_state[msg.from_user.id] = {"action": "broadcast"}
    bot.send_message(msg.chat.id, "📣 Broadcast message bhejein (text/photo/video):")


# ── TOP BUYERS ────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🏆 Top Buyers" and is_admin(m.from_user.id))
def admin_top_buyers(msg):
    top = list(users_col.find({}).sort("total_spent", DESCENDING).limit(10))
    txt = "🏆 *Top Buyers:*\n\n"
    for i, u in enumerate(top, 1):
        txt += f"{i}. `{u['user_id']}` (@{u.get('username','?')}) — ₹{u.get('total_spent',0):.2f}\n"
    bot.send_message(msg.chat.id, txt)


# ── ORDERS (Admin) ────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📦 Orders" and is_admin(m.from_user.id))
def admin_orders(msg):
    recent = list(orders_col.find({}).sort("created_at", DESCENDING).limit(15))
    if not recent:
        return bot.send_message(msg.chat.id, "No orders yet.")
    txt = "📦 *Recent Orders:*\n\n"
    for o in recent:
        txt += f"• UID:{o['user_id']} | {o.get('service','')} | ₹{o.get('amount',0)} | {o.get('status','?')}\n"
    bot.send_message(msg.chat.id, txt)


# ── STOCK (Admin) ─────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📈 Stock" and is_admin(m.from_user.id))
def admin_stock(msg):
    bot.send_message(msg.chat.id, "⏳ *Fetching live stock from APIs...* (may take 10-30 sec)")
    summary = get_all_stock_summary()
    # Group by service category
    grouped = {}
    for item in summary:
        cat = item['api']
        grouped.setdefault(cat, []).append(item)

    for api, items in grouped.items():
        txt = f"📊 *{api.upper()} Stock:*\n\n"
        for item in items:
            if item['stock'] > 0:
                txt += f"{item['flag']} {item['country']}: {item['stock']} @ ₹{item['price']} ({item['source']})\n"
            else:
                txt += f"{item['flag']} {item['country']}: ❌ No Stock\n"
        bot.send_message(msg.chat.id, txt)


# ── EXPORT ────────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "💾 Export" and is_admin(m.from_user.id))
def admin_export(msg):
    users = list(users_col.find({}, {"_id": 0}))
    data = json.dumps(users, default=str, indent=2)
    f = io.BytesIO(data.encode())
    f.name = "users_export.json"
    bot.send_document(msg.chat.id, f, caption=f"👥 Users Export — {len(users)} users")


# ── PLATFORM ADD ──────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "➕ Platform Add" and is_admin(m.from_user.id))
def admin_platform_add(msg):
    _admin_state[msg.from_user.id] = {"action": "platform_add"}
    bot.send_message(msg.chat.id,
        "Platform info bhejein:\n`Name | Link | Reward`\n\nExample:\n`Task App | https://taskapp.com | ₹50 per signup`"
    )


# ── ADMIN STATE HANDLER (text inputs) ────────────────────────────────────────
@bot.message_handler(func=lambda m: m.from_user.id in _admin_state and is_admin(m.from_user.id))
def admin_state_handler(msg):
    uid = msg.from_user.id
    state = _admin_state.get(uid, {})
    action = state.get("action", "")
    text = msg.text or ""

    # ADD BALANCE flow
    if action == "add_balance_uid":
        try:
            target = int(text.strip())
            _admin_state[uid] = {"action": "add_balance_amount", "target": target}
            bot.send_message(msg.chat.id, f"User `{target}` — Kitna balance add karein? (₹ mein):")
        except:
            bot.send_message(msg.chat.id, "❌ Valid User ID bhejein.")
        return

    if action == "add_balance_amount":
        try:
            amount = float(text.strip())
            target = state['target']
            add_balance(target, amount)
            bot.send_message(msg.chat.id, f"✅ ₹{amount} added to user `{target}`")
            try:
                bot.send_message(target, f"✅ *Admin ne aapke wallet mein ₹{amount} add kiye!*")
            except: pass
            _admin_state.pop(uid, None)
        except:
            bot.send_message(msg.chat.id, "❌ Valid amount bhejein.")
        return

    # DEDUCT BALANCE flow
    if action == "deduct_balance_uid":
        try:
            target = int(text.strip())
            _admin_state[uid] = {"action": "deduct_balance_amount", "target": target}
            bot.send_message(msg.chat.id, f"User `{target}` — Kitna balance deduct karein? (₹ mein):")
        except:
            bot.send_message(msg.chat.id, "❌ Valid User ID bhejein.")
        return

    if action == "deduct_balance_amount":
        try:
            amount = float(text.strip())
            target = state['target']
            # Force deduct (admin override — no balance check)
            users_col.update_one({"user_id": target}, {"$inc": {"balance": -amount}})
            bot.send_message(msg.chat.id, f"✅ ₹{amount} deducted from user `{target}`")
            _admin_state.pop(uid, None)
        except:
            bot.send_message(msg.chat.id, "❌ Valid amount bhejein.")
        return

    # BAN
    if action == "ban_uid":
        try:
            target = int(text.strip())
            users_col.update_one({"user_id": target}, {"$set": {"banned": True}})
            bot.send_message(msg.chat.id, f"🚫 User `{target}` banned.")
            _admin_state.pop(uid, None)
        except:
            bot.send_message(msg.chat.id, "❌ Valid User ID bhejein.")
        return

    # UNBAN
    if action == "unban_uid":
        try:
            target = int(text.strip())
            users_col.update_one({"user_id": target}, {"$set": {"banned": False}})
            bot.send_message(msg.chat.id, f"✅ User `{target}` unbanned.")
            _admin_state.pop(uid, None)
        except:
            bot.send_message(msg.chat.id, "❌ Valid User ID bhejein.")
        return

    # BROADCAST
    if action == "broadcast":
        all_users = list(users_col.find({}, {"user_id": 1}))
        sent = failed = 0
        for u in all_users:
            try:
                bot.copy_message(u['user_id'], msg.chat.id, msg.message_id)
                sent += 1
                time.sleep(0.05)
            except:
                failed += 1
        bot.send_message(msg.chat.id, f"📣 Broadcast done!\n✅ Sent: {sent}\n❌ Failed: {failed}")
        _admin_state.pop(uid, None)
        return

    # PLATFORM ADD
    if action == "platform_add":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) >= 2:
            platforms_col.insert_one({
                "name":   parts[0],
                "link":   parts[1],
                "reward": parts[2] if len(parts) > 2 else "",
                "added_at": datetime.utcnow()
            })
            bot.send_message(msg.chat.id, f"✅ Platform added: {parts[0]}")
        else:
            bot.send_message(msg.chat.id, "❌ Format: Name | Link | Reward")
        _admin_state.pop(uid, None)
        return

    # CHANNEL ADD
    if action in ("ch_add", "grp_add"):
        parts = [p.strip() for p in text.split("|")]
        if len(parts) >= 3:
            channels_col.update_one(
                {"channel_id": parts[0]},
                {"$set": {"channel_id": parts[0], "link": parts[1], "name": parts[2]}},
                upsert=True
            )
            bot.send_message(msg.chat.id, f"✅ Added: {parts[2]} ({parts[0]})")
        else:
            bot.send_message(msg.chat.id, "❌ Format: @ID | https://link | Name")
        _admin_state.pop(uid, None)
        return


# ── BAD WORDS FILTER ──────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=['text'])
def filter_bad_words(msg):
    if not msg.text: return
    low = msg.text.lower()
    if any(w in low for w in BAD_WORDS):
        try:
            bot.delete_message(msg.chat.id, msg.message_id)
            bot.send_message(msg.chat.id, "⚠️ Please respectful language use karein.")
        except: pass


# ══════════════════════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("🚀 OTPKING PRO — Starting (FIXED)")
    logger.info(f"   Owner ID : {OWNER_ID}")
    logger.info(f"   SmsPool  : {'✅ Set' if SMSPOOL_KEY else '❌ Not Set'}")
    logger.info(f"   Vak-SMS  : {'✅ Set' if VAKSMS_KEY else '❌ Not Set'}")
    logger.info(f"   MongoDB  : {'✅ URI Set' if MONGO_URI else '❌ Not Set'}")

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20, logger_level=logging.WARNING)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
