"""
╔══════════════════════════════════════════════════════════════╗
║          OTPKING PRO v8 — DGOTP ONLY BUILD                   ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ ONLY DgOTP.in — Primary & Only API                       ║
║  ✅ Price = DgOTP Raw INR × 1.10 (10% margin) — User pays    ║
║  ✅ Balance Cut = Sell price (DgOTP cost + 10%)              ║
║  ✅ OTP Auto-Check (30×10s = 5 min) + Auto Refund            ║
║  ✅ getStatus retry with multiple response formats           ║
║  ✅ Admin: Quick Balance Add/Deduct (buttons)                 ║
║  ✅ Admin: Live Price Checker (DgOTP raw + sell price)       ║
║  ✅ Admin: Balance Log, User Search, Ban/Unban               ║
║  ✅ Force Channel Join Guard                                  ║
║  ✅ Deposit: USDT + UPI with quick-approve buttons           ║
║  ✅ Gaali Auto-Ban + Broadcast + Export                       ║
║  ✅ 409 Conflict Fix + Auto Reconnect                         ║
╚══════════════════════════════════════════════════════════════╝
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

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — .env se aata hai
# ══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN          = os.getenv('BOT_TOKEN', '')
MONGO_URI          = os.getenv('MONGO_URI') or os.getenv('MONGO_URL', '')
# ── ONLY DGOTP.IN — SmsPool & VakSMS removed ─────────────────────────────────
DGOTP_KEY          = os.getenv('DGOTP_API_KEY', '')
DGOTP_BASE         = "https://dgotp.in/stubs/handler_api.php"
DGOTP_MARGIN       = 1.10   # 10% markup on DgOTP INR price — this is what user sees/pays
# ─────────────────────────────────────────────────────────────────────────────
OWNER_ID           = int(os.getenv('OWNER_ID', '0'))
SUPPORT_BOT        = os.getenv('SUPPORT_BOT', '@YourHelpBot')
PROOF_CHANNEL_ID   = os.getenv('PROOF_CHANNEL_ID', '@ProofChannel')
PROOF_CHANNEL_LINK = os.getenv('PROOF_CHANNEL_LINK', 'https://t.me/ProofChannel')
GROUP_ID           = os.getenv('GROUP_ID', '@YourGroup')
GROUP_LINK         = os.getenv('GROUP_LINK', 'https://t.me/YourGroup')
BINANCE_ADDRESS    = os.getenv('BINANCE_ADDRESS', '')
UPI_ID             = os.getenv('UPI_ID', '')

# Default constants (DB se override hote hain)
USDT_RATE_DEFAULT = 85.0
MARGIN_DEFAULT    = 1.40   # 40%
LOW_STOCK         = 5

# ══════════════════════════════════════════════════════════════════════════════
#  DEFAULT PRICES (USD) — SmsPool scale mein
#  Jab live API nahi to same formula: USD × rate × margin = INR
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_PRICES_USD = {
    "whatsapp": {
        "russia":0.18,"india":0.15,"usa":0.50,"england":0.65,"ukraine":0.15,
        "brazil":0.12,"indonesia":0.10,"kenya":0.10,"nigeria":0.10,"pakistan":0.10,
        "cambodia":0.10,"myanmar":0.10,"vietnam":0.10,"philippines":0.12,
        "bangladesh":0.10,"kazakhstan":0.12,
    },
    "telegram": {
        "russia":0.15,"india":0.12,"usa":0.45,"england":0.60,"ukraine":0.12,
        "cambodia":0.10,"myanmar":0.10,"indonesia":0.10,"kazakhstan":0.10,
        "vietnam":0.10,"bangladesh":0.10,"philippines":0.12,
    },
    "instagram": {
        "russia":0.20,"india":0.18,"usa":0.60,"ukraine":0.18,"brazil":0.15,
        "indonesia":0.12,"england":0.70,"nigeria":0.12,
    },
    "google": {
        "russia":0.25,"india":0.22,"usa":0.70,"ukraine":0.22,"england":0.75,
        "indonesia":0.15,
    },
    "facebook": {
        "russia":0.18,"india":0.15,"usa":0.55,"ukraine":0.15,
        "indonesia":0.12,"brazil":0.12,
    },
    "tiktok":   {"russia":0.18,"usa":0.50,"india":0.15,"indonesia":0.12,"brazil":0.12},
    "twitter":  {"russia":0.18,"india":0.15,"usa":0.50,"england":0.60},
    "snapchat": {"russia":0.22,"usa":0.55,"england":0.65,"india":0.18},
    "amazon":   {"russia":0.25,"india":0.22,"usa":0.70,"england":0.75},
    "linkedin": {"russia":0.28,"india":0.25,"usa":0.75,"england":0.80},
}
DEFAULT_STOCK = 50

# ══════════════════════════════════════════════════════════════════════════════
#  API COUNTRY / SERVICE CODES
# ══════════════════════════════════════════════════════════════════════════════
# ── DgOTP.in — sms-activate compatible API ───────────────────────────────────
# Country codes: numeric (sms-activate standard)
DGOTP_CC = {
    "russia":"0","india":"22","usa":"187","england":"16","ukraine":"1",
    "brazil":"7","indonesia":"6","kenya":"118","nigeria":"109","pakistan":"162",
    "cambodia":"36","myanmar":"26","vietnam":"15","philippines":"4",
    "bangladesh":"10","kazakhstan":"57","south_africa":"28","canada":"36",
}
DGOTP_SVC = {
    "whatsapp":"wa","telegram":"tg","instagram":"ig","google":"go",
    "facebook":"fb","tiktok":"tt","twitter":"tw","snapchat":"sc",
    "amazon":"az","linkedin":"li",
}

# ══════════════════════════════════════════════════════════════════════════════
#  SERVICES CATALOG
# ══════════════════════════════════════════════════════════════════════════════
SERVICES = {
    "📱 WhatsApp": {
        "wa_russia":      {"cc":"russia",     "api":"whatsapp","flag":"🇷🇺","country":"Russia"},
        "wa_india":       {"cc":"india",      "api":"whatsapp","flag":"🇮🇳","country":"India"},
        "wa_usa":         {"cc":"usa",        "api":"whatsapp","flag":"🇺🇸","country":"USA"},
        "wa_uk":          {"cc":"england",    "api":"whatsapp","flag":"🇬🇧","country":"UK"},
        "wa_ukraine":     {"cc":"ukraine",    "api":"whatsapp","flag":"🇺🇦","country":"Ukraine"},
        "wa_brazil":      {"cc":"brazil",     "api":"whatsapp","flag":"🇧🇷","country":"Brazil"},
        "wa_indonesia":   {"cc":"indonesia",  "api":"whatsapp","flag":"🇮🇩","country":"Indonesia"},
        "wa_kenya":       {"cc":"kenya",      "api":"whatsapp","flag":"🇰🇪","country":"Kenya"},
        "wa_nigeria":     {"cc":"nigeria",    "api":"whatsapp","flag":"🇳🇬","country":"Nigeria"},
        "wa_pakistan":    {"cc":"pakistan",   "api":"whatsapp","flag":"🇵🇰","country":"Pakistan"},
        "wa_cambodia":    {"cc":"cambodia",   "api":"whatsapp","flag":"🇰🇭","country":"Cambodia"},
        "wa_myanmar":     {"cc":"myanmar",    "api":"whatsapp","flag":"🇲🇲","country":"Myanmar"},
        "wa_vietnam":     {"cc":"vietnam",    "api":"whatsapp","flag":"🇻🇳","country":"Vietnam"},
        "wa_philippines": {"cc":"philippines","api":"whatsapp","flag":"🇵🇭","country":"Philippines"},
        "wa_bangladesh":  {"cc":"bangladesh", "api":"whatsapp","flag":"🇧🇩","country":"Bangladesh"},
        "wa_kazakhstan":  {"cc":"kazakhstan", "api":"whatsapp","flag":"🇰🇿","country":"Kazakhstan"},
    },
    "✈️ Telegram": {
        "tg_russia":      {"cc":"russia",     "api":"telegram","flag":"🇷🇺","country":"Russia"},
        "tg_india":       {"cc":"india",      "api":"telegram","flag":"🇮🇳","country":"India"},
        "tg_usa":         {"cc":"usa",        "api":"telegram","flag":"🇺🇸","country":"USA"},
        "tg_uk":          {"cc":"england",    "api":"telegram","flag":"🇬🇧","country":"UK"},
        "tg_ukraine":     {"cc":"ukraine",    "api":"telegram","flag":"🇺🇦","country":"Ukraine"},
        "tg_cambodia":    {"cc":"cambodia",   "api":"telegram","flag":"🇰🇭","country":"Cambodia"},
        "tg_myanmar":     {"cc":"myanmar",    "api":"telegram","flag":"🇲🇲","country":"Myanmar"},
        "tg_indonesia":   {"cc":"indonesia",  "api":"telegram","flag":"🇮🇩","country":"Indonesia"},
        "tg_kazakhstan":  {"cc":"kazakhstan", "api":"telegram","flag":"🇰🇿","country":"Kazakhstan"},
        "tg_vietnam":     {"cc":"vietnam",    "api":"telegram","flag":"🇻🇳","country":"Vietnam"},
        "tg_bangladesh":  {"cc":"bangladesh", "api":"telegram","flag":"🇧🇩","country":"Bangladesh"},
        "tg_philippines": {"cc":"philippines","api":"telegram","flag":"🇵🇭","country":"Philippines"},
    },
    "📸 Instagram": {
        "ig_russia":    {"cc":"russia",   "api":"instagram","flag":"🇷🇺","country":"Russia"},
        "ig_india":     {"cc":"india",    "api":"instagram","flag":"🇮🇳","country":"India"},
        "ig_usa":       {"cc":"usa",      "api":"instagram","flag":"🇺🇸","country":"USA"},
        "ig_ukraine":   {"cc":"ukraine",  "api":"instagram","flag":"🇺🇦","country":"Ukraine"},
        "ig_brazil":    {"cc":"brazil",   "api":"instagram","flag":"🇧🇷","country":"Brazil"},
        "ig_indonesia": {"cc":"indonesia","api":"instagram","flag":"🇮🇩","country":"Indonesia"},
        "ig_uk":        {"cc":"england",  "api":"instagram","flag":"🇬🇧","country":"UK"},
        "ig_nigeria":   {"cc":"nigeria",  "api":"instagram","flag":"🇳🇬","country":"Nigeria"},
    },
    "📧 Gmail": {
        "gm_russia":    {"cc":"russia",   "api":"google","flag":"🇷🇺","country":"Russia"},
        "gm_india":     {"cc":"india",    "api":"google","flag":"🇮🇳","country":"India"},
        "gm_usa":       {"cc":"usa",      "api":"google","flag":"🇺🇸","country":"USA"},
        "gm_ukraine":   {"cc":"ukraine",  "api":"google","flag":"🇺🇦","country":"Ukraine"},
        "gm_uk":        {"cc":"england",  "api":"google","flag":"🇬🇧","country":"UK"},
        "gm_indonesia": {"cc":"indonesia","api":"google","flag":"🇮🇩","country":"Indonesia"},
    },
    "📘 Facebook": {
        "fb_russia":    {"cc":"russia",   "api":"facebook","flag":"🇷🇺","country":"Russia"},
        "fb_india":     {"cc":"india",    "api":"facebook","flag":"🇮🇳","country":"India"},
        "fb_usa":       {"cc":"usa",      "api":"facebook","flag":"🇺🇸","country":"USA"},
        "fb_ukraine":   {"cc":"ukraine",  "api":"facebook","flag":"🇺🇦","country":"Ukraine"},
        "fb_indonesia": {"cc":"indonesia","api":"facebook","flag":"🇮🇩","country":"Indonesia"},
        "fb_brazil":    {"cc":"brazil",   "api":"facebook","flag":"🇧🇷","country":"Brazil"},
    },
    "🎵 TikTok": {
        "tt_russia":    {"cc":"russia",   "api":"tiktok","flag":"🇷🇺","country":"Russia"},
        "tt_usa":       {"cc":"usa",      "api":"tiktok","flag":"🇺🇸","country":"USA"},
        "tt_india":     {"cc":"india",    "api":"tiktok","flag":"🇮🇳","country":"India"},
        "tt_indonesia": {"cc":"indonesia","api":"tiktok","flag":"🇮🇩","country":"Indonesia"},
        "tt_brazil":    {"cc":"brazil",   "api":"tiktok","flag":"🇧🇷","country":"Brazil"},
    },
    "🐦 Twitter/X": {
        "tw_russia": {"cc":"russia", "api":"twitter","flag":"🇷🇺","country":"Russia"},
        "tw_india":  {"cc":"india",  "api":"twitter","flag":"🇮🇳","country":"India"},
        "tw_usa":    {"cc":"usa",    "api":"twitter","flag":"🇺🇸","country":"USA"},
        "tw_uk":     {"cc":"england","api":"twitter","flag":"🇬🇧","country":"UK"},
    },
    "📷 Snapchat": {
        "sc_russia": {"cc":"russia", "api":"snapchat","flag":"🇷🇺","country":"Russia"},
        "sc_usa":    {"cc":"usa",    "api":"snapchat","flag":"🇺🇸","country":"USA"},
        "sc_uk":     {"cc":"england","api":"snapchat","flag":"🇬🇧","country":"UK"},
        "sc_india":  {"cc":"india",  "api":"snapchat","flag":"🇮🇳","country":"India"},
    },
    "🛒 Amazon": {
        "az_russia": {"cc":"russia", "api":"amazon","flag":"🇷🇺","country":"Russia"},
        "az_india":  {"cc":"india",  "api":"amazon","flag":"🇮🇳","country":"India"},
        "az_usa":    {"cc":"usa",    "api":"amazon","flag":"🇺🇸","country":"USA"},
        "az_uk":     {"cc":"england","api":"amazon","flag":"🇬🇧","country":"UK"},
    },
    "💼 LinkedIn": {
        "li_russia": {"cc":"russia", "api":"linkedin","flag":"🇷🇺","country":"Russia"},
        "li_india":  {"cc":"india",  "api":"linkedin","flag":"🇮🇳","country":"India"},
        "li_usa":    {"cc":"usa",    "api":"linkedin","flag":"🇺🇸","country":"USA"},
        "li_uk":     {"cc":"england","api":"linkedin","flag":"🇬🇧","country":"UK"},
    },
}
ALL_BTNS = set(SERVICES.keys())

BAD_WORDS = [
    "madarchod","mc","bc","bhenchod","gandu","chutiya","randi","harami",
    "bhosdike","loda","lauda","chut","bsdk","fuck","bitch","asshole",
    "bastard","shit","dick","cunt","whore","sala","maderchod","behenchod",
]

# ══════════════════════════════════════════════════════════════════════════════
#  409 FIX — Webhook clear on startup
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
admin_log_col = db['admin_balance_log']

try:
    users_col.create_index("user_id", unique=True)
    users_col.create_index("username")
    orders_col.create_index("order_id")
    orders_col.create_index("user_id")
    deposits_col.create_index("user_id")
    channels_col.create_index("channel_id", unique=True)
    logger.info("✅ MongoDB indexes ready")
except Exception as e:
    logger.warning(f"Index: {e}")

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

def get_margin():   return float(get_setting("margin", MARGIN_DEFAULT))
def get_usdt_rate(): return float(get_setting("usdt_rate", USDT_RATE_DEFAULT))

# ══════════════════════════════════════════════════════════════════════════════
#  PRICE ENGINE — DgOTP ONLY
#  User dikhta hai: DgOTP raw INR price × 1.10 (10% margin)
#  Balance katta hai: yahi sell price (cost + 10%)
# ══════════════════════════════════════════════════════════════════════════════
_pc = {}   # price cache {key: (price, stock, 'dgotp', timestamp)}

def _get_default_price(cc, api):
    """Fallback static prices when DgOTP unreachable."""
    base_usd  = DEFAULT_PRICES_USD.get(api, {}).get(cc)
    usdt_rate = get_usdt_rate()
    if base_usd:
        sell = math.ceil(base_usd * usdt_rate * DGOTP_MARGIN)
        return sell, DEFAULT_STOCK
    return None, 0

def _dgotp_price(cc, api):
    """
    Returns (sell_price_inr, stock) from dgotp.in.
    sell_price = raw_inr_cost × DGOTP_MARGIN (1.10)
    This is what user sees AND what gets deducted from balance.
    """
    try:
        if not DGOTP_KEY: return None, 0
        country = DGOTP_CC.get(cc)
        service = DGOTP_SVC.get(api)
        if not country or not service: return None, 0

        r = requests.get(DGOTP_BASE,
            params={"api_key": DGOTP_KEY, "action": "getPrices",
                    "service": service, "country": country},
            timeout=10).json()

        # Try multiple response formats:
        # Format 1: {service: {country: {cost: X, count: Y}}}
        # Format 2: {service: {country: {retail_price: X, count: Y}}}
        # Format 3: flat list
        svc_data = r.get(service, r)

        # country might be int or str
        price_data = svc_data.get(str(country)) or svc_data.get(int(country), {})

        if not price_data and isinstance(svc_data, dict):
            # Try iterating if nested differently
            for k, v in svc_data.items():
                if str(k) == str(country):
                    price_data = v
                    break

        raw_cost = float(
            price_data.get("cost") or
            price_data.get("retail_price") or
            price_data.get("price") or 0
        )
        count = int(price_data.get("count", 0))

        if raw_cost > 0 and count > 0:
            sell = math.ceil(raw_cost * DGOTP_MARGIN)
            return sell, count

        # Fallback: try getNumbersStatus for stock check
        r2 = requests.get(DGOTP_BASE,
            params={"api_key": DGOTP_KEY, "action": "getNumbersStatus",
                    "country": country, "operator": "any"},
            timeout=8).json()
        key2 = f"{service}_0"
        entry = r2.get(key2, {})
        cnt2  = int(entry.get("count", 0))
        pr2   = float(entry.get("cost") or entry.get("price") or 0)
        if pr2 > 0 and cnt2 > 0:
            return math.ceil(pr2 * DGOTP_MARGIN), cnt2

    except Exception as e:
        logger.warning(f"DGOTP price [{cc}/{api}]: {e}")
    return None, 0

def best_price(cc, api):
    """Returns (sell_price, stock, source, dg_stock, 0)"""
    k = f"{cc}|{api}"
    c = _pc.get(k)
    if c and time.time() - c[3] < 600:   # 10 min cache
        return c[0], c[1], 'dgotp', c[1], 0

    pdg, sdg = _dgotp_price(cc, api)
    if pdg and sdg > 0:
        _pc[k] = (pdg, sdg, 'dgotp', time.time())
        return pdg, sdg, 'dgotp', sdg, 0

    dp, ds = _get_default_price(cc, api)
    if dp:
        return dp, ds, 'default', 0, 0
    return None, 0, None, 0, 0

# ══════════════════════════════════════════════════════════════════════════════
#  BUY ENGINE — DgOTP ONLY
# ══════════════════════════════════════════════════════════════════════════════
def smart_buy(cc, api):
    """Buy from DgOTP. Returns (order_id, number, 'dgotp') or (None, None, None)."""
    oid, num = _dgotp_buy(cc, api)
    if oid and num:
        return oid, num, 'dgotp'
    return None, None, None

def _dgotp_buy(cc, api):
    """
    Buy number from dgotp.in — sms-activate compatible handler_api.php
    Response: "ACCESS_NUMBER:ID:NUMBER" on success
    """
    try:
        country = DGOTP_CC.get(cc)
        service = DGOTP_SVC.get(api)
        if not country or not service:
            logger.error(f"DGOTP buy: no mapping for cc={cc} api={api}")
            return None, None

        logger.info(f"DGOTP buy request: country={country} service={service}")
        r = requests.get(DGOTP_BASE,
            params={"api_key": DGOTP_KEY, "action": "getNumber",
                    "service": service, "country": country,
                    "operator": "any"},
            timeout=20).text.strip()

        logger.info(f"DGOTP buy response: {r}")

        if r.startswith("ACCESS_NUMBER:"):
            parts = r.split(":")
            if len(parts) >= 3:
                oid = parts[1].strip()
                num = parts[2].strip()
                # Inform DgOTP that SMS has been sent (status=1)
                try:
                    requests.get(DGOTP_BASE,
                        params={"api_key": DGOTP_KEY, "action": "setStatus",
                                "status": "1", "id": oid}, timeout=8)
                except: pass
                return oid, num

        # Log non-success responses for debugging
        if r == "NO_NUMBERS":
            logger.warning(f"DGOTP: NO_NUMBERS for {cc}/{api}")
        elif r == "NO_BALANCE":
            logger.error(f"DGOTP: NO_BALANCE — recharge karein!")
            try:
                bot.send_message(OWNER_ID,
                    f"🚨 *DGOTP Balance Khatam!*\n\nAccount recharge karein turant!\n"
                    f"Service: {api} | Country: {cc}")
            except: pass
        elif r == "BAD_KEY":
            logger.error("DGOTP: BAD_KEY — API key galat hai!")
        else:
            logger.warning(f"DGOTP buy unexpected response: {r}")

    except requests.Timeout:
        logger.error(f"DGOTP buy TIMEOUT: {cc}/{api}")
    except Exception as e:
        logger.error(f"DGOTP buy exception: {e}")
    return None, None

def check_otp(oid, source):
    """
    Check OTP from DgOTP.
    Possible responses:
    - "STATUS_WAIT_CODE"      → waiting, no OTP yet
    - "STATUS_OK:CODE"        → OTP received
    - "STATUS_CANCEL"         → cancelled
    - "STATUS_WAIT_RETRY"     → waiting for another SMS
    """
    if source != 'dgotp':
        logger.warning(f"check_otp called with source={source}, expected dgotp")
        return None
    try:
        r = requests.get(DGOTP_BASE,
            params={"api_key": DGOTP_KEY, "action": "getStatus", "id": oid},
            timeout=12).text.strip()

        logger.debug(f"DGOTP getStatus [{oid}]: {r}")

        if r.startswith("STATUS_OK:"):
            code = r.split(":", 1)[1].strip()
            if code:
                return code

        # Some providers send just digits as code
        if r.isdigit() and len(r) >= 4:
            return r

        # Some send "STATUS_OK" without colon then code on next poll
        # Some send "6:CODE" format
        if ":" in r:
            parts = r.split(":")
            last = parts[-1].strip()
            if last.isdigit() and len(last) >= 4:
                return last

    except requests.Timeout:
        logger.warning(f"DGOTP getStatus TIMEOUT order {oid}")
    except Exception as e:
        logger.error(f"DGOTP OTP check [{oid}]: {e}")
    return None

def cancel_order_api(oid, source):
    """Cancel/release number — status 8 = cancel on dgotp."""
    try:
        if source == 'dgotp':
            r = requests.get(DGOTP_BASE,
                params={"api_key": DGOTP_KEY, "action": "setStatus",
                        "status": "8", "id": oid}, timeout=10).text.strip()
            logger.info(f"DGOTP cancel [{oid}]: {r}")
    except Exception as e:
        logger.warning(f"Cancel {oid} [{source}]: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  OTP WAIT — Auto check every 10s for 5 min, then auto refund
# ══════════════════════════════════════════════════════════════════════════════
def _otp_wait(cid, uid, oid, refund, num, svc, cat, rbal, source):
    otp_received = False
    try:
        for attempt in range(30):   # 30 × 10s = 5 min
            time.sleep(10)
            try:
                otp = check_otp(str(oid), source)
            except Exception as e:
                logger.warning(f"OTP check attempt {attempt+1} error: {e}")
                otp = None

            if otp:
                otp_received = True
                orders_col.update_one({"order_id": str(oid)},
                    {"$set": {"status": "done", "otp": otp}})
                u2 = users_col.find_one({"user_id": uid}) or {}
                fresh_bal = u2.get('balance', rbal)
                try:
                    bot.send_message(cid,
                        f"🎉 *OTP Aa Gaya!*\n\n"
                        f"📞 `{num}`\n"
                        f"{svc['flag']} {svc['country']} | {cat}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔑 *OTP:* `{otp}`\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"💰 Balance: ₹{fresh_bal:.0f}\n"
                        f"✅ OTP use kar lein! 🙏")
                except Exception as e: logger.error(f"OTP send msg: {e}")
                Thread(target=_post_proof,
                    args=(uid, num, svc, cat, refund, otp, source), daemon=True).start()
                return

    except Exception as e:
        logger.error(f"OTP wait loop crashed for order {oid}: {e}")

    # ── Timeout / Error — FULL REFUND ──────────────────────────────────────
    if not otp_received:
        # 1. Cancel on API (website ka paisa wapas)
        try: cancel_order_api(str(oid), source)
        except Exception as e: logger.error(f"Cancel API fail {oid}: {e}")

        # 2. Mark cancelled in DB
        try:
            orders_col.update_one({"order_id": str(oid)},
                {"$set": {"status": "cancelled", "otp": None}})
        except Exception as e: logger.error(f"DB cancel fail {oid}: {e}")

        # 3. Refund user balance
        refund_ok = False
        try:
            add_balance(uid, refund)
            refund_ok = True
            logger.info(f"✅ Refund ₹{refund} done → user {uid}, order {oid}")
        except Exception as e:
            logger.error(f"CRITICAL REFUND FAIL user={uid} order={oid}: {e}")
            try:
                bot.send_message(OWNER_ID,
                    f"🚨 *REFUND FAILED — MANUAL ACTION NEEDED!*\n\n"
                    f"👤 User: `{uid}`\n💵 Amount: ₹{refund:.0f}\n"
                    f"📦 Order: `{oid}`\n❌ Error: {str(e)[:100]}\n\n"
                    f"Manual karo: `/add {uid} {int(refund)}`")
            except: pass

        # 4. Notify user
        u2 = users_col.find_one({"user_id": uid}) or {}
        fresh_bal = u2.get('balance', rbal + (refund if refund_ok else 0))
        try:
            if refund_ok:
                bot.send_message(cid,
                    f"⏰ *OTP Timeout*\n\n"
                    f"📞 `{num}`\n"
                    f"{svc['flag']} {svc['country']} | {cat}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"❌ 5 min mein OTP nahi aaya\n"
                    f"✅ *₹{refund:.0f} Auto Refund Ho Gaya!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 Naya Balance: *₹{fresh_bal:.0f}*\n\n"
                    f"_Dobara try karein ya support se contact karein_\n"
                    f"📞 {SUPPORT_BOT}")
            else:
                bot.send_message(cid,
                    f"⏰ *OTP Timeout*\n\n📞 `{num}`\n"
                    f"❌ OTP nahi aaya\n\n"
                    f"⚠️ *Refund mein issue aayi!*\n"
                    f"📞 *Turant contact karein:* {SUPPORT_BOT}\n"
                    f"Order ID: `{oid}` | Amount: ₹{refund:.0f}")
        except Exception as e: logger.error(f"Timeout msg send: {e}")

def _post_proof(uid, num, svc, cat, amt, otp, source):
    u = users_col.find_one({"user_id": uid}) or {}
    name   = u.get('full_name') or f"User{str(uid)[-4:]}"
    masked = num[:4] + "****" + num[-2:] if len(num) > 6 else num
    src_n  = {"dgotp": "DgOTP.in", "smspool": "SmsPool", "vaksms": "Vak-SMS"}.get(source, "DgOTP.in")
    text   = (f"✅ *OTP Delivered!*\n\n📞 `{masked}`\n"
              f"📍 {svc['flag']} {svc['country']} | {cat}\n"
              f"💵 ₹{amt:.0f} | 🔗 {src_n}\n"
              f"🔑 OTP: `{otp}`\n👤 {name}\n"
              f"🕐 {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC\n👑 *OtpKing*")
    for dest in [PROOF_CHANNEL_ID, GROUP_ID]:
        try: bot.send_message(dest, text)
        except Exception as e: logger.warning(f"Proof to {dest}: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  FORCE CHANNELS
# ══════════════════════════════════════════════════════════════════════════════
def get_force_channels():
    try: return list(channels_col.find({"active": True}))
    except: return []

def is_joined(uid):
    ok = ['member', 'administrator', 'creator']
    for ch in get_force_channels():
        try:
            if bot.get_chat_member(ch['channel_id'], uid).status not in ok:
                return False
        except: pass
    return True

def join_markup():
    m = types.InlineKeyboardMarkup(row_width=1)
    for ch in get_force_channels():
        icon = "📢" if ch.get('type') == 'channel' else "👥"
        m.add(types.InlineKeyboardButton(f"{icon} {ch['name']} Join Karein ✅", url=ch['link']))
    m.add(types.InlineKeyboardButton("🔄 Join Kiya — Verify Karein", callback_data="check_join"))
    return m

# ══════════════════════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_user(uid, uname=None, fname=None):
    try:
        users_col.find_one_and_update(
            {"user_id": uid},
            {"$setOnInsert": {
                "user_id": uid, "username": uname or "", "full_name": fname or "",
                "balance": 0.0, "total_spent": 0.0, "orders": 0,
                "banned": False, "joined_at": datetime.utcnow(),
            }},
            upsert=True, return_document=True)
        if uname or fname:
            upd = {}
            if uname: upd["username"] = uname
            if fname:  upd["full_name"] = fname
            if upd: users_col.update_one({"user_id": uid}, {"$set": upd})
        return users_col.find_one({"user_id": uid})
    except Exception as e:
        logger.error(f"get_user: {e}")
        return {"user_id": uid, "balance": 0, "total_spent": 0, "orders": 0, "banned": False}

def find_user_by_username(username):
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
            "created_at": datetime.utcnow(),
        })
    except Exception as e: logger.error(f"log_order: {e}")

def log_admin_action(admin_id, uid, amount, action_type, note=""):
    try:
        admin_log_col.insert_one({
            "admin_id": admin_id, "user_id": uid,
            "amount": amount, "type": action_type,
            "note": note, "created_at": datetime.utcnow(),
        })
    except Exception as e: logger.error(f"admin_log: {e}")

def find_svc(key):
    for cat, items in SERVICES.items():
        if key in items: return items[key], cat
    return None, None

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
            bot.send_message(msg.chat.id, "⚠️ *Pehle join karein:*", reply_markup=join_markup()); return
        fn(msg)
    return w

def gaali_check(fn):
    def w(msg):
        if msg.from_user.id == OWNER_ID: fn(msg); return
        if any(x in (msg.text or "").lower() for x in BAD_WORDS):
            uid = msg.from_user.id
            users_col.update_one({"user_id": uid}, {"$set": {"banned": True}})
            bot.send_message(uid, f"🚫 *Block! Gaali = Ban.*\nAppeal: {SUPPORT_BOT}")
            try: bot.send_message(OWNER_ID,
                f"⚠️ Auto-Ban\n👤 {msg.from_user.first_name}\n🆔 `{uid}`\n💬 `{msg.text}`")
            except: pass
            return
        fn(msg)
    return w

def owner_only(fn):
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
    m.add("📊 Stats",          "👥 Users")
    m.add("📋 Pending Dep",    "💹 API Balances")
    m.add("🔑 API Keys",       "📡 Channels")
    m.add("📢 Broadcast",      "🏆 Top Buyers")
    m.add("📦 Orders",         "📈 Stock")
    m.add("➕ Platform Add",   "💾 Export")
    m.add("📡 Force Ch Manage","⚙️ Bot Settings")
    m.add("💰 Balance Adjust", "🔍 User Search")
    m.add("📜 Balance Log",    "💵 Quick Balance")
    m.add("📊 Live Price Check")
    m.add("🔙 Back")
    return m

ADMIN_BTNS = {
    "📊 Stats","👥 Users","📋 Pending Dep","💹 API Balances","🔑 API Keys",
    "📡 Channels","📢 Broadcast","🏆 Top Buyers","📦 Orders","📈 Stock",
    "➕ Platform Add","💾 Export","📡 Force Ch Manage","⚙️ Bot Settings",
    "💰 Balance Adjust","🔍 User Search","📜 Balance Log",
    "💵 Quick Balance","📊 Live Price Check",
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
    args = msg.text.split()
    if len(args) > 1:
        try:
            ref_uid = int(args[1])
            if ref_uid != uid:
                users_col.update_one({"user_id": uid},
                    {"$setOnInsert": {"referred_by": ref_uid}}, upsert=True)
        except: pass
    get_user(uid, msg.from_user.username, msg.from_user.first_name)
    if uid != OWNER_ID and get_force_channels() and not is_joined(uid):
        bot.send_message(uid, "⚠️ *OtpKing Bot*\n\nPehle join karein 👇",
            reply_markup=join_markup()); return
    _greet(uid, msg.from_user.first_name or "Dost")

def _greet(uid, name):
    bot.send_message(uid,
        f"👑 *OtpKing Bot*\nWelcome *{name}* ji! 🙏\n\n"
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
        bot.answer_callback_query(call.id, "❌ Sabhi channels join nahi kiye!", show_alert=True)

# ══════════════════════════════════════════════════════════════════════════════
#  BUY NUMBER FLOW
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
    cat   = msg.text
    uid   = msg.from_user.id
    items = SERVICES.get(cat, {})

    # ── Check balance FIRST before loading prices ────────────────────────────
    if uid != OWNER_ID:
        u   = get_user(uid)
        bal = u.get('balance', 0)
        if bal <= 0:
            mk = types.InlineKeyboardMarkup(row_width=1)
            mk.add(
                types.InlineKeyboardButton("💎 USDT Deposit (Binance TRC20)", callback_data="d_usdt"),
                types.InlineKeyboardButton("🇮🇳 UPI Deposit",                  callback_data="d_upi"),
            )
            bot.send_message(msg.chat.id,
                f"💰 *Pehle Deposit Karein!*\n\n"
                f"🛒 Service: *{cat}*\n"
                f"👛 Aapka Balance: *₹{bal:.0f}*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Number khareedne ke liye pehle wallet mein paisa daalna hoga.\n\n"
                f"👇 Deposit method chunein:", reply_markup=mk)
            return

    # ── Load prices ──────────────────────────────────────────────────────────
    lm  = bot.send_message(msg.chat.id, f"⏳ *{cat}* — Live prices load ho rahi hain...")
    mk  = types.InlineKeyboardMarkup(row_width=1)
    has = False

    for key, info in items.items():
        sell, stock, src, ssp, svk = best_price(info['cc'], info['api'])
        if sell and stock > 0:
            has = True
            if src == 'default': stock_ic = "🟢"
            elif stock <= LOW_STOCK: stock_ic = "🔴"
            elif stock <= 20: stock_ic = "🟡"
            else: stock_ic = "🟢"
            mk.add(types.InlineKeyboardButton(
                f"{info['flag']} {info['country']}  ·  ₹{sell}  ·  {stock_ic}{stock}",
                callback_data=f"buy_{key}"))

    mk.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=f"ref_{cat.replace(' ','_')}"))
    mk.add(types.InlineKeyboardButton("🔙 Back",    callback_data="go_back_menu"))

    txt = f"*{cat}* — Country & Stock chunein:" if has else \
          f"*{cat}*\n\n❌ Abhi koi stock available nahi.\nThodi der baad try karein."
    try: bot.edit_message_text(txt, lm.chat.id, lm.message_id, reply_markup=mk)
    except Exception as e: logger.error(f"edit_message: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("ref_"))
def cb_refresh(call):
    cat_raw = call.data[4:].replace("_", " ")
    matched = next((s for s in SERVICES if s.replace(" ","_") == call.data[4:] or s == cat_raw), None)
    if not matched:
        bot.answer_callback_query(call.id, "❌ Service nahi mili", show_alert=True); return
    bot.answer_callback_query(call.id, "⏳ Refreshing...")
    items = SERVICES[matched]
    for _, info in items.items(): _pc.pop(f"{info['cc']}|{info['api']}", None)
    mk = types.InlineKeyboardMarkup(row_width=1)
    has = False
    for key, info in items.items():
        sell, stock, src, ssp, svk = best_price(info['cc'], info['api'])
        if sell and stock > 0:
            has = True
            stock_ic = "🟢" if src == 'default' else ("🔴" if stock <= LOW_STOCK else ("🟡" if stock <= 20 else "🟢"))
            mk.add(types.InlineKeyboardButton(
                f"{info['flag']} {info['country']}  ·  ₹{sell}  ·  {stock_ic}{stock}",
                callback_data=f"buy_{key}"))
    mk.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=call.data))
    mk.add(types.InlineKeyboardButton("🔙 Back",    callback_data="go_back_menu"))
    txt = f"*{matched}* — Country & Stock chunein:" if has else \
          f"*{matched}*\n\n❌ Abhi koi stock nahi.\nThodi der baad try karein."
    try: bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mk)
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

    # Fresh price — clear cache for accurate price
    _pc.pop(f"{svc['cc']}|{svc['api']}", None)
    sell, cnt, src, ssp, svk = best_price(svc['cc'], svc['api'])

    if not sell:
        return bot.answer_callback_query(call.id,
            "❌ Price nahi mila. Admin se contact karein.", show_alert=True)

    # ── Balance check ────────────────────────────────────────────────────────
    u   = get_user(uid)
    bal = u.get('balance', 0)
    if bal < sell:
        short = sell - bal
        mk = types.InlineKeyboardMarkup(row_width=1)
        mk.add(
            types.InlineKeyboardButton("💰 Deposit Karein — USDT", callback_data="d_usdt"),
            types.InlineKeyboardButton("🇮🇳 Deposit Karein — UPI",  callback_data="d_upi"),
        )
        bot.answer_callback_query(call.id,
            f"❌ Balance kam hai! ₹{short:.0f} aur chahiye.", show_alert=True)
        bot.send_message(call.message.chat.id,
            f"💰 *Balance Kam Hai!*\n\n"
            f"🛒 {svc['flag']} {svc['country']} | {cat}\n"
            f"💵 Price: *₹{sell:.0f}*\n"
            f"👛 Aapka Balance: ₹{bal:.0f}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 Aur chahiye: *₹{short:.0f}*\n\n"
            f"👇 Deposit karein fir dobara try karein:", reply_markup=mk)
        return

    # ── Try to buy number ────────────────────────────────────────────────────
    bot.answer_callback_query(call.id, "⏳ Number dhundh rahe hain...")
    sm = bot.send_message(call.message.chat.id,
        f"🔄 *Processing...*\n"
        f"{svc['flag']} {svc['country']} | {cat}\n"
        f"💵 ₹{sell:.0f} balance se katega\n"
        f"⏳ Please wait...")

    oid, num, used_src = smart_buy(svc['cc'], svc['api'])

    if oid and num:
        # ── SUCCESS ──────────────────────────────────────────────────────────
        success = deduct_balance(uid, sell)
        if not success:
            cancel_order_api(str(oid), used_src)
            bot.edit_message_text(
                "❌ Balance deduct nahi hua. Dobara try karein.",
                call.message.chat.id, sm.message_id)
            return
        u2       = users_col.find_one({"user_id": uid}) or {}
        nb       = u2.get('balance', 0)
        src_icon = {"smspool": "🌐", "vaksms": "🔷", "dgotp": "🟡"}.get(used_src, "📋")
        src_name = {"smspool": "SmsPool", "vaksms": "Vak-SMS", "dgotp": "DgOTP"}.get(used_src, "API")
        log_order(uid, cat, svc, num, oid, sell, used_src)
        bot.edit_message_text(
            f"✅ *Number Mila!*\n\n"
            f"📞 `{num}`\n"
            f"{svc['flag']} {svc['country']} | {cat}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 ₹{sell:.0f} kata | Balance: ₹{nb:.0f}\n"
            f"{src_icon} Source: {src_name}\n\n"
            f"⏳ *OTP har 10 sec check ho raha hai...*\n"
            f"_(Max 5 min — OTP nahi aaya to Auto Refund)_ ✅",
            call.message.chat.id, sm.message_id)
        Thread(target=_otp_wait,
            args=(call.message.chat.id, uid, str(oid), sell, num, svc, cat, nb, used_src),
            daemon=True).start()

    else:
        # ── FAIL — APIs ka balance nahi / down ───────────────────────────────
        # User ka balance nahi kata — completely safe
        mk = types.InlineKeyboardMarkup(row_width=1)
        mk.add(types.InlineKeyboardButton("🔄 Dobara Try Karein", callback_data=f"buy_{key}"))
        mk.add(types.InlineKeyboardButton("📞 Support",
            url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
        bot.edit_message_text(
            f"⚠️ *Number Abhi Nahi Mila*\n\n"
            f"{svc['flag']} {svc['country']} | {cat}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 Kya hua:\n"
            f"• APIs ka balance temporarily khatam ho sakta hai\n"
            f"• Ya is waqt us country ka stock nahi hai\n\n"
            f"✅ *Aapka ₹{sell:.0f} balance bilkul safe hai*\n"
            f"_Kuch nahi kata_\n\n"
            f"👇 Dobara try karein ya admin se contact karein:",
            call.message.chat.id, sm.message_id, reply_markup=mk)

# ══════════════════════════════════════════════════════════════════════════════
#  WALLET & DEPOSIT
# ══════════════════════════════════════════════════════════════════════════════
_dep_method = {}

@bot.message_handler(func=lambda m: m.text == "💰 Wallet")
@ban_check
@join_check
def wallet(msg):
    u = get_user(msg.from_user.id)
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
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
        f"👇 Deposit karein:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "d_usdt")
def cb_usdt(call):
    addr = BINANCE_ADDRESS or f"⚠️ Admin ne address set nahi kiya — Contact: {SUPPORT_BOT}"
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("✅ Screenshot Submit Karo", callback_data="d_proof_usdt"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="d_back"))
    _dep_method[call.from_user.id] = "USDT"
    bot.send_message(call.message.chat.id,
        "💎 *USDT Deposit — TRC20 (Binance)*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *Wallet Address:*\n"
        f"`{addr}`\n_(Tap karke copy karein)_\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Steps:*\n"
        "1️⃣ Upar address copy karein\n"
        "2️⃣ Crypto app kholen\n"
        "3️⃣ *Network: TRC20 ONLY* chunein ⚠️\n"
        "4️⃣ Amount transfer karein\n"
        "5️⃣ Screenshot le ke yahan bhejein 📸\n\n"
        "⏰ _10-30 min mein approve hoga_", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "d_upi")
def cb_upi(call):
    upi = UPI_ID or f"⚠️ Admin ne UPI set nahi kiya — Contact: {SUPPORT_BOT}"
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("✅ Screenshot Submit Karo", callback_data="d_proof_upi"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="d_back"))
    _dep_method[call.from_user.id] = "UPI"
    bot.send_message(call.message.chat.id,
        "🇮🇳 *UPI Deposit*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 *UPI ID:* `{upi}`\n_(Tap karke copy karein)_\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Steps:*\n"
        "1️⃣ UPI ID copy karein\n"
        "2️⃣ PhonePe / GPay / Paytm kholen\n"
        "3️⃣ Amount transfer karein\n"
        "4️⃣ Screenshot le ke yahan bhejein 📸\n\n"
        "⏰ _10-30 min mein approve hoga_", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ["d_proof_usdt","d_proof_upi"])
def cb_dep_proof(call):
    method = "USDT" if call.data == "d_proof_usdt" else "UPI"
    _dep_method[call.from_user.id] = method
    bot.send_message(call.message.chat.id,
        f"📸 *Screenshot Bhejein*\n\n"
        f"Method: *{method}*\n"
        f"Abhi payment screenshot yahan bhejein 👇")

@bot.callback_query_handler(func=lambda c: c.data == "d_back")
def cb_dep_back(call):
    u = get_user(call.from_user.id)
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("💎 USDT Deposit (Binance TRC20)", callback_data="d_usdt"),
        types.InlineKeyboardButton("🇮🇳 UPI / QR Code Deposit",       callback_data="d_upi"),
        types.InlineKeyboardButton("📊 Transaction History",           callback_data="d_hist"),
    )
    bot.send_message(call.message.chat.id,
        f"💳 Balance: *₹{u.get('balance',0):.0f}*", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "d_hist")
def cb_hist(call):
    uid    = call.from_user.id
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
    else:
        t += "📭 Koi order nahi."
    bot.send_message(call.message.chat.id, t)

@bot.message_handler(content_types=['photo'])
def on_photo(msg):
    if msg.from_user.id == OWNER_ID: return
    uid    = msg.from_user.id
    method = _dep_method.pop(uid, "USDT/UPI")
    deposits_col.insert_one({
        "user_id": uid, "username": msg.from_user.username or "",
        "full_name": msg.from_user.first_name or "", "amount": 0.0,
        "status": "pending", "method": method,
        "message_id": msg.message_id, "created_at": datetime.utcnow(),
    })
    try: bot.forward_message(OWNER_ID, msg.chat.id, msg.message_id)
    except: pass
    icon = "💎" if method == "USDT" else "🇮🇳"
    mk   = types.InlineKeyboardMarkup(row_width=2)
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
            f"{icon} Method: *{method}*\n"
            f"👤 {msg.from_user.first_name} (@{msg.from_user.username or 'N/A'})\n"
            f"🆔 `{uid}`\n\n"
            f"Manual: `/add {uid} AMOUNT`\n"
            f"Reject: `/reject {uid}`\n\n"
            f"👇 Quick approve:", reply_markup=mk)
    except Exception as e: logger.error(f"Admin notify: {e}")
    try:
        bot.forward_message(PROOF_CHANNEL_ID, msg.chat.id, msg.message_id)
        bot.send_message(PROOF_CHANNEL_ID,
            f"💰 *Deposit Request*\n{icon} {method}\n"
            f"👤 {msg.from_user.first_name}\n⏳ Pending...\n👑 OtpKing")
    except: pass
    bot.reply_to(msg,
        "✅ *Screenshot mila!*\n\n"
        "⏳ Admin verify kar raha hai.\n"
        "_10-30 min mein balance add hoga._\n\n"
        f"📞 Help: {SUPPORT_BOT}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("qadd_") and c.data.count("_") == 2)
def cb_quick_add(call):
    if call.from_user.id != OWNER_ID: return
    try:
        parts  = call.data.split("_")
        uid    = int(parts[1]); amount = float(parts[2])
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
        bot.send_message(uid, f"❌ *Deposit Reject Hua.*\nScreenshot unclear tha.\nRetry: {SUPPORT_BOT}")
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
        f"💬 User `{uid}` ko kitna add karna hai?\nAmount bhejein (e.g. `850`)\n/cancel")

def _do_approve(uid, amount, method, call=None):
    if not add_balance(uid, amount):
        if call: bot.answer_callback_query(call.id, f"❌ User {uid} nahi mila!", show_alert=True)
        return
    deposits_col.update_one(
        {"user_id": uid, "status": "pending"},
        {"$set": {"status": "approved", "amount": amount, "method": method}},
        sort=[("created_at", -1)])
    log_admin_action(OWNER_ID, uid, amount, "add", f"deposit:{method}")
    u = users_col.find_one({"user_id": uid}) or {}
    nb   = u.get('balance', amount)
    icon = "💎" if "usdt" in method.lower() else "🇮🇳"
    bot.send_message(uid,
        f"🎉 *Deposit Approved!*\n\n"
        f"{icon} *{method.upper()}* → ₹{amount:.0f} add!\n\n"
        f"💵 *Naya Balance: ₹{nb:.0f}*\n\n"
        f"📲 *Buy Number* dabayein 🛒")
    try:
        bot.send_message(PROOF_CHANNEL_ID,
            f"✅ *Deposit Approved!*\n{icon} {method} → ₹{amount:.0f}\n"
            f"👤 `{uid}` | Balance: ₹{nb:.0f}\n"
            f"🕐 {datetime.utcnow().strftime('%d %b %H:%M')} UTC\n👑 OtpKing")
    except: pass
    if call:
        bot.answer_callback_query(call.id, f"✅ ₹{amount:.0f} added! Bal: ₹{nb:.0f}")
        try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except: pass
        bot.send_message(OWNER_ID, f"✅ *Done!* `{uid}` → ₹{amount:.0f}\nBal: ₹{nb:.0f}")

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
        t += (f"{ic} `{o['number']}`\n"
              f"   {o['service']} ₹{o.get('amount',0):.0f}\n"
              f"   {o['created_at'].strftime('%d %b %H:%M')}\n\n")
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
            f"👥 *Refer & Earn*\n\n⚠️ Abhi koi platform add nahi hua.\nAdmin: {SUPPORT_BOT}",
            reply_markup=main_menu(msg.from_user.id)); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for p in platforms:
        mk.add(types.InlineKeyboardButton(f"💰 {p['name']}", callback_data=f"earn_{str(p['_id'])}"))
    bot.send_message(msg.chat.id, "👥 *Refer & Earn*\n\n👇 Platform chunein:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("earn_"))
def cb_earn(call):
    from bson import ObjectId
    try: p = platforms_col.find_one({"_id": ObjectId(call.data[5:])})
    except: p = None
    if not p:
        bot.answer_callback_query(call.id, "❌ Platform nahi mila!", show_alert=True); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("🔗 Register Karein", url=p['link']))
    if p.get('video'):
        mk.add(types.InlineKeyboardButton("🎥 Video Tutorial", url=p['video']))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="earn_back"))
    bot.send_message(call.message.chat.id,
        f"💰 *{p['name']}*\n\n👇 Register karein aur earn karein!\n🔗 {p['link']}", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "earn_back")
def cb_earn_back(call):
    platforms = list(platforms_col.find())
    if not platforms:
        bot.send_message(call.message.chat.id, "📭 Koi platform nahi.",
            reply_markup=main_menu(call.from_user.id)); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for p in platforms:
        mk.add(types.InlineKeyboardButton(f"💰 {p['name']}", callback_data=f"earn_{str(p['_id'])}"))
    bot.send_message(call.message.chat.id, "👥 *Refer & Earn*\n\n👇 Platform chunein:", reply_markup=mk)

# ══════════════════════════════════════════════════════════════════════════════
#  PROOF / HELP / SUPPORT
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📊 Proof")
@ban_check
@join_check
def proof(msg):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📢 Proof Channel", url=PROOF_CHANNEL_LINK))
    mk.add(types.InlineKeyboardButton("👥 Group",         url=GROUP_LINK))
    bot.send_message(msg.chat.id, "📊 *OtpKing Proof*\n\nHumari successful deliveries dekho! 👇",
        reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🆘 Help")
@ban_check
@join_check
def help_msg(msg):
    bot.send_message(msg.chat.id,
        "🆘 *OtpKing — Help*\n\n"
        "📲 *Buy Number*\n"
        "→ Service → Country → Number milega → OTP aayega (max 5 min)\n"
        "→ OTP nahi aaya? Auto Refund hoga ✅\n\n"
        "💰 *Wallet*\n"
        "→ USDT (TRC20) ya UPI se deposit karo\n"
        "→ Screenshot bhejo → 10-30 min mein approve\n\n"
        "📋 *My Orders* → Apne orders dekho\n\n"
        "👥 *Refer & Earn* → Earning platforms dekho\n\n"
        f"📞 *Support:* {SUPPORT_BOT}")

@bot.message_handler(func=lambda m: m.text == "📞 Support")
@ban_check
def support(msg):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("💬 Admin se Contact",
        url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    bot.send_message(msg.chat.id, f"📞 *Support*\n\n{SUPPORT_BOT} pe message karein!", reply_markup=mk)

# ══════════════════════════════════════════════════════════════════════════════
#  FORCE CHANNEL MANAGEMENT (Admin)
# ══════════════════════════════════════════════════════════════════════════════
_ch_add_state = {}

@bot.message_handler(func=lambda m: m.text == "📡 Force Ch Manage" and m.from_user.id == OWNER_ID)
def ab_force_ch(msg):
    channels = get_force_channels()
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("➕ Channel Add Karein", callback_data="fch_add_channel"),
        types.InlineKeyboardButton("➕ Group Add Karein",   callback_data="fch_add_group"),
    )
    for ch in channels:
        icon = "📢" if ch.get('type') == 'channel' else "👥"
        mk.add(types.InlineKeyboardButton(
            f"🗑 Remove: {icon} {ch['name']}", callback_data=f"fch_del_{str(ch['_id'])}"))
    txt = (f"📡 *Force Channel/Group*\n\n{len(channels)} channel(s) active hain."
           if channels else "📡 *Force Channel/Group*\n\nAbhi koi channel add nahi hua.")
    bot.send_message(msg.chat.id, txt, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ["fch_add_channel","fch_add_group"])
def cb_fch_add(call):
    if call.from_user.id != OWNER_ID: return
    ch_type = "channel" if call.data == "fch_add_channel" else "group"
    _ch_add_state[OWNER_ID] = {"step": 1, "type": ch_type}
    bot.answer_callback_query(call.id)
    icon = "📢" if ch_type == "channel" else "👥"
    bot.send_message(OWNER_ID,
        f"➕ *Naya {icon} Add Karein*\n\n"
        f"*Step 1/3:* Naam bhejein\n_Example: OtpKing Official_\n\n/cancel se cancel")

@bot.callback_query_handler(func=lambda c: c.data.startswith("fch_del_"))
def cb_fch_del(call):
    if call.from_user.id != OWNER_ID: return
    from bson import ObjectId
    try:
        ch = channels_col.find_one({"_id": ObjectId(call.data[8:])})
        channels_col.delete_one({"_id": ObjectId(call.data[8:])})
        bot.answer_callback_query(call.id, f"✅ {ch['name'] if ch else 'Channel'} removed!")
        bot.send_message(OWNER_ID, f"✅ *Channel Remove Ho Gaya!*\n{'📢' if ch and ch.get('type')=='channel' else '👥'} {ch['name'] if ch else 'Unknown'}")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {e}", show_alert=True)

def handle_ch_add_steps(msg):
    if (msg.text or "").startswith('/'): return
    state = _ch_add_state.get(OWNER_ID, {})
    step  = state.get("step", 0)
    ch_type = state.get("type", "channel")
    icon    = "📢" if ch_type == "channel" else "👥"
    if step == 1:
        state["name"] = msg.text.strip(); state["step"] = 2
        _ch_add_state[OWNER_ID] = state
        bot.send_message(msg.chat.id,
            f"✅ Naam: *{state['name']}*\n\n*Step 2/3:* Channel ID bhejein\n_Example: @Channel ya -1001234567890_")
    elif step == 2:
        state["channel_id"] = msg.text.strip(); state["step"] = 3
        _ch_add_state[OWNER_ID] = state
        bot.send_message(msg.chat.id,
            f"✅ ID: `{state['channel_id']}`\n\n*Step 3/3:* Invite link bhejein\n_Example: https://t.me/..._")
    elif step == 3:
        link = msg.text.strip()
        if not link.startswith("http"):
            bot.send_message(msg.chat.id, "❌ Valid link chahiye (https:// se shuru ho)"); return
        sd = _ch_add_state.pop(OWNER_ID, {})
        try:
            channels_col.update_one(
                {"channel_id": sd["channel_id"]},
                {"$set": {"channel_id": sd["channel_id"], "name": sd["name"],
                          "link": link, "type": sd["type"],
                          "active": True, "added_at": datetime.utcnow()}},
                upsert=True)
            bot.send_message(msg.chat.id,
                f"✅ *{icon} Add Ho Gaya!*\n\n"
                f"📛 {sd['name']}\n🆔 `{sd['channel_id']}`\n🔗 {link}\n\n"
                f"⚠️ Bot ko Admin banana na bhoolein!")
        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Error: {e}")

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
    recent = list(users_col.find().sort("joined_at", DESCENDING).limit(5))
    t = f"👥 *Users*\nTotal: `{tu}` | Active: `{ac}` | Banned: `{bn}`\n\n*Recent:*\n"
    for u in recent:
        t += f"• `{u['user_id']}` {u.get('full_name','?')} ₹{u.get('balance',0):.0f}\n"
    t += f"\n🔍 Details: `/userinfo USER_ID`"
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
    # DgOTP balance
    try:
        r = requests.get(DGOTP_BASE,
            params={"api_key": DGOTP_KEY, "action": "getBalance"}, timeout=10).text.strip()
        if r.startswith("ACCESS_BALANCE:"):
            bal = float(r.split(":")[1])
            w   = " ⚠️ RECHARGE KARO!" if bal < 50 else (" ⚠️ Low" if bal < 200 else "")
            ic  = "✅" if bal >= 50 else "❌"
            results.append(f"{ic} DgOTP.in: *₹{bal:.2f}*{w}")
        else:
            results.append(f"⚠️ DgOTP response: `{r[:50]}`")
    except Exception as e:
        results.append(f"❌ DgOTP: {str(e)[:40]}")

    bot.send_message(msg.chat.id,
        "💹 *API Balances*\n\n" + "\n".join(results) +
        f"\n\n🔷 DgOTP Margin: *{int((DGOTP_MARGIN-1)*100)}%* (fixed)\n"
        f"📊 User price = DgOTP raw × {DGOTP_MARGIN}\n\n"
        f"ℹ️ Balance ₹50 se upar rakhen — orders fail na hon")

_last_keys_time = {}

@bot.message_handler(func=lambda m: m.text == "🔑 API Keys" and m.from_user.id == OWNER_ID)
def ab_keys(msg):
    # Debounce — prevent spam
    now = time.time()
    if now - _last_keys_time.get(OWNER_ID, 0) < 3:
        return
    _last_keys_time[OWNER_ID] = now

    results = [
        f"{'✅' if DGOTP_KEY else '❌'} DGOTP_API_KEY: {'Set ✅' if DGOTP_KEY else 'NOT SET ❌ — Set karein Railway mein!'}",
        f"🔷 DGOTP_BASE: `{DGOTP_BASE}`",
        f"📈 DGOTP Margin: {int((DGOTP_MARGIN-1)*100)}% (fixed)",
        f"{'✅' if BINANCE_ADDRESS else '⚠️'} BINANCE_ADDRESS: {'Set ✅' if BINANCE_ADDRESS else 'NOT SET'}",
        f"{'✅' if UPI_ID else '⚠️'} UPI_ID: `{UPI_ID or 'Not set'}`",
        f"✅ OWNER_ID: `{OWNER_ID}`",
    ]
    try:
        cnt = users_col.count_documents({})
        results.append(f"✅ MongoDB: Connected ({cnt} users)")
    except Exception as e: results.append(f"❌ MongoDB: {str(e)[:40]}")
    results.append(f"📡 Force Channels: {channels_col.count_documents({'active': True})} active")

    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton(
        "📖 Railway Variables Guide", callback_data="show_railway_guide"))

    bot.send_message(msg.chat.id,
        "🔑 *Config Status*\n\n" + "\n".join(results) +
        "\n\n━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Railway mein keys set karne ke liye 👇",
        reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "show_railway_guide")
def cb_railway_guide(call):
    if call.from_user.id != OWNER_ID: return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "🚂 *Railway Variables Setup Guide*\n\n"
        "1️⃣ railway.app kholo\n"
        "2️⃣ Apna project select karo\n"
        "3️⃣ *Variables* tab click karo\n"
        "4️⃣ *New Variable* button dabao\n"
        "5️⃣ Yeh variables add karo:\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "`BOT_TOKEN` = Telegram bot token\n"
        "`MONGO_URI` = MongoDB connection string\n"
        "`OWNER_ID` = Aapka Telegram ID\n"
        "`DGOTP_API_KEY` = DgOTP.in API key ⭐\n"
        "`BINANCE_ADDRESS` = TRC20 wallet\n"
        "`UPI_ID` = UPI ID\n"
        "`SUPPORT_BOT` = @YourSupportBot\n"
        "`PROOF_CHANNEL_ID` = @ProofChannel\n"
        "`PROOF_CHANNEL_LINK` = https://t.me/...\n"
        "`GROUP_ID` = @YourGroup\n"
        "`GROUP_LINK` = https://t.me/...\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "6️⃣ *Deploy* karo\n\n"
        "🟡 *DgOTP API Key kahan milegi:*\n"
        "dgotp.in → Login → Profile → API Key copy karo")

@bot.message_handler(func=lambda m: m.text == "📡 Channels" and m.from_user.id == OWNER_ID)
def ab_channels(msg):
    channels = get_force_channels()
    t = f"📡 *Force Channels ({len(channels)} active)*\n\n"
    for ch in channels:
        icon = "📢" if ch.get('type') == 'channel' else "👥"
        t += f"{icon} *{ch['name']}*\n🆔 `{ch['channel_id']}`\n🔗 {ch['link']}\n\n"
    if not channels: t += "Koi channel nahi.\n'📡 Force Ch Manage' se add karein."
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.from_user.id == OWNER_ID)
def ab_bc(msg): bot.send_message(msg.chat.id, "📢 `/broadcast Your message here`")

@bot.message_handler(func=lambda m: m.text == "🏆 Top Buyers" and m.from_user.id == OWNER_ID)
def ab_top(msg):
    r = list(orders_col.aggregate([
        {"$match": {"status":"done"}},
        {"$group": {"_id":"$user_id","total":{"$sum":"$amount"},"cnt":{"$sum":1}}},
        {"$sort": {"total":-1}}, {"$limit":10}]))
    if not r: bot.send_message(msg.chat.id,"📭 Koi buyer nahi."); return
    t = "🏆 *Top 10 Buyers*\n\n"
    for i, x in enumerate(r, 1):
        u = users_col.find_one({"user_id": x['_id']}) or {}
        t += f"{i}. {u.get('full_name','N/A')} `{x['_id']}` — ₹{x['total']:.0f} ({x['cnt']} orders)\n"
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "📦 Orders" and m.from_user.id == OWNER_ID)
def ab_orders(msg):
    orders = list(orders_col.find().sort("created_at",DESCENDING).limit(10))
    if not orders: bot.send_message(msg.chat.id,"📭"); return
    t = "📦 *Recent Orders*\n\n"
    for o in orders:
        ic  = "✅" if o['status']=="done" else ("❌" if o['status']=="cancelled" else "⏳")
        src = "🌐" if o.get('source')=='smspool' else ("🔷" if o.get('source')=='vaksms' else "📋")
        t  += (f"{ic}{src} `{o['number']}` {o['service']}\n"
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

@bot.message_handler(func=lambda m: m.text == "💾 Export" and m.from_user.id == OWNER_ID)
def ab_export(msg):
    users = list(users_col.find({},{"user_id":1,"username":1,"full_name":1,"balance":1,"orders":1,"banned":1}))
    lines = ["ID|Name|Username|Balance|Orders|Banned"]
    lines += [f"{u['user_id']}|{u.get('full_name','N/A')}|@{u.get('username','N/A')}|₹{u.get('balance',0):.0f}|{u.get('orders',0)}|{u.get('banned',False)}" for u in users]
    f = io.BytesIO("\n".join(lines).encode()); f.name = f"users_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.txt"
    bot.send_document(msg.chat.id, f, caption=f"📦 Total: {len(users)} users")

@bot.message_handler(func=lambda m: m.text == "🔙 Back" and m.from_user.id == OWNER_ID)
def ab_back_admin(msg):
    bot.send_message(msg.chat.id, "🏠", reply_markup=main_menu(OWNER_ID))

# ══════════════════════════════════════════════════════════════════════════════
#  BOT SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
_settings_state = {}

@bot.message_handler(func=lambda m: m.text == "⚙️ Bot Settings" and m.from_user.id == OWNER_ID)
def ab_bot_settings(msg):
    margin    = get_margin()
    usdt_rate = get_usdt_rate()
    warn = " ⚠️ BAHUT ZYADA!" if margin > 1.80 else ""
    mk   = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton(f"📈 Margin Set ({int((margin-1)*100)}%){warn}", callback_data="set_margin"),
        types.InlineKeyboardButton(f"💱 USDT Rate Set (₹{usdt_rate})",              callback_data="set_usdt_rate"),
        types.InlineKeyboardButton("🔄 Reset Margin to 40% (Recommended)",          callback_data="set_reset_margin"),
        types.InlineKeyboardButton("🗑 Price Cache Clear",                           callback_data="set_clear_cache"),
    )
    bot.send_message(msg.chat.id,
        f"⚙️ *Bot Settings*\n\n"
        f"📈 Margin: *{int((margin-1)*100)}%*{warn}\n"
        f"💱 USDT Rate: *₹{usdt_rate}*\n\n"
        f"_Recommended: Margin 40%, USDT Rate ₹85-90_", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ["set_margin","set_usdt_rate","set_clear_cache","set_reset_margin"])
def cb_settings(call):
    if call.from_user.id != OWNER_ID: return
    if call.data == "set_clear_cache":
        _pc.clear()
        bot.answer_callback_query(call.id, "✅ Cache cleared!")
        bot.send_message(OWNER_ID, "✅ *Price cache cleared!*\nAb fresh prices fetch honge.")
    elif call.data == "set_reset_margin":
        set_setting("margin", 1.40)
        _pc.clear()
        bot.answer_callback_query(call.id, "✅ Margin reset to 40%!")
        bot.send_message(OWNER_ID,
            "✅ *Margin Reset Ho Gaya!*\n\n📈 Naya Margin: *40%*\n🗑 Cache cleared!\nAb correct prices dikhenge.")
    elif call.data == "set_margin":
        _settings_state[OWNER_ID] = "margin"
        bot.answer_callback_query(call.id)
        bot.send_message(OWNER_ID,
            f"📈 *Margin Set Karein*\n\nCurrent: *{int((get_margin()-1)*100)}%*\n\n"
            f"Naya % bhejein (e.g. `40` for 40%)\nRange: 10–200%\n/cancel")
    elif call.data == "set_usdt_rate":
        _settings_state[OWNER_ID] = "usdt_rate"
        bot.answer_callback_query(call.id)
        bot.send_message(OWNER_ID,
            f"💱 *USDT Rate Set Karein*\n\nCurrent: *₹{get_usdt_rate()}*\n\n"
            f"Naya rate bhejein (e.g. `87.5`)\n/cancel")

# ══════════════════════════════════════════════════════════════════════════════
#  BALANCE ADJUST (old system — shows user profile + buttons)
# ══════════════════════════════════════════════════════════════════════════════
_bal_adjust_state = {}
_user_search_state = {}

@bot.message_handler(func=lambda m: m.text == "💰 Balance Adjust" and m.from_user.id == OWNER_ID)
def ab_balance_adjust(msg):
    _quick_bal_state.pop(OWNER_ID, None)
    _bal_adjust_state[OWNER_ID] = {"step": "uid"}
    bot.send_message(msg.chat.id,
        "💰 *Balance Adjust*\n\nUser ID ya @username bhejein:\n_Example: `12345678`_\n\n/cancel")

@bot.message_handler(func=lambda m: m.text == "🔍 User Search" and m.from_user.id == OWNER_ID)
def ab_user_search(msg):
    _user_search_state[OWNER_ID] = True
    bot.send_message(msg.chat.id,
        "🔍 *User Search*\n\nUser ID ya @username bhejein:\n_Example: `12345678` ya `@username`_\n\n/cancel")

@bot.message_handler(func=lambda m: m.text == "📜 Balance Log" and m.from_user.id == OWNER_ID)
def ab_balance_log(msg):
    logs = list(admin_log_col.find().sort("created_at", DESCENDING).limit(15))
    if not logs: bot.send_message(msg.chat.id, "📭 Koi log nahi."); return
    t = "📜 *Recent Balance Actions*\n\n"
    for l in logs:
        ic = "✅➕" if l['type'] == 'add' else ("🔄" if l['type'] == 'set' else "❌➖")
        t += (f"{ic} User `{l['user_id']}` — ₹{l.get('amount',0):.0f}\n"
              f"📝 {l.get('note','manual')}\n"
              f"🕐 {l['created_at'].strftime('%d %b %H:%M')}\n\n")
    bot.send_message(msg.chat.id, t)

def _show_user_for_adjust(cid, u):
    uid = u['user_id']
    done_orders = orders_col.count_documents({"user_id": uid, "status": "done"})
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
        f"🛒 Orders (done): `{done_orders}`\n"
        f"💸 Total Spent: `₹{u.get('total_spent',0):.0f}`\n"
        f"📅 Joined: {u.get('joined_at', datetime.utcnow()).strftime('%d %b %Y')}\n"
        f"Status: {ban_status}\n\n"
        f"⚠️ Min ₹100 | 👇 Balance adjust karein:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("badj_"))
def cb_balance_adjust(call):
    if call.from_user.id != OWNER_ID: return
    parts  = call.data.split("_")
    action = parts[1]

    if action == "ban":
        uid = int(parts[2])
        u   = users_col.find_one({"user_id": uid}) or {}
        new_ban = not u.get("banned", False)
        users_col.update_one({"user_id": uid}, {"$set": {"banned": new_ban}})
        status = "🚫 BANNED" if new_ban else "✅ Unbanned"
        bot.answer_callback_query(call.id, status)
        bot.send_message(OWNER_ID, f"{status} User `{uid}`")
        try:
            msg_txt = f"🚫 *Aap ban kar diye gaye hain.*\nSupport: {SUPPORT_BOT}" if new_ban \
                      else "✅ *Aapka ban hata diya gaya hai!*"
            bot.send_message(uid, msg_txt)
        except: pass
        return

    if action == "set":
        uid = int(parts[2])
        _bal_adjust_state[OWNER_ID] = {"step": "amount", "action": "set", "uid": uid}
        bot.answer_callback_query(call.id)
        u = users_col.find_one({"user_id": uid}) or {}
        bot.send_message(OWNER_ID,
            f"🔄 *Balance SET*\nUser `{uid}` — Current: ₹{u.get('balance',0):.0f}\n\nNaya exact balance bhejein:\n/cancel")
        return

    uid        = int(parts[2])
    amount_str = parts[3]
    if amount_str == "custom":
        action_name = "add" if action == "add" else "deduct"
        _bal_adjust_state[OWNER_ID] = {"step": "amount", "action": action_name, "uid": uid}
        bot.answer_callback_query(call.id)
        u = users_col.find_one({"user_id": uid}) or {}
        bot.send_message(OWNER_ID,
            f"💬 User `{uid}` — Balance: ₹{u.get('balance',0):.0f}\n"
            f"Kitna {'add' if action=='add' else 'deduct'} karna hai? (Min ₹100)\n/cancel")
        return

    amount   = float(amount_str)
    u_before = users_col.find_one({"user_id": uid}) or {}
    bb       = u_before.get('balance', 0)

    if action == "add":
        add_balance(uid, amount)
        log_admin_action(OWNER_ID, uid, amount, "add", "admin_panel")
        u_after = users_col.find_one({"user_id": uid}) or {}
        bot.answer_callback_query(call.id, f"✅ ₹{amount:.0f} add kiya!")
        bot.send_message(OWNER_ID,
            f"✅ *Add Done!*\n👤 `{uid}`\n₹{bb:.0f} → ₹{u_after.get('balance',0):.0f}\nAdded: ₹{amount:.0f}")
        try: bot.send_message(uid, f"✅ *₹{amount:.0f} Balance Add Hua!*\nNaya Balance: ₹{u_after.get('balance',0):.0f}")
        except: pass
    elif action == "ded":
        add_balance(uid, -amount)
        log_admin_action(OWNER_ID, uid, amount, "deduct", "admin_panel")
        u_after = users_col.find_one({"user_id": uid}) or {}
        bot.answer_callback_query(call.id, f"✅ ₹{amount:.0f} deduct kiya!")
        bot.send_message(OWNER_ID,
            f"✅ *Deduct Done!*\n👤 `{uid}`\n₹{bb:.0f} → ₹{u_after.get('balance',0):.0f}\nDeducted: ₹{amount:.0f}")
        try: bot.send_message(uid, f"❕ ₹{amount:.0f} balance deduct hua.\nNaya Balance: ₹{u_after.get('balance',0):.0f}")
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  QUICK BALANCE (new — ID → amount buttons → done)
# ══════════════════════════════════════════════════════════════════════════════
_quick_bal_state = {}

@bot.message_handler(func=lambda m: m.text == "💵 Quick Balance" and m.from_user.id == OWNER_ID)
def ab_quick_balance(msg):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("➕ Balance Add Karein",            callback_data="qbal_start_add"),
        types.InlineKeyboardButton("➖ Balance Deduct Karein",         callback_data="qbal_start_deduct"),
        types.InlineKeyboardButton("🔄 Balance Set Karein (Exact)",    callback_data="qbal_start_set"),
    )
    bot.send_message(msg.chat.id,
        "💵 *Quick Balance Management*\n\n"
        "➕ *Add* — Balance badhao\n"
        "➖ *Deduct* — Balance ghataao\n"
        "🔄 *Set* — Exact balance set karo\n\n"
        "⚠️ Minimum add/deduct: *₹100*", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("qbal_start_"))
def cb_qbal_start(call):
    if call.from_user.id != OWNER_ID: return
    action = call.data.replace("qbal_start_", "")
    # Clear all other states
    for s in [_bal_adjust_state, _user_search_state, _custom_add_state, _settings_state]:
        s.pop(OWNER_ID, None)
    _quick_bal_state[OWNER_ID] = {"step": "uid", "action": action}
    bot.answer_callback_query(call.id)
    at = "ADD ➕" if action == "add" else ("DEDUCT ➖" if action == "deduct" else "SET 🔄")
    bot.send_message(OWNER_ID,
        f"💵 *Balance {at}*\n\nUser ka *ID* ya *@username* bhejein:\n"
        f"_Example: `12345678` ya `@username`_\n\n/cancel")

@bot.message_handler(func=lambda m: (
    m.from_user.id == OWNER_ID
    and OWNER_ID in _quick_bal_state
    and m.text not in ADMIN_BTNS
    and not (m.text or "").startswith('/')
))
def handle_quick_bal_state(msg):
    txt   = (msg.text or "").strip()
    state = _quick_bal_state.get(OWNER_ID)
    if not state: return

    if state.get("step") == "uid":
        u = find_user_by_username(txt) if txt.startswith('@') else \
            users_col.find_one({"user_id": int(txt)}) if txt.isdigit() else None
        if not u:
            bot.send_message(msg.chat.id,
                f"❌ User `{txt}` nahi mila.\nSahi ID / @username bhejein ya /cancel"); return

        _quick_bal_state[OWNER_ID]["step"] = "amount"
        _quick_bal_state[OWNER_ID]["uid"]  = u["user_id"]
        action = state["action"]
        uid    = u["user_id"]
        mk     = types.InlineKeyboardMarkup(row_width=3)
        if action in ("add", "deduct"):
            px = "qadd" if action == "add" else "qded"
            mk.add(
                types.InlineKeyboardButton("₹100",  callback_data=f"{px}_qb_{uid}_100"),
                types.InlineKeyboardButton("₹200",  callback_data=f"{px}_qb_{uid}_200"),
                types.InlineKeyboardButton("₹500",  callback_data=f"{px}_qb_{uid}_500"),
                types.InlineKeyboardButton("₹1000", callback_data=f"{px}_qb_{uid}_1000"),
                types.InlineKeyboardButton("₹2000", callback_data=f"{px}_qb_{uid}_2000"),
                types.InlineKeyboardButton("₹5000", callback_data=f"{px}_qb_{uid}_5000"),
            )
            mk.add(types.InlineKeyboardButton("✏️ Custom Amount", callback_data=f"{px}_qb_{uid}_custom"))
        else:
            mk.add(types.InlineKeyboardButton("✏️ Exact Amount Bhejein", callback_data=f"qset_qb_{uid}_custom"))
        mk.add(types.InlineKeyboardButton("❌ Cancel", callback_data="qbal_cancel"))

        at = "ADD ➕" if action == "add" else ("DEDUCT ➖" if action == "deduct" else "SET 🔄")
        bot.send_message(msg.chat.id,
            f"✅ *User Mila!*\n\n🆔 `{uid}`\n"
            f"📛 {u.get('full_name','?')} @{u.get('username','N/A')}\n"
            f"💵 Balance: *₹{u.get('balance',0):.0f}*\n\n"
            f"*{at}* — Amount chunein 👇\n_(Min ₹100)_", reply_markup=mk)

    elif state.get("step") == "custom_amount":
        uid    = state.get("uid")
        action = state.get("action")
        try: amount = float(txt)
        except:
            bot.send_message(msg.chat.id, "❌ Sirf number bhejein! (e.g. `500`)\nDobara:"); return
        if action in ("add","deduct") and amount < 100:
            bot.send_message(msg.chat.id, "❌ *Minimum ₹100* chahiye!\nDobara bhejein:"); return
        _quick_bal_state.pop(OWNER_ID, None)
        _exec_quick_balance(msg.chat.id, uid, amount, action)

@bot.callback_query_handler(func=lambda c:
    c.data.startswith("qadd_qb_") or c.data.startswith("qded_qb_") or c.data.startswith("qset_qb_"))
def cb_qbal_amount(call):
    if call.from_user.id != OWNER_ID: return
    parts      = call.data.split("_")
    prefix     = parts[0]
    action     = "add" if prefix == "qadd" else ("deduct" if prefix == "qded" else "set")
    uid        = int(parts[2])
    amount_str = parts[3]
    if amount_str == "custom":
        _quick_bal_state[OWNER_ID] = {"step": "custom_amount", "action": action, "uid": uid}
        bot.answer_callback_query(call.id)
        u = users_col.find_one({"user_id": uid}) or {}
        bot.send_message(OWNER_ID,
            f"✏️ *Custom Amount*\n\n👤 `{uid}` — Balance: ₹{u.get('balance',0):.0f}\n\n"
            f"Amount bhejein {'(Min ₹100)' if action != 'set' else '(Exact)'}:\n/cancel")
        return
    amount = float(amount_str)
    bot.answer_callback_query(call.id, f"⏳ Processing ₹{amount:.0f}...")
    _quick_bal_state.pop(OWNER_ID, None)
    _exec_quick_balance(call.message.chat.id, uid, amount, action)

@bot.callback_query_handler(func=lambda c: c.data == "qbal_cancel")
def cb_qbal_cancel(call):
    if call.from_user.id != OWNER_ID: return
    _quick_bal_state.pop(OWNER_ID, None)
    bot.answer_callback_query(call.id, "✅ Cancel ho gaya")
    bot.send_message(OWNER_ID, "✅ Cancel ho gaya.", reply_markup=admin_menu())

def _exec_quick_balance(cid, uid, amount, action):
    u_before = users_col.find_one({"user_id": uid}) or {}
    bb       = u_before.get('balance', 0)

    if action == "add":
        add_balance(uid, amount)
        log_admin_action(OWNER_ID, uid, amount, "add", "quick_balance")
        u2 = users_col.find_one({"user_id": uid}) or {}
        bot.send_message(cid,
            f"✅ *Balance Add Done!*\n\n👤 `{uid}`\n📛 {u_before.get('full_name','?')} @{u_before.get('username','N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n💵 Pehle: ₹{bb:.0f}\n➕ Add: ₹{amount:.0f}\n💰 Naya: *₹{u2.get('balance',0):.0f}*")
        try: bot.send_message(uid,
            f"🎉 *₹{amount:.0f} Balance Add Hua!*\n💵 Pehle: ₹{bb:.0f}\n💰 Naya Balance: *₹{u2.get('balance',0):.0f}*\n\n📲 Buy Number dabayein 🛒")
        except: pass

    elif action == "deduct":
        add_balance(uid, -amount)
        log_admin_action(OWNER_ID, uid, amount, "deduct", "quick_balance")
        u2 = users_col.find_one({"user_id": uid}) or {}
        bot.send_message(cid,
            f"✅ *Deduct Done!*\n\n👤 `{uid}`\n📛 {u_before.get('full_name','?')} @{u_before.get('username','N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n💵 Pehle: ₹{bb:.0f}\n➖ Deduct: ₹{amount:.0f}\n💰 Naya: *₹{u2.get('balance',0):.0f}*")
        try: bot.send_message(uid,
            f"❕ ₹{amount:.0f} balance deduct hua.\nNaya Balance: ₹{u2.get('balance',0):.0f}")
        except: pass

    elif action == "set":
        users_col.update_one({"user_id": uid}, {"$set": {"balance": amount}})
        log_admin_action(OWNER_ID, uid, amount, "set", "quick_balance")
        bot.send_message(cid,
            f"✅ *Balance SET Done!*\n\n👤 `{uid}`\n📛 {u_before.get('full_name','?')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n💵 Pehle: ₹{bb:.0f}\n🔄 Set: ₹{amount:.0f}")
        try: bot.send_message(uid, f"✅ Balance update hua!\nNaya Balance: *₹{amount:.0f}*")
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  LIVE PRICE CHECKER (Admin)
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📊 Live Price Check" and m.from_user.id == OWNER_ID)
def ab_live_price_check(msg):
    mk = types.InlineKeyboardMarkup(row_width=2)
    for label, api in [
        ("📱 WhatsApp","whatsapp"),("✈️ Telegram","telegram"),
        ("📸 Instagram","instagram"),("📧 Gmail","google"),
        ("📘 Facebook","facebook"),("🎵 TikTok","tiktok"),
        ("🐦 Twitter/X","twitter"),("📷 Snapchat","snapchat"),
        ("🛒 Amazon","amazon"),("💼 LinkedIn","linkedin"),
    ]:
        mk.add(types.InlineKeyboardButton(label, callback_data=f"lpc_svc_{api}"))
    mk.add(types.InlineKeyboardButton("📊 Full Stock Report", callback_data="lpc_full"))
    bot.send_message(msg.chat.id,
        "📊 *Live Price Checker — DgOTP*\n\n"
        "Service chunein:\n"
        "🔷 DgOTP raw INR price dikhega\n"
        "+10% margin ke baad user price\n"
        "📦 Live stock bhi dikhega", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lpc_svc_"))
def cb_lpc_service(call):
    if call.from_user.id != OWNER_ID: return
    api = call.data[8:]
    bot.answer_callback_query(call.id, "⏳ Loading...")
    done = set(); mk = types.InlineKeyboardMarkup(row_width=2)
    for _, items in SERVICES.items():
        for _, info in items.items():
            if info['api'] == api and info['cc'] not in done:
                done.add(info['cc'])
                mk.add(types.InlineKeyboardButton(
                    f"{info['flag']} {info['country']}", callback_data=f"lpc_check_{api}_{info['cc']}"))
    mk.add(types.InlineKeyboardButton("🔄 Sabka Price", callback_data=f"lpc_all_{api}"))
    mk.add(types.InlineKeyboardButton("🔙 Back",        callback_data="lpc_back"))
    bot.send_message(call.message.chat.id,
        f"📊 *{api.title()}* — Country chunein:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lpc_check_"))
def cb_lpc_check(call):
    if call.from_user.id != OWNER_ID: return
    rest   = call.data[10:]
    api    = rest.split("_")[0]
    cc     = "_".join(rest.split("_")[1:])
    bot.answer_callback_query(call.id, "⏳ DgOTP live price fetch ho rahi hai...")

    _pc.pop(f"{cc}|{api}", None)

    # DgOTP live raw price
    pdg_raw = 0; sdg = 0
    try:
        co_dg = DGOTP_CC.get(cc); sv_dg = DGOTP_SVC.get(api)
        if co_dg and sv_dg:
            rd = requests.get(DGOTP_BASE,
                params={"api_key": DGOTP_KEY, "action": "getPrices",
                        "service": sv_dg, "country": co_dg}, timeout=10).json()
            # Try multiple formats
            svc_data = rd.get(sv_dg, rd)
            pd_data  = svc_data.get(str(co_dg)) or svc_data.get(int(co_dg), {})
            if not pd_data:
                for k, v in svc_data.items():
                    if str(k) == str(co_dg): pd_data = v; break
            pdg_raw = float(pd_data.get("cost") or pd_data.get("retail_price") or pd_data.get("price") or 0)
            sdg     = int(pd_data.get("count", 0))
    except Exception as e:
        logger.warning(f"LPC DgOTP: {e}")

    flag_info = ""
    for _, items in SERVICES.items():
        for _, info in items.items():
            if info['cc'] == cc and info['api'] == api:
                flag_info = f"{info['flag']} {info['country']}"; break
        if flag_info: break

    t  = f"📊 *{flag_info} {api.title()}*\n"
    t += f"━━━━━━━━━━━━━━━━━━━━\n"
    t += f"🔷 *DgOTP.in* — Live Price\n\n"

    if pdg_raw > 0 and sdg > 0:
        dg_sell = math.ceil(pdg_raw * DGOTP_MARGIN)
        profit  = round(dg_sell - pdg_raw, 2)
        t += f"💰 Raw Cost: *₹{pdg_raw:.2f}*\n"
        t += f"📈 Margin: +{int((DGOTP_MARGIN-1)*100)}%\n"
        t += f"━━━━━━━━━━━━━━━━━━━━\n"
        t += f"🏷️ User Price: *₹{dg_sell}*\n"
        t += f"💵 Profit per sim: *₹{profit:.2f}*\n"
        t += f"📦 Stock: *{sdg}*\n"
        ic = "🟢" if sdg > 20 else ("🟡" if sdg > 5 else "🔴")
        t += f"Status: {ic}\n"
    elif pdg_raw > 0 and sdg == 0:
        t += f"💰 Price: ₹{pdg_raw:.2f} (sell ₹{math.ceil(pdg_raw*DGOTP_MARGIN)})\n"
        t += "❌ *Stock khatam — No Numbers*\n"
    else:
        dp, ds = _get_default_price(cc, api)
        t += f"❌ *DgOTP se live price nahi mila*\n\n"
        if dp:
            t += f"📋 Default fallback: ₹{dp} (stock: {ds})\n"
        t += f"\n_DgOTP API balance check karein_"
    t += f"\n\n🕐 {datetime.utcnow().strftime('%H:%M')} UTC"

    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=call.data))
    mk.add(types.InlineKeyboardButton("🔙 Back",    callback_data=f"lpc_svc_{api}"))
    bot.send_message(call.message.chat.id, t, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lpc_all_"))
def cb_lpc_all(call):
    if call.from_user.id != OWNER_ID: return
    api = call.data[8:]
    bot.answer_callback_query(call.id, "⏳ DgOTP prices fetch ho rahi hain...")
    done = set(); results = []
    for _, items in SERVICES.items():
        for _, info in items.items():
            if info['api'] == api and info['cc'] not in done:
                done.add(info['cc'])
                cc = info['cc']
                _pc.pop(f"{cc}|{api}", None)
                pdg, sdg = _dgotp_price(cc, api)
                dp, _    = _get_default_price(cc, api)
                if pdg and sdg > 0:
                    ic = "🟢" if sdg > 20 else ("🟡" if sdg > LOW_STOCK else "🔴")
                    results.append(f"{ic}{info['flag']} {info['country']}: *₹{pdg}* 📦{sdg}")
                elif dp:
                    results.append(f"📋{info['flag']} {info['country']}: ₹{dp} (default)")
    t  = f"📊 *{api.title()} — All Countries (DgOTP)*\n"
    t += f"Margin: +{int((DGOTP_MARGIN-1)*100)}% | {datetime.utcnow().strftime('%H:%M')} UTC\n"
    t += "━━━━━━━━━━━━━━━━━━━━\n\n"
    t += "\n".join(results) if results else "❌ Koi live price nahi"
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=call.data))
    mk.add(types.InlineKeyboardButton("🔙 Back",    callback_data=f"lpc_svc_{api}"))
    bot.send_message(call.message.chat.id, t, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "lpc_back")
def cb_lpc_back(call):
    if call.from_user.id != OWNER_ID: return
    bot.answer_callback_query(call.id)
    ab_live_price_check(call.message)

@bot.callback_query_handler(func=lambda c: c.data == "lpc_full")
def cb_lpc_full(call):
    if call.from_user.id != OWNER_ID: return
    bot.answer_callback_query(call.id, "⏳ Full report ban rahi hai...")
    _stock_report(call.message.chat.id)

# ══════════════════════════════════════════════════════════════════════════════
#  PLATFORM ADD / MANAGE
# ══════════════════════════════════════════════════════════════════════════════
_add_plat_state = {}

@bot.message_handler(commands=['add_platform'])
@owner_only
def cmd_add_platform(msg):
    _add_plat_state[OWNER_ID] = {"step": 1}
    bot.send_message(msg.chat.id, "➕ *Platform Add*\n\n*Step 1/3:* Naam?\n/cancel")

@bot.message_handler(commands=['list_platforms'])
@owner_only
def cmd_list_platforms(msg):
    platforms = list(platforms_col.find())
    if not platforms: bot.send_message(msg.chat.id, "📭 Koi platform nahi."); return
    t = "📋 *Earning Platforms*\n\n"
    for i, p in enumerate(platforms, 1):
        t += f"{i}. *{p['name']}*\n🔗 {p['link']}\n🎥 {p.get('video','N/A')}\n🗑 `/del_plat_{str(p['_id'])}`\n\n"
    bot.send_message(msg.chat.id, t)

@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and (m.text or "").startswith('/del_plat_'))
def cmd_del_platform(msg):
    from bson import ObjectId
    try:
        platforms_col.delete_one({"_id": ObjectId(msg.text.replace('/del_plat_','').strip())})
        bot.reply_to(msg, "✅ Platform delete ho gaya.")
    except Exception as e: bot.reply_to(msg, f"❌ Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN COMMANDS
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(commands=['add'])
@owner_only
def cmd_add(msg):
    try:
        parts  = msg.text.split()
        uid    = int(parts[1]); amount = float(parts[2])
        method = parts[3].upper() if len(parts) > 3 else "MANUAL"
        _do_approve(uid, amount, method)
        u = users_col.find_one({"user_id": uid}) or {}
        bot.reply_to(msg, f"✅ ₹{amount:.0f} added to `{uid}` ({method})\nNew balance: ₹{u.get('balance',0):.0f}")
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}\nFormat: `/add USER_ID AMOUNT`")

@bot.message_handler(commands=['deduct'])
@owner_only
def cmd_deduct(msg):
    try:
        _, uid_s, amt_s = msg.text.split()
        uid    = int(uid_s); amount = float(amt_s)
        u_b    = users_col.find_one({"user_id": uid}) or {}
        add_balance(uid, -amount)
        log_admin_action(OWNER_ID, uid, amount, "deduct", "cmd")
        u_a = users_col.find_one({"user_id": uid}) or {}
        bot.reply_to(msg, f"✅ ₹{amount:.0f} deducted from `{uid}`\n₹{u_b.get('balance',0):.0f} → ₹{u_a.get('balance',0):.0f}")
        try: bot.send_message(uid, f"❕ ₹{amount:.0f} balance adjust hua. Naya Balance: ₹{u_a.get('balance',0):.0f}")
        except: pass
    except: bot.reply_to(msg, "❌ Format: `/deduct USER_ID AMOUNT`")

@bot.message_handler(commands=['setbal'])
@owner_only
def cmd_setbal(msg):
    try:
        parts  = msg.text.split()
        uid    = int(parts[1]); amount = float(parts[2])
        u_b    = users_col.find_one({"user_id": uid}) or {}
        users_col.update_one({"user_id": uid}, {"$set": {"balance": amount}})
        log_admin_action(OWNER_ID, uid, amount, "set", "cmd")
        bot.reply_to(msg, f"✅ Balance SET!\n`{uid}`: ₹{u_b.get('balance',0):.0f} → ₹{amount:.0f}")
    except: bot.reply_to(msg, "❌ Format: `/setbal USER_ID AMOUNT`")

@bot.message_handler(commands=['reject'])
@owner_only
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
@owner_only
def cmd_ban(msg):
    try:
        uid = int(msg.text.split()[1])
        users_col.update_one({"user_id": uid}, {"$set": {"banned": True}})
        try: bot.send_message(uid, f"🚫 Ban. Appeal: {SUPPORT_BOT}")
        except: pass
        bot.reply_to(msg, f"🚫 `{uid}` banned.")
    except: bot.reply_to(msg, "❌ `/ban USER_ID`")

@bot.message_handler(commands=['unban'])
@owner_only
def cmd_unban(msg):
    try:
        uid = int(msg.text.split()[1])
        users_col.update_one({"user_id": uid}, {"$set": {"banned": False}})
        try: bot.send_message(uid, "✅ Ban hata diya.")
        except: pass
        bot.reply_to(msg, f"✅ `{uid}` unbanned.")
    except: bot.reply_to(msg, "❌ `/unban USER_ID`")

@bot.message_handler(commands=['broadcast'])
@owner_only
def cmd_bc(msg):
    t = msg.text.replace('/broadcast','',1).strip()
    if not t: bot.reply_to(msg, "❌ `/broadcast MSG`"); return
    _do_broadcast(msg.chat.id, t)

@bot.message_handler(commands=['stats'])
@owner_only
def cmd_stats(msg): _send_stats(msg.chat.id)

@bot.message_handler(commands=['userinfo'])
@owner_only
def cmd_uinfo(msg):
    try:
        arg = msg.text.split()[1]
        u   = find_user_by_username(arg) if arg.startswith('@') else users_col.find_one({"user_id": int(arg)})
        if not u: bot.reply_to(msg, "❌ User nahi mila."); return
        _show_user_for_adjust(msg.chat.id, u)
    except: bot.reply_to(msg, "❌ `/userinfo USER_ID` ya `/userinfo @username`")

@bot.message_handler(commands=['balance'])
@owner_only
def cmd_check_bal(msg):
    try:
        arg = msg.text.split()[1]
        u   = find_user_by_username(arg) if arg.startswith('@') else users_col.find_one({"user_id": int(arg)})
        if not u: bot.reply_to(msg, "❌ User nahi mila."); return
        bot.reply_to(msg,
            f"👤 `{u['user_id']}` @{u.get('username','N/A')}\n"
            f"💵 Balance: ₹{u.get('balance',0):.0f}\n🛒 Orders: {u.get('orders',0)}")
    except: bot.reply_to(msg, "❌ `/balance USER_ID` ya `/balance @username`")

@bot.message_handler(commands=['cancel'])
@owner_only
def cmd_cancel(msg):
    for s in [_add_plat_state, _custom_add_state, _ch_add_state,
              _settings_state, _bal_adjust_state, _user_search_state, _quick_bal_state]:
        s.pop(OWNER_ID, None)
    bot.reply_to(msg, "✅ Cancel ho gaya.")

@bot.message_handler(commands=['skip'])
@owner_only
def cmd_skip(msg):
    state = _add_plat_state.get(OWNER_ID, {})
    if state.get("step") == 3:
        sd = _add_plat_state.pop(OWNER_ID, {})
        platforms_col.insert_one({
            "name": sd["name"], "link": sd["link"],
            "video": None, "added_at": datetime.utcnow()})
        bot.send_message(msg.chat.id,
            f"✅ *Platform Add Ho Gaya!* (No video)\n\n"
            f"📛 {sd['name']}\n🔗 {sd['link']}\n\n"
            f"👥 Refer & Earn mein dikhega!")
    else:
        bot.reply_to(msg, "❌ Skip yahan applicable nahi.")

def _apply_balance_action(cid, uid, amount, action, note="admin"):
    """Common DRY helper: add / deduct / set with log + user notify."""
    u_b = users_col.find_one({"user_id": uid}) or {}
    bb  = u_b.get('balance', 0)
    if action == "add":
        add_balance(uid, amount)
        log_admin_action(OWNER_ID, uid, amount, "add", note)
        u2 = users_col.find_one({"user_id": uid}) or {}
        nb = u2.get('balance', 0)
        bot.send_message(cid,
            f"✅ *Add Done!*\n`{uid}`: ₹{bb:.0f} → *₹{nb:.0f}* (+₹{amount:.0f})")
        try: bot.send_message(uid,
            f"✅ *₹{amount:.0f} Balance Add Hua!*\nNaya Balance: *₹{nb:.0f}*\n\n📲 Buy Number dabayein!")
        except: pass
    elif action == "deduct":
        add_balance(uid, -amount)
        log_admin_action(OWNER_ID, uid, amount, "deduct", note)
        u2 = users_col.find_one({"user_id": uid}) or {}
        nb = u2.get('balance', 0)
        bot.send_message(cid,
            f"✅ *Deduct Done!*\n`{uid}`: ₹{bb:.0f} → *₹{nb:.0f}* (-₹{amount:.0f})")
        try: bot.send_message(uid,
            f"❕ ₹{amount:.0f} balance deduct hua.\nNaya Balance: ₹{nb:.0f}")
        except: pass
    elif action == "set":
        users_col.update_one({"user_id": uid}, {"$set": {"balance": amount}})
        log_admin_action(OWNER_ID, uid, amount, "set", note)
        bot.send_message(cid,
            f"✅ *Set Done!*\n`{uid}`: ₹{bb:.0f} → *₹{amount:.0f}*")
        try: bot.send_message(uid,
            f"✅ Balance update hua!\nNaya Balance: *₹{amount:.0f}*")
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  UNIFIED ADMIN TEXT HANDLER (multi-step flows)
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: (
    m.from_user.id == OWNER_ID
    and m.text not in ADMIN_BTNS
    and not (m.text or "").startswith('/')
    and OWNER_ID not in _quick_bal_state
    and (
        (OWNER_ID in _add_plat_state and _add_plat_state.get(OWNER_ID, {}).get("step", 0) > 0)
        or (OWNER_ID in _ch_add_state and _ch_add_state.get(OWNER_ID, {}).get("step", 0) > 0)
        or OWNER_ID in _custom_add_state
        or OWNER_ID in _settings_state
        or OWNER_ID in _bal_adjust_state
        or OWNER_ID in _user_search_state
    )
))
def handle_admin_text_states(msg):
    txt = (msg.text or "").strip()

    # ── PRIORITY 1: Platform Add (naam → link → video) ──────────────────────
    # MUST be checked first — naam is plain text, clashes with user search
    if OWNER_ID in _add_plat_state and _add_plat_state.get(OWNER_ID, {}).get("step", 0) > 0:
        state = _add_plat_state[OWNER_ID]
        step  = state.get("step", 0)
        if step == 1:
            state["name"] = txt
            state["step"] = 2
            bot.send_message(msg.chat.id,
                f"✅ Naam: *{txt}*\n\n"
                f"*Step 2/3:* Registration link bhejein:\n"
                f"_Example: https://easebux.com/ref/123_")
        elif step == 2:
            if not txt.startswith("http"):
                bot.send_message(msg.chat.id,
                    "❌ Valid URL chahiye (https:// se shuru ho)\nDobara bhejein:"); return
            state["link"] = txt
            state["step"] = 3
            bot.send_message(msg.chat.id,
                f"✅ Link: {txt}\n\n"
                f"*Step 3/3:* Video tutorial link? (optional)\n"
                f"_YouTube ya koi bhi link — `/skip` to skip_")
        elif step == 3:
            video = txt if txt.startswith("http") else None
            if not video:
                bot.send_message(msg.chat.id,
                    "❌ Valid video URL chahiye (https://) ya `/skip` likho"); return
            sd = _add_plat_state.pop(OWNER_ID, {})
            platforms_col.insert_one({
                "name": sd["name"], "link": sd["link"],
                "video": video, "added_at": datetime.utcnow()})
            bot.send_message(msg.chat.id,
                f"✅ *Platform Add Ho Gaya!*\n\n"
                f"📛 {sd['name']}\n🔗 {sd['link']}\n🎥 {video}\n\n"
                f"👥 Refer & Earn mein dikhega!")
        return

    # ── PRIORITY 2: Channel Add ──────────────────────────────────────────────
    if OWNER_ID in _ch_add_state and _ch_add_state.get(OWNER_ID, {}).get("step", 0) > 0:
        handle_ch_add_steps(msg); return

    # ── PRIORITY 3: Settings ─────────────────────────────────────────────────
    if OWNER_ID in _settings_state:
        setting = _settings_state.pop(OWNER_ID)
        if setting == "margin":
            try:
                val = float(txt)
                if not (10 <= val <= 200):
                    bot.send_message(msg.chat.id, "❌ Range: 10-200%")
                    _settings_state[OWNER_ID] = "margin"; return
                set_setting("margin", 1 + val/100); _pc.clear()
                bot.send_message(msg.chat.id,
                    f"✅ *Margin: {val}%* set ho gaya!\n🗑 Cache cleared!")
            except:
                bot.send_message(msg.chat.id, "❌ Sirf number bhejein! (e.g. `40`)")
                _settings_state[OWNER_ID] = "margin"
        elif setting == "usdt_rate":
            try:
                val = float(txt)
                if not (50 <= val <= 200):
                    bot.send_message(msg.chat.id, "❌ Range: 50-200")
                    _settings_state[OWNER_ID] = "usdt_rate"; return
                set_setting("usdt_rate", val); _pc.clear()
                bot.send_message(msg.chat.id,
                    f"✅ *USDT Rate: ₹{val}* set ho gaya!\n🗑 Cache cleared!")
            except:
                bot.send_message(msg.chat.id, "❌ Sirf number bhejein! (e.g. `87.5`)")
                _settings_state[OWNER_ID] = "usdt_rate"
        return

    # ── PRIORITY 4: Custom Deposit Add ──────────────────────────────────────
    if OWNER_ID in _custom_add_state:
        state = _custom_add_state.pop(OWNER_ID)
        uid   = state["uid"] if isinstance(state, dict) else state
        try:
            amount = float(txt.split()[0])
            method = "UPI" if "upi" in txt.lower() else "USDT"
            _do_approve(uid, amount, method)
            u = users_col.find_one({"user_id": uid}) or {}
            bot.send_message(msg.chat.id,
                f"✅ ₹{amount:.0f} added to `{uid}`\nNew balance: ₹{u.get('balance',0):.0f}")
        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Error: {e}\nFormat: `500` ya `500 upi`")
        return

    # ── PRIORITY 5: Balance Adjust ───────────────────────────────────────────
    if OWNER_ID in _bal_adjust_state:
        state = _bal_adjust_state[OWNER_ID]
        if state.get("step") == "uid":
            u = find_user_by_username(txt) if txt.startswith('@') else \
                users_col.find_one({"user_id": int(txt)}) if txt.isdigit() else None
            if not u:
                bot.send_message(msg.chat.id,
                    f"❌ User `{txt}` nahi mila.\nSahi ID ya @username bhejein:"); return
            _bal_adjust_state.pop(OWNER_ID, None)
            _show_user_for_adjust(msg.chat.id, u)
        elif state.get("step") == "amount":
            uid = state["uid"]; action = state["action"]
            try: amount = float(txt)
            except:
                bot.send_message(msg.chat.id, "❌ Sirf number bhejein!"); return
            if action in ("add","deduct") and amount < 100:
                bot.send_message(msg.chat.id, "❌ Minimum ₹100!"); return
            _bal_adjust_state.pop(OWNER_ID, None)
            _apply_balance_action(msg.chat.id, uid, amount, action, "admin_adj")
        return

    # ── PRIORITY 6: User Search ──────────────────────────────────────────────
    if OWNER_ID in _user_search_state:
        _user_search_state.pop(OWNER_ID, None)
        u = find_user_by_username(txt) if txt.startswith('@') else \
            users_col.find_one({"user_id": int(txt)}) if txt.isdigit() else None
        if not u:
            bot.send_message(msg.chat.id,
                f"❌ User `{txt}` nahi mila.\n🔍 User Search fir se try karein."); return
        _show_user_for_adjust(msg.chat.id, u)
        return

# ══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _send_stats(cid):
    tu = users_col.count_documents({})
    bu = users_col.count_documents({"banned": True})
    to = orders_col.count_documents({})
    do = orders_col.count_documents({"status": "done"})
    co = orders_col.count_documents({"status": "cancelled"})
    pd = deposits_col.count_documents({"status": "pending"})

    # DgOTP revenue only
    agg = list(orders_col.aggregate([
        {"$match": {"status": "done"}},
        {"$group": {"_id": "$source", "rev": {"$sum": "$amount"}, "cnt": {"$sum": 1}}}
    ]))
    rev_dg = cnt_dg = 0
    for x in agg:
        if x['_id'] == 'dgotp':
            rev_dg = x['rev']; cnt_dg = x['cnt']

    total_rev  = rev_dg
    profit_est = round(total_rev * (1 - 1 / DGOTP_MARGIN), 0)

    total_add = sum(l.get('amount', 0) for l in admin_log_col.find({"type": "add"}))
    total_ded = sum(l.get('amount', 0) for l in admin_log_col.find({"type": "deduct"}))

    # DgOTP live balance
    dg_bal = "?"
    try:
        rb = requests.get(DGOTP_BASE,
            params={"api_key": DGOTP_KEY, "action": "getBalance"}, timeout=8).text.strip()
        if rb.startswith("ACCESS_BALANCE:"):
            dg_bal = f"₹{float(rb.split(':')[1]):.2f}"
        else:
            dg_bal = rb[:20]
    except: dg_bal = "N/A"

    bot.send_message(cid,
        f"📊 *Bot Statistics*\n\n"
        f"👥 Users: `{tu}` (🚫{bu})\n"
        f"🛒 Orders: `{to}` ✅{do} ❌{co}\n"
        f"📥 Pending Dep: `{pd}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔷 *DgOTP.in*\n"
        f"   💰 Revenue: `₹{rev_dg:.0f}` ({cnt_dg} orders)\n"
        f"   📈 Est. Profit (+{int((DGOTP_MARGIN-1)*100)}%): `₹{profit_est:.0f}`\n"
        f"   💳 Live Balance: `{dg_bal}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"➕ Admin Added: `₹{total_add:.0f}`\n"
        f"➖ Admin Deducted: `₹{total_ded:.0f}`")

def _do_broadcast(cid, text):
    all_u = list(users_col.find({"banned":{"$ne":True}}))
    pm = bot.send_message(cid, f"📢 {len(all_u)} users ko bhej rahe hain...")
    s = f = 0
    for u in all_u:
        try: bot.send_message(u['user_id'], f"📢 *Announcement*\n\n{text}"); s+=1
        except: f+=1
        time.sleep(0.05)
    bot.edit_message_text(f"✅ Sent:`{s}` Failed:`{f}`", cid, pm.message_id)

def _stock_report(cid):
    checks = [
        ("WhatsApp","russia","whatsapp","🇷🇺"), ("WhatsApp","india","whatsapp","🇮🇳"),
        ("WhatsApp","usa","whatsapp","🇺🇸"),    ("WhatsApp","uk","england","🇬🇧"),
        ("WhatsApp","ukraine","ukraine","🇺🇦"),  ("WhatsApp","indonesia","indonesia","🇮🇩"),
        ("WhatsApp","kenya","whatsapp","🇰🇪"),   ("WhatsApp","nigeria","whatsapp","🇳🇬"),
        ("Telegram","russia","telegram","🇷🇺"),  ("Telegram","india","telegram","🇮🇳"),
        ("Instagram","russia","instagram","🇷🇺"),("Instagram","india","instagram","🇮🇳"),
        ("Gmail","russia","google","🇷🇺"),       ("Gmail","india","google","🇮🇳"),
        ("Facebook","russia","facebook","🇷🇺"),  ("Facebook","india","facebook","🇮🇳"),
    ]
    t = f"📈 *Live Stock Report — DgOTP.in*\n"
    t += f"Margin: +{int((DGOTP_MARGIN-1)*100)}% | {datetime.utcnow().strftime('%H:%M')} UTC\n\n"
    for svc_name, cc_name, api, flag in checks:
        cc = cc_name
        _pc.pop(f"{cc}|{api}", None)
        pdg, sdg = _dgotp_price(cc, api)
        dp, ds   = _get_default_price(cc, api)
        if pdg and sdg > 0:
            ic = "🔴" if sdg <= LOW_STOCK else ("🟡" if sdg <= 20 else "🟢")
            t += f"{ic}{flag} {cc.title()} {svc_name}: ₹{pdg} | 📦{sdg}\n"
        elif dp:
            t += f"📋{flag} {cc.title()} {svc_name}: No live | Fallback ₹{dp}\n"
        else:
            t += f"⚫{flag} {cc.title()} {svc_name}: No data\n"
    bot.send_message(cid, t)

def _stock_monitor():
    """Background: low stock alert every 30 min — DgOTP only"""
    while True:
        time.sleep(1800)
        try:
            lows = []
            for svc_name, cc, api, flag in [
                ("WhatsApp","russia","whatsapp","🇷🇺"),
                ("WhatsApp","india","whatsapp","🇮🇳"),
                ("WhatsApp","indonesia","whatsapp","🇮🇩"),
                ("Telegram","russia","telegram","🇷🇺"),
                ("Telegram","india","telegram","🇮🇳"),
            ]:
                _pc.pop(f"{cc}|{api}", None)
                pdg, sdg = _dgotp_price(cc, api)
                if sdg > 0 and sdg <= LOW_STOCK:
                    lows.append(f"{flag}{cc.title()} {svc_name}: {sdg} left!")
            if lows:
                # Also get current balance
                try:
                    rb = requests.get(DGOTP_BASE,
                        params={"api_key": DGOTP_KEY, "action": "getBalance"},
                        timeout=8).text.strip()
                    bal_txt = rb.replace("ACCESS_BALANCE:", "₹") if rb.startswith("ACCESS_BALANCE:") else rb
                except: bal_txt = "Unknown"
                bot.send_message(OWNER_ID,
                    "⚠️ *LOW STOCK ALERT!*\n\n" + "\n".join(lows) +
                    f"\n\n💰 DgOTP Balance: {bal_txt}\n"
                    f"🔗 https://dgotp.in")
        except Exception as e:
            logger.error(f"Stock monitor: {e}")

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
    logger.info("👑 OtpKing Pro v8 — DgOTP Only — Starting...")
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
