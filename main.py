"""
ANOKHA OTP STORE — FIXED & FINAL
Fix: 409 Conflict resolved, single instance, webhook cleared
"""
import os, logging, requests, time, math, sys
from pymongo import MongoClient
from telebot import types
import telebot
from dotenv import load_dotenv
from threading import Thread
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN          = os.getenv('BOT_TOKEN')
MONGO_URI          = os.getenv('MONGO_URI') or os.getenv('MONGO_URL')  # both names supported
SIM_API_KEY        = os.getenv('SIM_API_KEY')
OWNER_ID           = int(os.getenv('OWNER_ID'))
SUPPORT_BOT        = os.getenv('SUPPORT_BOT', '@YourHelpBot')
CHANNEL_ID         = os.getenv('CHANNEL_ID', '@YourChannel')
CHANNEL_LINK       = os.getenv('CHANNEL_LINK', 'https://t.me/YourChannel')
GROUP_ID           = os.getenv('GROUP_ID', '@YourGroup')
GROUP_LINK         = os.getenv('GROUP_LINK', 'https://t.me/YourGroup')
PROOF_CHANNEL_ID   = os.getenv('PROOF_CHANNEL_ID', '@YourProofChannel')
PROOF_CHANNEL_LINK = os.getenv('PROOF_CHANNEL_LINK', 'https://t.me/YourProofChannel')
BINANCE_ADDRESS    = os.getenv('BINANCE_ADDRESS', 'YOUR_USDT_TRC20_ADDRESS')

# ── 409 FIX: Delete webhook + drop pending updates before polling ─────────────
def clear_webhook_and_updates():
    """Call this ONCE at startup to kill any old session"""
    try:
        # Step 1: delete webhook
        r1 = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10)
        logger.info(f"deleteWebhook: {r1.json()}")
        time.sleep(2)
        # Step 2: getUpdates with offset=-1 to clear queue
        r2 = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1&timeout=1",
            timeout=10)
        logger.info(f"clearUpdates: ok")
        time.sleep(1)
    except Exception as e:
        logger.error(f"Webhook clear failed: {e}")

# Run fix immediately
clear_webhook_and_updates()

# ── Bot init (threaded=False avoids double-thread conflict) ────────────────────
bot   = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown", threaded=False)
mongo = MongoClient(MONGO_URI)
db    = mongo['anokha_otp_db']
users_col    = db['users']
orders_col   = db['orders']
deposits_col = db['deposits']

PROFIT_PCT      = 0.60
LOW_STOCK_LIMIT = 5
USD_TO_INR      = 85
SIM_HEADERS     = {'Authorization': f'Bearer {SIM_API_KEY}', 'Accept': 'application/json'}
USDT_AMOUNTS    = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,18,20,25,30,35,40,45,50]

BAD_WORDS = [
    "madarchod","mc","bc","bhenchod","gandu","chutiya","randi","harami",
    "bhosdike","loda","lauda","chut","bsdk","fuck","bitch","asshole",
    "bastard","shit","dick","cunt","whore","sala","maderchod"
]
def has_bad(text): return any(w in (text or "").lower() for w in BAD_WORDS)

# ── Services ──────────────────────────────────────────────────────────────────
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

# ── Price Cache ───────────────────────────────────────────────────────────────
_pcache = {}
def live_ps(cc, api):
    k = f"{cc}|{api}"
    c = _pcache.get(k)
    if c and time.time()-c[2] < 1800: return c[0], c[1]
    try:
        r  = requests.get(f"https://5sim.net/v1/guest/prices?country={cc}&product={api}", timeout=8).json()
        pd = r.get(cc,{}).get(api,{})
        if not pd: return None,0
        best=None; tot=0
        for op,info in pd.items():
            cnt=info.get('count',0); tot+=cnt
            if cnt>0:
                cost=info.get('cost',0)
                if best is None or cost<best: best=cost
        if best:
            inr=round(best*USD_TO_INR,2); _pcache[k]=(inr,tot,time.time()); return inr,tot
    except Exception as e: logger.warning(f"price {cc}/{api}: {e}")
    return None,0

def sellp(buy): return int(math.ceil(buy*(1+PROFIT_PCT)/5)*5)
def find_svc(key):
    for cat,items in SERVICES.items():
        if key in items: return items[key],cat
    return None,None

# ── DB ─────────────────────────────────────────────────────────────────────────
def get_user(uid, uname=None, fname=None):
    u = users_col.find_one({"user_id":uid})
    if not u:
        u = {"user_id":uid,"username":uname or "","full_name":fname or "",
             "balance":0,"total_spent":0,"orders":0,"referrals":0,
             "referral_by":None,"banned":False,"is_reseller":False,
             "total_earned":0,"joined_at":datetime.utcnow()}
        users_col.insert_one(u)
    return u

def is_banned(uid):
    u=users_col.find_one({"user_id":uid}); return bool(u and u.get("banned"))

def log_order(uid,cat,svc,num,oid,bp,sell):
    orders_col.insert_one({
        "user_id":uid,"category":cat,
        "service":f"{svc['flag']} {svc['country']} {cat}",
        "api":svc['api'],"cc":svc['cc'],
        "number":num,"order_id":oid,
        "buy_price":bp,"amount":sell,"profit":sell-bp,
        "status":"pending","otp":None,"created_at":datetime.utcnow()})

