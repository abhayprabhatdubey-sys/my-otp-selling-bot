import telebot
from telebot import types
import time

# --- CONFIGURATION ---
# Aapka ekdum naya token
TOKEN = '8692935006:AAF3uUPWZbd9f4NuiUZPbWYycUDrfsEY1tQ'
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
    
    bot.send_message(message.chat.id, f"Welcome {message.from_user.first_name}!\nAbhay ka Bot ekdum mast chal raha hai.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '💰 Balance')
def check_balance(message):
    bal = user_data.get(message.from_user.id, {}).get('balance', 0)
    bot.reply_to(message, f"👤 User: {message.from_user.first_name}\n💰 Balance: {bal} INR")

@bot.message_handler(func=lambda message: message.text == '📞 Support')
def support(message):
    bot.reply_to(message, "Admin se contact karein: @Abhay_Support")

# Loop to handle 409 Conflict automatically
while True:
    try:
        print("Bot starting fresh...")
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Connection issue: {e}")
        time.sleep(5)
