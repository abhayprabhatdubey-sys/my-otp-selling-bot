import telebot
from telebot import types

# --- CONFIGURATION ---
# Aapka Bot Token
TOKEN = '8745603057:AAGrtukbcj7KCBZK2FsX5j89sA4VfPrN'
# Aapki Telegram ID (Admin)
ADMIN_ID = 7634311488 

bot = telebot.TeleBot(TOKEN)

# Temporary data store (Balance save karne ke liye)
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    # Agar naya user hai toh 0 balance set karo
    if user_id not in user_data:
        user_data[user_id] = {'balance': 0}
    
    # Buttons banana
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('🛍️ Buy Accounts')
    btn2 = types.KeyboardButton('💰 Balance')
    btn3 = types.KeyboardButton('📥 Deposit')
    btn4 = types.KeyboardButton('📞 Support')
    markup.add(btn1, btn2, btn3, btn4)
    
    welcome_text = f"Welcome {message.from_user.first_name}!\nUnlimited OTP Bot ready hai. Kya help chahiye?"
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '💰 Balance')
def check_balance(message):
    user_id = message.from_user.id
    bal = user_data.get(user_id, {}).get('balance', 0)
    bot.reply_to(message, f"👤 User: {message.from_user.first_name}\n💰 Aapka Current Balance: {bal} INR")

@bot.message_handler(func=lambda message: message.text == '📞 Support')
def support(message):
    bot.reply_to(message, "Bhai, support ke liye Admin ko contact karein: @Abhay_Support_Bot") # Yahan apna handle daal dena

# Bot ko chalu rakhne ke liye
print("Bot is running...")
bot.polling(none_stop=True)