# ── Force Join ────────────────────────────────────────────────────────────────
def is_member(uid):
    try:
        ok=['member','administrator','creator']
        return (bot.get_chat_member(CHANNEL_ID,uid).status in ok and
                bot.get_chat_member(GROUP_ID,uid).status in ok)
    except: return True

def join_mk():
    m=types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("📢 Channel Join करें",url=CHANNEL_LINK),
          types.InlineKeyboardButton("👥 Group Join करें",url=GROUP_LINK),
          types.InlineKeyboardButton("✅ Join किया — Verify करें",callback_data="vfy"))
    return m

# ── Keyboards ─────────────────────────────────────────────────────────────────
def mk_main(uid):
    m=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    m.add("📱 WhatsApp","✈️ Telegram","📸 Instagram","📧 Gmail",
          "📘 Facebook","🎵 TikTok","🐦 Twitter/X","📷 Snapchat",
          "🛒 Amazon","💼 LinkedIn",
          "💰 Wallet","📋 My Orders",
          "💸 Earn Money","👥 Refer & Earn",
          "❓ Help","📊 Proof","📞 Support")
    if uid==OWNER_ID: m.add("🔧 Admin Panel")
    return m

def mk_admin():
    m=types.ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    m.add("📊 Stats","👥 Total Users",
          "📋 Pending Deposits","💹 5sim Balance",
          "📢 Broadcast","🏆 Top Buyers",
          "📦 Recent Orders","📈 Stock Check",
          "💾 Export Users","🔙 Back")
    return m

# ── Decorators ────────────────────────────────────────────────────────────────
def ban_check(fn):
    def w(msg):
        if is_banned(msg.from_user.id):
            bot.send_message(msg.chat.id,"🚫 *आप बैन हैं!*\nHelp: "+SUPPORT_BOT); return
        fn(msg)
    return w

def join_check(fn):
    def w(msg):
        uid=msg.from_user.id
        if uid==OWNER_ID: fn(msg); return
        if not is_member(uid):
            bot.send_message(msg.chat.id,
                "⚠️ *Bot use करने के लिए Join करें:*\n\n"
                "1️⃣ Channel join करें\n2️⃣ Group join करें\n3️⃣ Verify दबाएं ✅",
                reply_markup=join_mk()); return
        fn(msg)
    return w

def gaali_check(fn):
    def w(msg):
        if msg.from_user.id==OWNER_ID: fn(msg); return
        if has_bad(msg.text or ""):
            uid=msg.from_user.id
            users_col.update_one({"user_id":uid},{"$set":{"banned":True}})
            bot.send_message(uid,"🚫 *Block हो गए!*\nGaaliyan dene se ban hota hai.\nAppeal: "+SUPPORT_BOT)
            try: bot.send_message(OWNER_ID,
                f"⚠️ *Auto-Ban (Gaali)*\n👤 {msg.from_user.first_name} @{msg.from_user.username or 'N/A'}\n🆔 `{uid}`\n💬 `{msg.text}`")
            except: pass
            return
        fn(msg)
    return w

# ══════════════════════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid=msg.from_user.id; args=msg.text.split()
    u=get_user(uid,msg.from_user.username,msg.from_user.first_name)
    if len(args)>1 and not u.get("referral_by"):
        ref=args[1]
        if ref.isdigit() and int(ref)!=uid:
            rid=int(ref)
            users_col.update_one({"user_id":uid},{"$set":{"referral_by":rid}})
            users_col.update_one({"user_id":rid},{"$inc":{"balance":10,"referrals":1}})
            try: bot.send_message(rid,"🎉 Referral! *+₹10* wallet mein! 💰")
            except: pass
    if uid!=OWNER_ID and not is_member(uid):
        bot.send_message(uid,"👋 *Anokha OTP Store* mein swagat!\n\n🔒 Pehle Join karein:",
            reply_markup=join_mk()); return
    _greet(uid,msg.from_user.first_name or "Dost")

def _greet(uid,name):
    bot.send_message(uid,
        f"🔥 *OtpKing Store*\nNamaste *{name}* ji! 🙏\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ 10 Services | 50+ Countries\n"
        "⚡ Instant OTP Delivery\n"
        "🔄 Auto Refund if OTP fails\n"
        "💰 USDT Deposit (Binance)\n"
        "📊 Live Stock & Prices\n"
        "💸 Earn by Reselling\n"
        "👥 Refer karo, ₹10 pao\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Service chunein:",reply_markup=mk_main(uid))

@bot.callback_query_handler(func=lambda c:c.data=="vfy")
def cb_vfy(call):
    if is_member(call.from_user.id):
        bot.answer_callback_query(call.id,"✅ Verified! Welcome!")
        _greet(call.from_user.id,call.from_user.first_name or "Dost")
    else:
        bot.answer_callback_query(call.id,"❌ Pehle dono join karein!",show_alert=True)

