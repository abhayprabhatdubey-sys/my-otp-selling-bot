async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'admin_panel':
        if user_id != OWNER_ID:
            return await query.edit_message_text("❌ Unauthorized access.")
            
        keyboard = [
            [InlineKeyboardButton("➕ Add Stock", callback_data='admin_add_stock'), InlineKeyboardButton("➖ Remove Stock", callback_data='admin_rem_stock')],
            [InlineKeyboardButton("✅ Approve Deposits", callback_data='admin_deposits')],
            [InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast'), InlineKeyboardButton("👥 Users", callback_data='admin_users')],
            [InlineKeyboardButton("🔙 Back to Main", callback_data='start_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⚙️ Advanced Admin Panel\nSelect an operation:", reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == 'start_menu':
        keyboard = [
            [InlineKeyboardButton("🛒 Buy Products", callback_data='buy_menu')],
            [InlineKeyboardButton("💰 Deposit Funds", callback_data='deposit_menu'), InlineKeyboardButton("👤 Profile", callback_data='profile')],
            [InlineKeyboardButton("🔗 Refer & Earn", callback_data='referral_menu')]
        ]
        if user_id == OWNER_ID:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data='admin_panel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Main Menu:", reply_markup=reply_markup)

    elif query.data == 'profile':
        conn = sqlite3.connect('store.db')
        c = conn.cursor()
        c.execute("SELECT balance, is_reseller FROM users WHERE user_id = ?", (user_id,))
        user_data = c.fetchone()
        conn.close()
        
        balance = user_data[0] if user_data else 0.0
        reseller_status = "Yes ⭐" if user_data and user_data[1] else "No"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='start_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        profile_text = (
            f"👤 Your Profile\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 User ID: {user_id}\n"
            f"💰 Balance: ₹{balance}\n"
            f"⭐ Reseller: {reseller_status}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

# ================= BOT INITIALIZATION =================
def main():
    # 1. Initialize Database
    init_db()
    logger.info("Database initialized successfully.")
    
    # 2. Start Flask Server in background thread (For Render Web Service)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    logger.info(f"Dummy web server started on port {PORT}.")

    # 3. Initialize Telegram Bot
    application = Application.builder().token(TOKEN).build()
    
    # Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # 4. Start Polling
    logger.info("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if name == 'main':
    main()
