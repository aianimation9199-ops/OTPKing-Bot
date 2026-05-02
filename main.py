import os, logging, requests, time, math, threading
from pymongo import MongoClient
from telebot import types
import telebot
from dotenv import load_dotenv
from datetime import datetime
from bson.objectid import ObjectId

# --- CONFIG ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv()

BOT_TOKEN    = os.getenv('BOT_TOKEN', '')
MONGO_URI    = os.getenv('MONGO_URI', '')
OWNER_ID     = int(os.getenv('OWNER_ID', '0'))
FIVE_SIM_KEY = os.getenv('SIM_API_KEY', '') # 5Sim
VAK_SMS_KEY  = os.getenv('VAK_SMS_KEY', '') # VAK-SMS

MARGIN = 1.40  # 40% Profit
USDT_RATE = 85.0

# Channels for Force Join
CHANNELS = [os.getenv('CH1_ID', '@Ch1'), os.getenv('CH2_ID', '@Ch2')]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
db = MongoClient(MONGO_URI)['otp_king_final_db']
users_col = db['users']
orders_col = db['orders']
platforms_col = db['earning_platforms']

# --- VAK-SMS & 5SIM MAPPINGS ---
# VAK-SMS Country Codes: ru, id, in, etc.
VAK_CC = {"russia": "ru", "india": "in", "indonesia": "id", "usa": "us", "brazil": "br"}
# VAK-SMS Service Codes: wa, tg, ig, go, fb
VAK_SVC = {"whatsapp": "wa", "telegram": "tg", "instagram": "ig", "google": "go", "facebook": "fb"}

SERVICES = {
    "📱 WhatsApp": {"cc": "india", "api": "whatsapp", "flag": "🇮🇳", "country": "India", "key": "wa_india"},
    "✈️ Telegram": {"cc": "india", "api": "telegram", "flag": "🇮🇳", "country": "India", "key": "tg_india"},
    "📸 Instagram": {"cc": "russia", "api": "instagram", "flag": "🇷🇺", "country": "Russia", "key": "ig_russia"}
}

# --- CORE UTILS ---
def get_user(uid, uname=None):
    return users_col.find_one_and_update(
        {"user_id": uid},
        {"$setOnInsert": {"user_id": uid, "username": uname, "balance": 0.0, "orders": 0, "joined_at": datetime.utcnow()}},
        upsert=True, return_document=True
    )

def is_joined(uid):
    if uid == OWNER_ID: return True
    try:
        for ch in CHANNELS:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        return True
    except: return False

# --- PRICE ENGINE ---
def get_best_price(cc, svc):
    p5 = None
    try:
        r = requests.get(f"https://5sim.net/v1/guest/prices?country={cc}&product={svc}", timeout=5).json()
        cost = list(r[cc][svc].values())[0]['cost']
        p5 = (math.ceil(cost * USDT_RATE * MARGIN), "5sim")
    except: pass

    pvak = None
    try:
        v_cc = VAK_CC.get(cc)
        v_svc = VAK_SVC.get(svc)
        # VAK Price API: getCountNumber
        r = requests.get(f"https://vak-sms.com/api/v2/getCountNumber/?apiKey={VAK_SMS_KEY}&service={v_svc}&country={v_cc}").json()
        # VAK returns direct price in RUB, we assume 1 RUB = 1.1 INR approx or use a fixed multiplier
        cost = float(r.get('price', 999))
        pvak = (math.ceil(cost * 1.5 * MARGIN), "vaksms") # 1.5 is RUB to INR conversion
    except: pass

    if p5 and pvak: return p5 if p5[0] <= pvak[0] else pvak
    return p5 or pvak or (None, None)

# --- BUYING ENGINE ---
def smart_buy(cc, svc, source):
    if source == "5sim":
        try:
            h = {'Authorization': f'Bearer {FIVE_SIM_KEY}', 'Accept': 'application/json'}
            r = requests.get(f"https://5sim.net/v1/user/buy/activation/{cc}/any/{svc}", headers=h).json()
            return r['id'], r['phone']
        except: return None, None
    else:
        try:
            v_cc, v_svc = VAK_CC.get(cc), VAK_SVC.get(svc)
            r = requests.get(f"https://vak-sms.com/api/v2/getNumber/?apiKey={VAK_SMS_KEY}&service={v_svc}&country={v_cc}").json()
            if 'idNum' in r: return r['idNum'], "+" + str(r['tel'])
        except: return None, None
    return None, None

def check_otp(oid, source):
    if source == "5sim":
        try:
            h = {'Authorization': f'Bearer {FIVE_SIM_KEY}', 'Accept': 'application/json'}
            r = requests.get(f"https://5sim.net/v1/user/check/{oid}", headers=h).json()
            if r.get('sms'): return r['sms'][0]['code']
        except: return None
    else:
        try:
            r = requests.get(f"https://vak-sms.com/api/v2/getSmsCode/?apiKey={VAK_SMS_KEY}&idNum={oid}").json()
            return r.get('smsCode') # VAK returns None if not received
        except: return None