# ══════════════════════════════════════════════════════════════════════════════
#  WALLET
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m:m.text=="💰 Wallet")
@ban_check
@join_check
def wallet(msg):
    u=get_user(msg.from_user.id)
    m=types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("💎 USDT Deposit (Binance)",callback_data="d_usdt"),
          types.InlineKeyboardButton("📊 Transaction History",callback_data="d_hist"))
    bot.send_message(msg.chat.id,
        f"💳 *Aapka Wallet*\n\n"
        f"🆔 `{msg.from_user.id}`\n"
        f"💵 Balance:     *₹{u['balance']}*\n"
        f"🛒 Orders:      `{u.get('orders',0)}`\n"
        f"💸 Total Spent: `₹{u.get('total_spent',0)}`\n"
        f"💰 Earned:      `₹{u.get('total_earned',0)}`\n"
        f"👥 Referrals:   `{u.get('referrals',0)}`",reply_markup=m)

@bot.callback_query_handler(func=lambda c:c.data=="d_usdt")
def cb_usdt(call):
    m=types.InlineKeyboardMarkup(row_width=4)
    m.add(*[types.InlineKeyboardButton(f"${a}",callback_data=f"usdt_{a}") for a in USDT_AMOUNTS])
    m.add(types.InlineKeyboardButton("🔙 Back",callback_data="d_back"))
    bot.send_message(call.message.chat.id,"💎 *USDT — Amount chunein:*",reply_markup=m)

@bot.callback_query_handler(func=lambda c:c.data.startswith("usdt_"))
def cb_usdt_amt(call):
    amt=call.data.split("_")[1]; inr=int(float(amt)*USD_TO_INR)
    m=types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("💬 Admin se Binance Address Lein",
        url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    bot.send_message(call.message.chat.id,
        f"💎 *${amt} USDT Deposit — Steps:*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *STEP 1: Admin se Contact Karein PEHLE*\n"
        f"   👉 {SUPPORT_BOT}\n"
        f"   Bolein: *'${amt} USDT deposit karna hai'*\n\n"
        f"📋 *STEP 2: Admin Binance Address Dega*\n"
        f"   Admin aapko TRC20 address send karega\n\n"
        f"₿ *STEP 3: Binance se Send Karein*\n"
        f"   Amount: *${amt} USDT*\n"
        f"   Network: *TRC20 (TRON) only*\n"
        f"   ⚠️ Koi aur network use mat karein!\n\n"
        f"📸 *STEP 4: Screenshot Bhejein*\n"
        f"   Transaction screenshot is chat mein\n\n"
        f"✅ *STEP 5: Verify → ≈₹{inr} Wallet Mein!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💱 $1 ≈ ₹{USD_TO_INR} | ⏱ 5-30 min\n"
        f"⚠️ *Bina admin confirm ke send mat karein!*",reply_markup=m)

@bot.callback_query_handler(func=lambda c:c.data=="d_back")
def cb_dep_back(call):
    u=get_user(call.from_user.id)
    m=types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("💎 USDT Deposit",callback_data="d_usdt"),
          types.InlineKeyboardButton("📊 History",callback_data="d_hist"))
    bot.send_message(call.message.chat.id,f"💳 Balance: *₹{u['balance']}*",reply_markup=m)

@bot.callback_query_handler(func=lambda c:c.data=="d_hist")
def cb_hist(call):
    orders =list(orders_col.find({"user_id":call.from_user.id}).sort("created_at",-1).limit(8))
    deps   =list(deposits_col.find({"user_id":call.from_user.id}).sort("created_at",-1).limit(5))
    t="📊 *Transaction History*\n\n"
    if deps:
        t+="💰 *Deposits:*\n"
        for d in deps:
            ic="✅" if d['status']=="approved" else("❌" if d['status']=="rejected" else "⏳")
            t+=f"{ic} USDT ${d.get('usdt_amt',0)} ≈ ₹{d['amount']} — {d['created_at'].strftime('%d %b %H:%M')}\n"
        t+="\n"
    if orders:
        t+="🛒 *Orders:*\n"
        for o in orders:
            ic="✅" if o['status']=="done" else("❌" if o['status']=="cancelled" else "⏳")
            t+=f"{ic} {o['service']} ₹{o['amount']} — {o['created_at'].strftime('%d %b %H:%M')}\n"
    else: t+="📭 Koi order nahi."
    bot.send_message(call.message.chat.id,t)

@bot.message_handler(content_types=['photo'])
def on_photo(msg):
    if msg.from_user.id==OWNER_ID: return
    deposits_col.insert_one({
        "user_id":msg.from_user.id,"username":msg.from_user.username or "",
        "full_name":msg.from_user.first_name or "","amount":0,"usdt_amt":0,
        "status":"pending","method":"USDT","message_id":msg.message_id,
        "created_at":datetime.utcnow()})
    bot.forward_message(OWNER_ID,msg.chat.id,msg.message_id)
    bot.send_message(OWNER_ID,
        f"📩 *Naya Deposit Screenshot!*\n\n"
        f"👤 {msg.from_user.first_name} @{msg.from_user.username or 'N/A'}\n"
        f"🆔 `{msg.from_user.id}`\n\n"
        f"✅ `/add {msg.from_user.id} INR_AMOUNT USDT_AMOUNT`\n"
        f"❌ `/reject {msg.from_user.id}`")
    bot.reply_to(msg,"✅ *Screenshot mila!*\n⏳ Admin 5-30 min mein verify karega.")

