import aiosqlite

DB_NAME = "premium_store.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, 
            is_reseller BOOLEAN DEFAULT 0, banned BOOLEAN DEFAULT 0)""")
        
        # Stock table updated with API details
        await db.execute("""CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            category TEXT, 
            phone_number TEXT,
            api_id TEXT, 
            api_hash TEXT, 
            price INTEGER)""")
            
        await db.execute("""CREATE TABLE IF NOT EXISTS deposits (
            utr TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, status TEXT)""")
        await db.commit()

async def add_stock_db(category, phone, api_id, api_hash, price):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO stock (category, phone_number, api_id, api_hash, price) VALUES (?, ?, ?, ?, ?)", 
                         (category, phone, api_id, api_hash, price))
        await db.commit()

async def get_all_stock():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, category, price FROM stock") as c:
            return await c.fetchall()

async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()
