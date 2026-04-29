import telebot
from telebot import types
from pymongo import MongoClient
import os, threading, json, time
from flask import Flask

# --- RENDER UPTIME FIX ---
app = Flask('')
@app.route('/')
def home(): return "TITAN BOT IS ALIVE"

def run_web():
    # Render automatically provides a PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

# --- CONFIG (Fetching from Render Env Variables) ---
TOKEN = os.environ.get("BOT_TOKEN", "8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw")
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGODB_LINK_HERE")
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- DB SETUP ---
client = MongoClient(MONGO_URI)
db = client['titan_render_db']
users = db['users']
settings = db['settings']

# Settings Init
if not settings.find_one({"id": "config"}):
    settings.insert_one({"id": "config", "admins": [OWNER_ID], "upi": "abhay-op.315@ptyes", "buy_rates": {}, "sell_rates": {}})

# --- REUSABLE KEYBOARD ---
def main_kb():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📊 STATS', '📞 SUPPORT')
    return kb

# ==========================================
# 📥 DEPOSIT LOGIC (STRICT 12-DIGIT UTR)
# ==========================================
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(m):
    msg = bot.send_message(m.chat.id, "💵 **Amount enter karein (₹):**")
    bot.register_next_step_handler(msg, get_amt)

def get_amt(m):
    if not m.text.isdigit():
        return bot.send_message(m.chat.id, "❌ Invalid! Sirf numbers dalo.")
    amt = m.text
    conf = settings.find_one({"id": "config"})
    bot.send_message(m.chat.id, f"💳 Pay: `{conf['upi']}`\n\nAb **12-digit UTR** bhejein:")
    bot.register_next_step_handler(m, get_utr, amt)

def get_utr(m, amt):
    utr = m.text.strip()
    if len(utr) != 12 or not utr.isdigit():
        return bot.send_message(m.chat.id, "❌ **Error:** UTR 12 digit ka hona chahiye. Dubara /start karein.")
    
    bot.send_message(m.chat.id, "📸 **Screenshot** bhejein:")
    bot.register_next_step_handler(m, finish_dep, amt, utr)

def finish_dep(m, amt, utr):
    if m.content_type != 'photo':
        return bot.send_message(m.chat.id, "❌ Photo missing.")
    
    mk = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"ADM_OK_{m.from_user.id}_{amt}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"ADM_NO_{m.from_user.id}")
    )
    conf = settings.find_one({"id": "config"})
    for a in conf['admins']:
        bot.send_photo(a, m.photo[-1].file_id, caption=f"💰 **NEW DEP**\nUser: `{m.from_user.id}`\nAmt: ₹{amt}\nUTR: {utr}", reply_markup=mk)
    bot.send_message(m.chat.id, "⏳ Request sent to Admin.")

# ==========================================
# 👑 ADMIN COMMANDS
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_cmd(m):
    conf = settings.find_one({"id": "config"})
    if m.from_user.id not in conf['admins']: return
    bot.send_message(m.chat.id, "👑 **ADMIN PANEL**\n\n`/addc NAME BUY SELL`\n`/setupi UPI`\n`/addbal ID AMT`")

@bot.message_handler(commands=['addc'])
def add_country(m):
    conf = settings.find_one({"id": "config"})
    if m.from_user.id not in conf['admins']: return
    try:
        _, name, b, s = m.text.split()
        settings.update_one({"id": "config"}, {"$set": {f"buy_rates.{name.upper()}": int(b), f"sell_rates.{name.upper()}": int(s)}})
        bot.reply_to(m, "✅ Market Updated.")
    except: pass

# ==========================================
# ⚙️ CALLBACKS & POLLING
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_cbs(call):
    p = call.data.split('_')
    if p[0] == 'ADM':
        uid = p[2]
        if p[1] == 'OK':
            amt = int(p[3])
            users.update_one({"uid": uid}, {"$inc": {"bal": amt}}, upsert=True)
            bot.send_message(int(uid), f"✅ ₹{amt} added!")
            bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def welcome(m):
    bot.send_message(m.chat.id, "🔥 **TITAN RENDER V12**\nEverything Fixed & Validated.", reply_markup=main_kb())

bot.infinity_polling()