# ══════════════════════════════════════════════════════════════════════════════
#  OWNER COMMANDS
# ══════════════════════════════════════════════════════════════════════════════
def oo(fn):   # owner_only decorator
    def w(msg):
        if msg.from_user.id!=OWNER_ID: return
        fn(msg)
    return w

@bot.message_handler(commands=['add'])
@oo
def cmd_add(msg):
    try:
        parts=msg.text.split(); uid=int(parts[1]); inr=int(parts[2])
        usdt=float(parts[3]) if len(parts)>3 else 0
        users_col.update_one({"user_id":uid},{"$inc":{"balance":inr}})
        deposits_col.update_one({"user_id":uid,"status":"pending"},
            {"$set":{"status":"approved","amount":inr,"usdt_amt":usdt}},sort=[("created_at",-1)])
        bot.send_message(uid,
            f"🎉 *Deposit Approved!*\n\n💎 ${usdt} USDT → *₹{inr}* wallet mein!\nAb number khareedein 🛒")
        bot.reply_to(msg,f"✅ ₹{inr} (${usdt}) → `{uid}`")
    except: bot.reply_to(msg,"❌ `/add USER_ID INR USDT`\nExample: `/add 123456 850 10`")

@bot.message_handler(commands=['reject'])
@oo
def cmd_reject(msg):
    try:
        uid=int(msg.text.split()[1])
        deposits_col.update_one({"user_id":uid,"status":"pending"},
            {"$set":{"status":"rejected"}},sort=[("created_at",-1)])
        bot.send_message(uid,f"❌ Deposit reject hua.\nRetry: {SUPPORT_BOT}")
        bot.reply_to(msg,f"✅ Rejected `{uid}`")
    except: bot.reply_to(msg,"❌ `/reject USER_ID`")

@bot.message_handler(commands=['deduct'])
@oo
def cmd_deduct(msg):
    try:
        _,uid,amt=msg.text.split()
        users_col.update_one({"user_id":int(uid)},{"$inc":{"balance":-int(amt)}})
        bot.reply_to(msg,f"✅ ₹{amt} deducted `{uid}`")
    except: bot.reply_to(msg,"❌ `/deduct USER_ID AMOUNT`")

@bot.message_handler(commands=['ban'])
@oo
def cmd_ban(msg):
    try:
        uid=int(msg.text.split()[1])
        users_col.update_one({"user_id":uid},{"$set":{"banned":True}})
        try: bot.send_message(uid,f"🚫 Ban kiya gaya.\nAppeal: {SUPPORT_BOT}")
        except: pass
        bot.reply_to(msg,f"🚫 `{uid}` banned.")
    except: bot.reply_to(msg,"❌ `/ban USER_ID`")

@bot.message_handler(commands=['unban'])
@oo
def cmd_unban(msg):
    try:
        uid=int(msg.text.split()[1])
        users_col.update_one({"user_id":uid},{"$set":{"banned":False}})
        try: bot.send_message(uid,"✅ Ban hata diya gaya.")
        except: pass
        bot.reply_to(msg,f"✅ `{uid}` unbanned.")
    except: bot.reply_to(msg,"❌ `/unban USER_ID`")

@bot.message_handler(commands=['broadcast'])
@oo
def cmd_bc(msg):
    t=msg.text.replace('/broadcast','',1).strip()
    if not t: bot.reply_to(msg,"❌ `/broadcast MESSAGE`"); return
    _bc(msg.chat.id,t)

@bot.message_handler(commands=['stats'])
@oo
def cmd_stats(msg): _stats(msg.chat.id)

@bot.message_handler(commands=['userinfo'])
@oo
def cmd_uinfo(msg):
    try: _uinfo(msg.chat.id,int(msg.text.split()[1]))
    except: bot.reply_to(msg,"❌ `/userinfo USER_ID`")

@bot.message_handler(commands=['makereseller'])
@oo
def cmd_reseller(msg):
    try:
        uid=int(msg.text.split()[1])
        users_col.update_one({"user_id":uid},{"$set":{"is_reseller":True}})
        bot.send_message(uid,"🎉 *Reseller ban gaye!*\nHar order par 10% extra earning!")
        bot.reply_to(msg,f"✅ `{uid}` is reseller now.")
    except: bot.reply_to(msg,"❌ `/makereseller USER_ID`")

# ── Admin Panel ────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m:m.text=="🔧 Admin Panel")
def admin_panel(msg):
    if msg.from_user.id!=OWNER_ID: return
    bot.send_message(msg.chat.id,"🔧 *Admin Panel*",reply_markup=mk_admin())

@bot.message_handler(func=lambda m:m.text=="📊 Stats" and m.from_user.id==OWNER_ID)
def ab_stats(msg): _stats(msg.chat.id)

@bot.message_handler(func=lambda m:m.text=="👥 Total Users" and m.from_user.id==OWNER_ID)
def ab_users(msg):
    total =users_col.count_documents({})
    active=users_col.count_documents({"orders":{"$gt":0}})
    banned=users_col.count_documents({"banned":True})
    today =users_col.count_documents({"joined_at":{"$gte":datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)}})
    resell=users_col.count_documents({"is_reseller":True})
    bot.send_message(msg.chat.id,
        f"👥 *User Analytics*\n\n"
        f"📊 Total:       `{total}`\n"
        f"✅ Active:      `{active}`\n"
        f"🚫 Banned:      `{banned}`\n"
        f"🌟 Resellers:   `{resell}`\n"
        f"🆕 Today:       `{today}`")

