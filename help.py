"""
╔══════════════════════════════════════════════╗
║         ANOKHA HELP BOT                     ║
║  • FAQ buttons                              ║
║  • User → Admin message forward            ║
║  • Admin → User reply                       ║
║  • Gaali → Auto block                       ║
╚══════════════════════════════════════════════╝
"""
import os, logging
from telebot import types
import telebot
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
HELP_BOT_TOKEN = os.getenv('HELP_BOT_TOKEN')
OWNER_ID       = int(os.getenv('OWNER_ID'))
MAIN_BOT       = os.getenv('BOT_USERNAME', '@AnokhaOTPBot')
MONGO_URI      = os.getenv('MONGO_URI')

bot   = telebot.TeleBot(HELP_BOT_TOKEN, parse_mode="Markdown")
mongo = MongoClient(MONGO_URI)
db    = mongo['anokha_otp_db']
users_col = db['users']

# Track owner replies
_reply_map = {}  # fwd_msg_id → user_id

BAD_WORDS = [
    "madarchod","mc","bc","bhenchod","gandu","chutiya","randi","harami",
    "bhosdike","loda","lauda","chut","bsdk","fuck","bitch","asshole",
    "bastard","shit","dick","cunt","whore","sala"
]
def has_bad(text): return any(w in (text or "").lower() for w in BAD_WORDS)

FAQ = {
    "💰 Deposit kaise karein?":
        "💰 *Deposit Steps:*\n\n"
        "1️⃣ Main bot: " + MAIN_BOT + "\n"
        "2️⃣ Wallet → USDT Deposit\n"
        "3️⃣ Amount select karein\n"
        "4️⃣ *Pehle Admin se contact karein*\n"
        "5️⃣ Admin address dega → Binance TRC20 se send karein\n"
        "6️⃣ Screenshot bhejein → Admin verify → Balance add!",

    "📱 Number kaise khareedein?":
        "📱 *Number Buy Steps:*\n\n"
        "1️⃣ Wallet mein balance hona chahiye\n"
        "2️⃣ Service choose karein (WhatsApp etc)\n"
        "3️⃣ Country choose karein (live stock dikhega)\n"
        "4️⃣ Confirm → Number milega\n"
        "5️⃣ OTP automatically aayega (max 5 min)\n"
        "6️⃣ OTP nahi aaya? *Auto Refund*!",

    "🔄 Refund policy?":
        "🔄 *Refund Policy:*\n\n"
        "✅ OTP 5 min mein nahi aaya → *Auto Refund*\n"
        "✅ Number available nahi → *Instant Refund*\n"
        "❌ OTP aa gaya → Refund nahi hoga\n\n"
        "Refund automatically wallet mein aata hai.",

    "💎 USDT deposit kaise karein?":
        "💎 *USDT Deposit:*\n\n"
        "⚠️ *PEHLE Admin se confirm karein!*\n\n"
        "1️⃣ Admin ko message karein: 'USDT deposit karna hai $X'\n"
        "2️⃣ Admin USDT TRC20 address dega\n"
        "3️⃣ Binance se TRC20 mein bhejein\n"
        "4️⃣ Screenshot bhejein\n"
        "5️⃣ Verify → Balance add!\n\n"
        "⚠️ Bina confirm ke payment mat karein!",

    "❓ OTP nahi aaya?":
        "❓ *OTP Nahi Aaya?*\n\n"
        "✅ 5 minute wait karein\n"
        "✅ 5 min ke baad auto refund hoga\n"
        "✅ Dobara try karein ya dusri country try karein\n\n"
        "Agar phir bhi problem ho toh yahan message karein.",

    "💸 Paise kaise kamayen?":
        "💸 *Earning Ways:*\n\n"
        "1️⃣ *Referral:* Har refer par ₹10\n"
        "   Main bot → Refer & Earn → Link share karein\n\n"
        "2️⃣ *Reseller:* Numbers khareed ke zyada mein becho\n"
        "   Admin se contact karein reseller banane ke liye\n\n"
        "3️⃣ *Channel:* Apna channel banao, bot link share karo",

    "🚫 Ban kyon hua?":
        "🚫 *Ban Reasons:*\n\n"
        "• Abusive language / gaaliyan\n"
        "• Fraud activity\n"
        "• Fake screenshots\n\n"
        "Appeal ke liye yahan message karein.",
}

