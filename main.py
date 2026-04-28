import telebot
from telebot import types

# --- CONFIGURATION ---
TOKEN = 8745603057:AAHQfMfRNXP_898hBrZToaXsEigbP_m2sZQ
ADMIN_ID = 7634311488 

bot = telebot.TeleBot(TOKEN)
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {'balance': 0}
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('🛍️ Buy Accounts')
    btn2 = types.KeyboardButton('💰 Balance')
    btn3 = types.KeyboardButton('📥 Deposit')
    btn4 = types.KeyboardButton('📞 Support')
    markup.add(btn1, btn2, btn3, btn4)
    
    bot.send_message(message.chat.id, f"Welcome {message.from_user.first_name}!\nUnlimited OTP Bot ready hai.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '💰 Balance')
def check_balance(message):
    bal = user_data.get(message.from_user.id, {}).get('balance', 0)
    bot.reply_to(message, f"👤 User: {message.from_user.first_name}\n💰 Aapka Balance: {bal} INR")

print("Bot chalu ho gaya hai...")
bot.polling(none_stop=True)