@bot.message_handler(func=lambda m:m.text=="📋 Pending Deposits" and m.from_user.id==OWNER_ID)
def ab_pend(msg):
    deps=list(deposits_col.find({"status":"pending"}).sort("created_at",-1).limit(10))
    if not deps: bot.send_message(msg.chat.id,"✅ Koi pending nahi."); return
    t="📋 *Pending Deposits:*\n\n"
    for d in deps:
        t+=(f"👤 {d.get('full_name','N/A')} @{d.get('username','N/A')}\n"
            f"🆔 `{d['user_id']}` — {d['created_at'].strftime('%d %b %H:%M')}\n"
            f"➡️ `/add {d['user_id']} INR USDT`\n\n")
    bot.send_message(msg.chat.id,t)

@bot.message_handler(func=lambda m:m.text=="💹 5sim Balance" and m.from_user.id==OWNER_ID)
def ab_sim(msg):
    try:
        r=requests.get("https://5sim.net/v1/user/profile",headers=SIM_HEADERS,timeout=10).json()
        bot.send_message(msg.chat.id,
            f"💹 *5sim Account*\n💵 Balance: `${r.get('balance',0):.4f}`\n📧 `{r.get('email','N/A')}`")
    except: bot.send_message(msg.chat.id,"❌ 5sim error")

@bot.message_handler(func=lambda m:m.text=="📢 Broadcast" and m.from_user.id==OWNER_ID)
def ab_bc(msg): bot.send_message(msg.chat.id,"📢 Format:\n`/broadcast Your message`")

@bot.message_handler(func=lambda m:m.text=="🏆 Top Buyers" and m.from_user.id==OWNER_ID)
def ab_top(msg):
    r=list(orders_col.aggregate([
        {"$match":{"status":"done"}},
        {"$group":{"_id":"$user_id","total":{"$sum":"$amount"},"cnt":{"$sum":1}}},
        {"$sort":{"total":-1}},{"$limit":10}]))
    if not r: bot.send_message(msg.chat.id,"📭"); return
    t="🏆 *Top 10 Buyers*\n\n"
    for i,x in enumerate(r,1):
        u=users_col.find_one({"user_id":x['_id']}) or {}
        n=u.get('full_name') or u.get('username') or str(x['_id'])
        t+=f"{i}. {n} — ₹{x['total']} ({x['cnt']})\n"
    bot.send_message(msg.chat.id,t)

@bot.message_handler(func=lambda m:m.text=="📦 Recent Orders" and m.from_user.id==OWNER_ID)
def ab_rec(msg):
    orders=list(orders_col.find().sort("created_at",-1).limit(10))
    if not orders: bot.send_message(msg.chat.id,"📭"); return
    t="📦 *Recent Orders*\n\n"
    for o in orders:
        ic="✅" if o['status']=="done" else("❌" if o['status']=="cancelled" else "⏳")
        t+=f"{ic} `{o['number']}` {o['service']}\n👤`{o['user_id']}` ₹{o['amount']} {o['created_at'].strftime('%d %b %H:%M')}\n\n"
    bot.send_message(msg.chat.id,t)

@bot.message_handler(func=lambda m:m.text=="📈 Stock Check" and m.from_user.id==OWNER_ID)
def ab_stock(msg):
    bot.send_message(msg.chat.id,"⏳ Checking..."); _stock_report(msg.chat.id)

@bot.message_handler(func=lambda m:m.text=="💾 Export Users" and m.from_user.id==OWNER_ID)
def ab_export(msg):
    import io
    users=list(users_col.find({},{"user_id":1,"username":1,"full_name":1,"balance":1,"orders":1,"banned":1}))
    lines=["ID | Name | Username | Balance | Orders | Banned"]
    lines+=[f"{u['user_id']}|{u.get('full_name','N/A')}|@{u.get('username','N/A')}|₹{u['balance']}|{u.get('orders',0)}|{u.get('banned',False)}"
            for u in users]
    f=io.BytesIO("\n".join(lines).encode()); f.name=f"users_{datetime.utcnow().strftime('%Y%m%d')}.txt"
    bot.send_document(msg.chat.id,f,caption=f"📦 Total: {len(users)} users")

@bot.message_handler(func=lambda m:m.text=="🔙 Back" and m.from_user.id==OWNER_ID)
def ab_back(msg): bot.send_message(msg.chat.id,"🏠",reply_markup=mk_main(OWNER_ID))

def _stats(cid):
    tu=users_col.count_documents({})
    bu=users_col.count_documents({"banned":True})
    to=orders_col.count_documents({})
    do=orders_col.count_documents({"status":"done"})
    co=orders_col.count_documents({"status":"cancelled"})
    pd=deposits_col.count_documents({"status":"pending"})
    ag=list(orders_col.aggregate([{"$match":{"status":"done"}},
        {"$group":{"_id":None,"rev":{"$sum":"$amount"},"pft":{"$sum":"$profit"}}}]))
    rev=ag[0]['rev'] if ag else 0; pft=ag[0]['pft'] if ag else 0
    bot.send_message(cid,
        f"📊 *Bot Statistics*\n\n"
        f"👥 Users:       `{tu}` (🚫{bu})\n"
        f"🛒 Orders:      `{to}`\n"
        f"✅ Done:        `{do}`\n"
        f"❌ Cancelled:   `{co}`\n"
        f"📥 Pending Dep: `{pd}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Revenue:     `₹{rev}`\n"
        f"📈 Net Profit:  `₹{pft}`\n"
        f"📊 Margin:      `{int(PROFIT_PCT*100)}%`")