def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for q in FAQ: m.add(q)
    m.add("💬 Admin se directly baat karein")
    m.add("🔥 Main Bot par jaayein")
    return m

@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id,
        "🤖 *Anokha Help Bot*\n\n"
        "Namaste! Koi bhi sawaal poochh sakte hain.\n\n"
        "👇 Apni problem choose karein:",
        reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text in FAQ and m.from_user.id != OWNER_ID)
def faq_ans(msg):
    bot.send_message(msg.chat.id, FAQ[msg.text], reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "💬 Admin se directly baat karein")
def contact_admin(msg):
    bot.send_message(msg.chat.id,
        "💬 *Admin se Baat Karein*\n\n"
        "Apni problem type karein aur bhejein.\n"
        "Admin jald reply karega.\n"
        "⏰ Available: 10AM - 10PM IST")

@bot.message_handler(func=lambda m: m.text == "🔥 Main Bot par jaayein")
def main_bot_btn(msg):
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("🔥 Main Bot",
        url=f"https://t.me/{MAIN_BOT.replace('@', '')}"))
    bot.send_message(msg.chat.id, "👇 Main bot:", reply_markup=m)

# ── All user messages → forward to owner ──────────────────────────────────────
@bot.message_handler(func=lambda m: m.from_user.id != OWNER_ID)
def user_msg(msg):
    uid = msg.from_user.id

    # Gaali check → auto ban
    if has_bad(msg.text):
        users_col.update_one({"user_id": uid}, {"$set": {"banned": True}})
        bot.send_message(uid,
            "🚫 *Block हो गए!*\n\n"
            "Abusive language se account ban hota hai.\n"
            "Appeal ke liye: dusre account se contact karein.")
        bot.send_message(OWNER_ID,
            f"⚠️ *Help Bot Auto-Ban*\n\n"
            f"👤 {msg.from_user.first_name} @{msg.from_user.username or 'N/A'}\n"
            f"🆔 `{uid}`\n💬 `{msg.text}`")
        return

    name  = msg.from_user.first_name or "User"
    uname = f"@{msg.from_user.username}" if msg.from_user.username else f"ID:{uid}"
    fwd   = bot.send_message(OWNER_ID,
        f"📩 *Help Bot Message*\n\n"
        f"👤 {name} {uname}\n"
        f"🆔 `{uid}`\n\n"
        f"💬 {msg.text or '[media/sticker]'}\n\n"
        f"_Is message pe reply karein answer bhejne ke liye_")
    _reply_map[fwd.message_id] = uid
    bot.reply_to(msg, "✅ Message admin tak pahunch gaya!\nJald reply milega. ⏰")

# ── Owner reply → forward to user ─────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID)
def owner_reply(msg):
    if msg.reply_to_message and msg.reply_to_message.message_id in _reply_map:
        uid = _reply_map[msg.reply_to_message.message_id]
        try:
            bot.send_message(uid,
                f"💬 *Admin ka Reply:*\n\n{msg.text or '[media]'}")
            bot.reply_to(msg, f"✅ Reply bhej diya user `{uid}` ko!")
        except:
            bot.reply_to(msg, "❌ User tak nahi pahuncha (blocked/left).")
    else:
        bot.send_message(msg.chat.id,
            "ℹ️ User ke forward message pe *reply* karein\nwarna user ko nahi jayega.")

if __name__ == "__main__":
    logger.info("🤖 Help Bot starting...")
    bot.infinity_polling(timeout=30, long_polling_timeout=15)