# --- KEYBOARDS ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("📲 Buy Number", "💰 Wallet")
    m.add("📋 My Orders", "👥 Refer & Earn")
    m.add("🆘 Help")
    return m

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    get_user(uid, msg.from_user.username)
    if not is_joined(uid):
        mk = types.InlineKeyboardMarkup()
        for ch in CHANNELS: mk.add(types.InlineKeyboardButton("Join Channel", url=f"https://t.me/{ch[1:]}"))
        bot.send_message(uid, "❌ **Pehle Join Karein!**", reply_markup=mk)
        return
    bot.send_message(uid, "👑 **Welcome to OtpKing (5Sim + VAK-SMS)!**", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📲 Buy Number")
def buy_menu(msg):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for name, info in SERVICES.items():
        price, src = get_best_price(info['cc'], info['api'])
        if price:
            mk.add(types.InlineKeyboardButton(f"{info['flag']} {name} - ₹{price}", callback_data=f"buy_{info['key']}"))
    bot.send_message(msg.chat.id, "🎯 **Select Service:**", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith('buy_'))
def handle_purchase(call):
    uid = call.from_user.id
    key = call.data.split('_')[1]
    
    # Find service info
    svc_info = None
    for s in SERVICES.values():
        if s['key'] == key: svc_info = s; break
    
    price, source = get_best_price(svc_info['cc'], svc_info['api'])
    user = get_user(uid)

    if user['balance'] < price:
        bot.answer_callback_query(call.id, "❌ Low Balance!", show_alert=True)
        return

    bot.edit_message_text("⏳ Number nikal raha hoon...", call.message.chat.id, call.message.message_id)
    oid, num = smart_buy(svc_info['cc'], svc_info['api'], source)

    if oid and num:
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -price, "orders": 1}})
        orders_col.insert_one({"user_id": uid, "order_id": str(oid), "num": num, "price": price, "source": source, "status": "pending"})
        
        bot.edit_message_text(f"✅ **Number:** `{num}`\n💰 **Price:** ₹{price}\n\n⏳ OTP ka wait karein...", call.message.chat.id, call.message.message_id)
        threading.Thread(target=otp_worker, args=(call.message.chat.id, uid, oid, source, price)).start()
    else:
        bot.edit_message_text("❌ No stock in both APIs.", call.message.chat.id, call.message.message_id)

def otp_worker(chat_id, uid, oid, source, price):
    for _ in range(15): # 5 minutes
        time.sleep(20)
        otp = check_otp(oid, source)
        if otp:
            bot.send_message(chat_id, f"📩 **OTP Received:** `{otp}`")
            orders_col.update_one({"order_id": oid}, {"$set": {"status": "completed", "otp": otp}})
            return
    
    # Refund
    users_col.update_one({"user_id": uid}, {"$inc": {"balance": price}})
    orders_col.update_one({"order_id": oid}, {"$set": {"status": "refunded"}})
    bot.send_message(chat_id, "⚠️ OTP Timeout! Balance Refunded.")

@bot.message_handler(func=lambda m: m.text == "💰 Wallet")
def wallet(msg):
    u = get_user(msg.from_user.id)
    bot.send_message(msg.chat.id, f"💳 **Wallet Balance:** ₹{u['balance']}\n\nDeposit ke liye admin ko message karein.")

@bot.message_handler(func=lambda m: m.text == "👥 Refer & Earn")
def refer(msg):
    plats = list(platforms_col.find())
    if not plats:
        bot.send_message(msg.chat.id, "❌ No platforms.")
        return
    mk = types.InlineKeyboardMarkup()
    for p in plats: mk.add(types.InlineKeyboardButton(p['name'], url=p['link']))
    bot.send_message(msg.chat.id, "💰 **Earning Platforms:**", reply_markup=mk)

# --- ADMIN ---
@bot.message_handler(commands=['add_bal'])
def add_bal(msg):
    if msg.from_user.id != OWNER_ID: return
    args = msg.text.split()
    users_col.update_one({"user_id": int(args[1])}, {"$inc": {"balance": float(args[2])}}, upsert=True)
    bot.reply_to(msg, "✅ Done!")

@bot.message_handler(commands=['add_plat'])
def add_plat(msg):
    if msg.from_user.id != OWNER_ID: return
    try:
        # /add_plat Name|Link
        data = msg.text.split()[1]
        name, link = data.split('|')
        platforms_col.insert_one({"name": name, "link": link})
        bot.reply_to(msg, "✅ Platform Added!")
    except: pass

if __name__ == "__main__":
    bot.infinity_polling()