def _uinfo(cid,uid):
    u=get_user(uid); uo=orders_col.count_documents({"user_id":uid,"status":"done"})
    bot.send_message(cid,
        f"👤 *User Info*\n🆔 `{u['user_id']}`\n"
        f"📛 {u.get('full_name','N/A')} @{u.get('username','N/A')}\n"
        f"💵 ₹{u['balance']} | 🛒 {uo} orders\n"
        f"💸 Spent: ₹{u.get('total_spent',0)} | 🌟 Reseller: {u.get('is_reseller',False)}\n"
        f"🚫 Banned: {u.get('banned',False)} | 📅 {str(u.get('joined_at',''))[:10]}")

def _bc(cid,text):
    all_u=list(users_col.find({"banned":{"$ne":True}}))
    pm=bot.send_message(cid,f"📢 {len(all_u)} users ko bhej rahe hain...")
    s=f=0
    for u in all_u:
        try: bot.send_message(u['user_id'],f"📢 *Announcement*\n\n{text}"); s+=1
        except: f+=1
        time.sleep(0.05)
    bot.edit_message_text(f"✅ Sent:`{s}` Failed:`{f}`",cid,pm.message_id)

def _stock_report(cid):
    checks=[("WhatsApp","russia","whatsapp","🇷🇺"),("WhatsApp","india","whatsapp","🇮🇳"),
            ("WhatsApp","usa","whatsapp","🇺🇸"),("Telegram","russia","telegram","🇷🇺"),
            ("Telegram","india","telegram","🇮🇳"),("Instagram","russia","instagram","🇷🇺"),
            ("Gmail","russia","google","🇷🇺"),("Gmail","india","google","🇮🇳")]
    t="📈 *Live Stock*\n\n"; lows=[]
    for svc,cc,api,flag in checks:
        _pcache.pop(f"{cc}|{api}",None); buy,cnt=live_ps(cc,api)
        if buy:
            s=sellp(buy); ic="🔴" if cnt<=LOW_STOCK_LIMIT else("🟡" if cnt<=20 else "🟢")
            t+=f"{ic}{flag}{cc.title()} {svc}: `{cnt}` | ₹{s}\n"
            if cnt<=LOW_STOCK_LIMIT: lows.append(f"{flag}{cc.title()} {svc}: *{cnt} left!*")
        else: t+=f"⚫{flag}{cc.title()} {svc}: Unavailable\n"
    t+=f"\n_{datetime.utcnow().strftime('%H:%M')} UTC_"
    bot.send_message(cid,t)
    if lows:
        bot.send_message(OWNER_ID,"⚠️ *LOW STOCK!*\n\n"+"\n".join(lows)+"\n\n💡 5sim.net balance add karein!")

def _stock_monitor():
    while True:
        time.sleep(1800)
        try:
            lows=[]
            for svc,cc,api,flag in [("WhatsApp","russia","whatsapp","🇷🇺"),("WhatsApp","india","whatsapp","🇮🇳"),
                                     ("Telegram","russia","telegram","🇷🇺"),("Telegram","india","telegram","🇮🇳")]:
                _pcache.pop(f"{cc}|{api}",None); buy,cnt=live_ps(cc,api)
                if buy is not None and cnt<=LOW_STOCK_LIMIT:
                    lows.append(f"{flag}{cc.title()} {svc}: *{cnt} bache!*")
            if lows: bot.send_message(OWNER_ID,"⚠️ *LOW STOCK ALERT!*\n\n"+"\n".join(lows)+"\n\n💡 https://5sim.net")
        except Exception as e: logger.error(f"Stock monitor: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  MY ORDERS
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m:m.text=="📋 My Orders")
@ban_check
@join_check
def my_orders(msg):
    orders=list(orders_col.find({"user_id":msg.from_user.id}).sort("created_at",-1).limit(7))
    if not orders: bot.send_message(msg.chat.id,"📭 Koi order nahi."); return
    t="📋 *Your Orders*\n\n"
    for o in orders:
        ic="✅" if o['status']=="done" else("❌" if o['status']=="cancelled" else "⏳")
        t+=f"{ic} `{o['number']}`\n   {o['service']} | ₹{o['amount']}\n   {o['created_at'].strftime('%d %b %H:%M')}\n\n"
    bot.send_message(msg.chat.id,t)

