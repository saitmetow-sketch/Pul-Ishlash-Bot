import logging, sqlite3, os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# --- SOZLAMALAR ---
API_TOKEN = os.getenv('API_TOKEN') 
ADMIN_ID = 8588301820       
BONUS_AMOUNT = 3000

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AdminState(StatesGroup):
    broadcast = State()
    set_channel = State()

# --- BAZA BILAN ISHLASH ---
def db_start():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            balance REAL DEFAULT 0, 
            referrals INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def set_setting(key, value):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance, referrals FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_balance(referrer_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE user_id = ?', (BONUS_AMOUNT, referrer_id))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    conn.close()
    return total_users

# --- OBUNANI TEKSHIRISH ---
async def check_sub(user_id):
    channel = get_setting('channel_id')
    if not channel:
        return True 
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'creator', 'administrator', 'restricted']
    except:
        return False

# --- START ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    db_start()
    user_id = message.from_user.id
    add_user(user_id)
    args = message.get_args()
    
    if args and args.isdigit() and int(args) != user_id:
        update_balance(int(args))
        try:
            await bot.send_message(int(args), f"🎉 Yangi do'stingiz qo'shildi! Hisobingizga {BONUS_AMOUNT} so'm qo'shildi.")
        except:
            pass

    if not await check_sub(user_id):
        channel_link = get_setting('channel_link') or 'https://t.me/'
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Kanalga obuna bo'lish 🔔", url=channel_link))
        markup.add(types.InlineKeyboardButton("Tekshirish ✅", callback_data='check_sub'))
        await message.answer("Botdan foydalanish uchun avval quyidagi kanalimizga obuna bo'ling:", reply_markup=markup)
    else:
        await main_menu(message)

async def main_menu(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('💰 Pul ishlash', '👤 Profil')
    markup.row('📞 Admin bilan bog\'lanish')
    if message.from_user.id == ADMIN_ID:
        markup.row('🛠 Admin Panel')
    await message.answer("Asosiy menyu:", reply_markup=markup)

@dp.callback_query_handler(text='check_sub')
async def cb_check_sub(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await main_menu(call.message)
    else:
        await call.answer("Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

# --- MENYU TUGMALARI ---
@dp.message_handler(text='💰 Pul ishlash')
async def earn_money(message: types.Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(
        f"💰 **Pul ishlash bo'limi**\n\n"
        f"Do'stlaringizni taklif qiling va har bir taklif uchun **{BONUS_AMOUNT} so'm** oling!\n\n"
        f"🔗 Sizning referal havolangiz:\n{ref_link}"
    )

@dp.message_handler(text='👤 Profil')
async def profile(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if user_data:
        balance, referrals = user_data[0], user_data[1]
        await message.answer(
            f"👤 **Sizning profilingiz:**\n\n"
            f"🆔 ID raqamingiz: `{user_id}`\n"
            f"💳 Balansingiz: {balance} so'm\n"
            f"👥 Taklif qilganlaringiz: {referrals} ta",
            parse_mode="Markdown"
        )

# --- ADMIN PANEL ---
@dp.message_handler(text='🛠 Admin Panel')
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📊 Statistika', '📢 Xabar yuborish (Rassilka)')
    markup.row('⚙️ Kanalni sozlash', '🔙 Asosiy menyu')
    await message.answer("🛠 Admin panelga xush kelibsiz:", reply_markup=markup)

@dp.message_handler(text='🔙 Asosiy menyu')
async def back_to_main(message: types.Message):
    await main_menu(message)

@dp.message_handler(text='📊 Statistika')
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total = get_stats()
    await message.answer(f"📊 **Statistika:**\n\n👥 Jami foydalanuvchilar: {total} ta")

@dp.message_handler(text='📢 Xabar yuborish (Rassilka)')
async def admin_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring (matn, rasm yoki video):")
    await AdminState.broadcast.set()

@dp.message_handler(state=AdminState.broadcast, content_types=types.ContentTypes.ANY)
async def send_broadcast(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()

    success = 0
    for row in users:
        try:
            await message.send_copy(chat_id=row[0])
            success += 1
        except:
            pass

    await message.answer(f"✅ Xabar {success} ta foydalanuvchiga yuborildi!")
    await state.finish()
    await admin_panel(message)

@dp.message_handler(text='⚙️ Kanalni sozlash')
async def admin_set_channel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "Kanalni sozlash uchun quyidagi formatda yuboring:\n\n"
        "`Kanal_ID | Kanal_Havolasi`\n\n"
        "Masalan: `-100123456789 | https://t.me/kanal_nomi`",
        parse_mode="Markdown"
    )
    await AdminState.set_channel.set()

@dp.message_handler(state=AdminState.set_channel)
async def save_channel(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split('|')
        ch_id = parts[0].strip()
        ch_link = parts[1].strip()
        
        set_setting('channel_id', ch_id)
        set_setting('channel_link', ch_link)
        
        await message.answer("✅ Kanal muvaffaqiyatli saqlandi va majburiy obuna yoqildi!")
    except:
        await message.answer("❌ Xato format! Qaytadan urinib ko'ring (Masalan: `-100123 | https://t.me/kanal`)")
    
    await state.finish()
    await admin_panel(message)

if __name__ == '__main__':
    db_start()
    executor.start_polling(dp, skip_updates=True)