# ══════════════════════════════════════════════════════════════════════════════
#  EARN MONEY
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m:m.text=="💸 Earn Money")
@ban_check
@join_check
def earn_money(msg):
    uid=msg.from_user.id; u=get_user(uid)
    link=f"https://t.me/{bot.get_me().username}?start={uid}"
    m=types.InlineKeyboardMarkup()
    if not u.get('is_reseller'):
        m.add(types.InlineKeyboardButton("🌟 Reseller Banen",
            url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    bot.send_message(msg.chat.id,
        f"💸 *Earn Money — 3 Tarike*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*1️⃣ Referral*\n"
        f"   Har refer par *₹10* automatic\n"
        f"   Referrals: `{u.get('referrals',0)}` = ₹{u.get('referrals',0)*10}\n"
        f"   🔗 `{link}`\n\n"
        f"*2️⃣ Reseller* {'✅ Active' if u.get('is_reseller') else '❌ Not Active'}\n"
        f"   Numbers khareed ke dosto ko becho\n"
        f"   Example: ₹65 ka number → ₹120 mein becho\n"
        f"   *₹55 profit* per number!\n\n"
        f"*3️⃣ Channel Promote*\n"
        f"   Apna channel banao\n"
        f"   Bot link share karo\n"
        f"   Har join par referral income!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Total Earned: `₹{u.get('total_earned',0)}`",reply_markup=m if not u.get('is_reseller') else types.InlineKeyboardMarkup())

# ══════════════════════════════════════════════════════════════════════════════
#  REFER / HELP / PROOF / SUPPORT
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m:m.text=="👥 Refer & Earn")
@ban_check
@join_check
def refer(msg):
    uid=msg.from_user.id; u=get_user(uid)
    link=f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(msg.chat.id,
        f"👥 *Refer & Earn*\n\nHar refer par *₹10* milta hai!\n\n"
        f"Referrals: `{u.get('referrals',0)}` | Earned: `₹{u.get('referrals',0)*10}`\n\n"
        f"🔗 *Your Link:*\n`{link}`")

@bot.message_handler(func=lambda m:m.text=="❓ Help")
def help_btn(msg):
    m=types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("🤖 Help Bot — Direct Support",
              url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"),
          types.InlineKeyboardButton("📢 Proof Channel",url=PROOF_CHANNEL_LINK),
          types.InlineKeyboardButton("👥 Join Group",url=GROUP_LINK))
    bot.send_message(msg.chat.id,
        "❓ *Help & FAQ*\n\n"
        "🔹 *Number kaise khareedein?*\n   Service → Country → Confirm\n\n"
        "🔹 *Balance add kaise?*\n   Wallet → USDT → Admin contact → Pay → Screenshot\n\n"
        "🔹 *OTP nahi aaya?*\n   5 min wait → Auto Refund\n\n"
        "🔹 *Earn kaise karein?*\n   Earn Money button dabayein\n\n"
        "🆘 *Help Bot par jaayein* 👇",reply_markup=m)

@bot.message_handler(func=lambda m:m.text=="📊 Proof")
def proof_btn(msg):
    m=types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("📢 Proof Channel",url=PROOF_CHANNEL_LINK))
    bot.send_message(msg.chat.id,"📊 *Proof Channel*\n\n✅ Har successful OTP proof auto post hota hai.",reply_markup=m)

@bot.message_handler(func=lambda m:m.text=="📞 Support")
def support_btn(msg):
    m=types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("💬 Support Bot",url=f"https://t.me/{SUPPORT_BOT.replace('@','')}"))
    bot.send_message(msg.chat.id,f"📞 *Support*\n{SUPPORT_BOT}\n⏰ 10AM-10PM IST",reply_markup=m)

# ══════════════════════════════════════════════════════════════════════════════
#  BUY FLOW
# ══════════════════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m:m.text in ALL_BTNS)
@ban_check
@join_check
def show_countries(msg):
    cat=msg.text; items=SERVICES.get(cat,{})
    lm=bot.send_message(msg.chat.id,f"⏳ *{cat}* — Live data loading...")
    mk=types.InlineKeyboardMarkup(row_width=1)
    for key,info in items.items():
        buy,cnt=live_ps(info['cc'],info['api'])
        if buy and cnt>0:
            s=sellp(buy); si="🔴" if cnt<=5 else("🟡" if cnt<=20 else "🟢")
            mk.add(types.InlineKeyboardButton(
                f"{info['flag']} {info['country']}  ·  ₹{s}  {si}{cnt}",callback_data=f"buy_{key}"))
        else:
            mk.add(types.InlineKeyboardButton(
                f"{info['flag']} {info['country']}  ·  ❌ Out of Stock",callback_data="oos"))
    mk.add(types.InlineKeyboardButton("🔙 Main Menu",callback_data="gomn"))
    bot.edit_message_text(
        f"{cat} — *Country chunein:*\n🟢OK 🟡Low 🔴Critical ❌Out\n_60% margin included_",
        lm.chat.id,lm.message_id,reply_markup=mk)

@bot.callback_query_handler(func=lambda c:c.data=="oos")
def cb_oos(call): bot.answer_callback_query(call.id,"❌ Stock khatam! Dusri try karein.",show_alert=True)

@bot.callback_query_handler(func=lambda c:c.data=="gomn")
def cb_gomn(call): bot.send_message(call.message.chat.id,"🏠",reply_markup=mk_main(call.from_user.id))

@bot.callback_query_handler(func=lambda c:c.data.startswith("buy_"))
def cb_buy(call):
    if is_banned(call.from_user.id): return bot.answer_callback_query(call.id,"🚫 Ban.",show_alert=True)
    if not is_member(call.from_user.id) and call.from_user.id!=OWNER_ID:
        return bot.answer_callback_query(call.id,"⚠️ Pehle Join karein!",show_alert=True)
    key=call.data[4:]; svc,cat=find_svc(key)
    if not svc: return bot.answer_callback_query(call.id,"❌ Invalid.",show_alert=True)
    buy,cnt=live_ps(svc['cc'],svc['api'])
    if not buy or cnt==0: return bot.answer_callback_query(call.id,"❌ Stock khatam!",show_alert=True)
    sell=sellp(buy); u=get_user(call.from_user.id)
    if u['balance']<sell:
        return bot.answer_callback_query(call.id,
            f"❌ Balance kam!\nChahiye:₹{sell}\nHai:₹{u['balance']}\nKam:₹{sell-u['balance']}",show_alert=True)
    bot.answer_callback_query(call.id,"⏳ Number dhundh rahe hain...")
    sm=bot.send_message(call.message.chat.id,
        f"🔄 *Processing...*\n{svc['flag']} {svc['country']} {cat}\n💵 ₹{sell}")
    url=f"https://5sim.net/v1/user/buy/activation/{svc['cc']}/any/{svc['api']}"
    try: res=requests.get(url,headers=SIM_HEADERS,timeout=15).json()
    except Exception as e:
        logger.error(e); bot.edit_message_text("❌ API Error. Baad mein try karein.",call.message.chat.id,sm.message_id); return
    if 'phone' in res:
        oid=res['id']; num=res['phone']; nb=u['balance']-sell
        users_col.update_one({"user_id":call.from_user.id},{"$inc":{"balance":-sell,"orders":1,"total_spent":sell}})
        log_order(call.from_user.id,cat,svc,num,oid,buy,sell)
        bot.edit_message_text(
            f"✅ *Number mila!*\n\n📞 `{num}`\n{svc['flag']} {svc['country']} {cat}\n"
            f"💵 ₹{sell} | Balance: ₹{nb}\n\n⏳ *OTP wait...* _(5 min → Auto Refund)_",
            call.message.chat.id,sm.message_id)
        Thread(target=_otp_wait,args=(call.message.chat.id,call.from_user.id,oid,sell,num,svc,cat,nb),daemon=True).start()
    else:
        bot.edit_message_text(f"❌ Number nahi mila\n{res.get('message','')}\n_Balance safe._",
            call.message.chat.id,sm.message_id)

# ── OTP + Proof ────────────────────────────────────────────────────────────────
def _post_proof(uid,num,svc,cat,amt,otp):
    u=users_col.find_one({"user_id":uid}) or {}
    name=u.get('full_name') or f"User{str(uid)[-4:]}"
    masked=num[:4]+"****"+num[-2:] if len(num)>6 else num
    try:
        bot.send_message(PROOF_CHANNEL_ID,
            f"✅ *OTP Delivered!*\n\n📞 `{masked}`\n{svc['flag']} {svc['country']} {cat}\n"
            f"💵 ₹{amt}\n🔑 OTP: `{otp}`\n👤 {name}\n"
            f"🕐 {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC\n\n"
            f"🔥 *OtpKing Store*\n{CHANNEL_LINK}")
    except Exception as e: logger.warning(f"Proof: {e}")

def _otp_wait(cid,uid,oid,refund,num,svc,cat,rbal):
    for _ in range(30):
        time.sleep(10)
        try:
            r=requests.get(f"https://5sim.net/v1/user/check/{oid}",headers=SIM_HEADERS,timeout=10).json()
        except Exception as e: logger.error(e); continue
        if r.get('sms'):
            otp=r['sms'][0]['code']
            orders_col.update_one({"order_id":oid},{"$set":{"status":"done","otp":otp}})
            bot.send_message(cid,
                f"🎉 *OTP aa gaya!*\n\n📞 `{num}`\n{svc['flag']} {svc['country']} {cat}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n🔑 *OTP:* `{otp}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n💰 Balance: ₹{rbal}\n✅ Done! 🙏")
            Thread(target=_post_proof,args=(uid,num,svc,cat,refund,otp),daemon=True).start()
            return
    try: requests.get(f"https://5sim.net/v1/user/cancel/{oid}",headers=SIM_HEADERS,timeout=10)
    except: pass
    orders_col.update_one({"order_id":oid},{"$set":{"status":"cancelled"}})
    users_col.update_one({"user_id":uid},{"$inc":{"balance":refund,"total_spent":-refund}})
    bot.send_message(cid,f"❌ *OTP Timeout*\n📞 `{num}`\n\n💰 *₹{refund} Refund ho gaya!*")

# ── Gaali filter on ALL messages ──────────────────────────────────────────────
@bot.message_handler(func=lambda m:True)
@gaali_check
def fallback(msg):
    bot.send_message(msg.chat.id,"❓ Buttons use karein 👇",reply_markup=mk_main(msg.from_user.id))

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN — single instance with retry
# ══════════════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    logger.info("🤖 OtpKing Bot starting...")
    Thread(target=_stock_monitor,daemon=True).start()
    while True:
        try:
            logger.info("Starting polling...")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
            clear_webhook_and_updates()
