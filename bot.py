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
    add_channel = State()
    del_channel = State()
    check_user = State()
    add_admin = State()

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
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_link TEXT,
            channel_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()
    
    # Asosiy adminni bazaga qo'shib qo'yamiz
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO admins (admin_id) VALUES (?)', (ADMIN_ID,))
    conn.commit()
    conn.close()

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT admin_id FROM admins WHERE admin_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

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

def get_channels():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id, channel_link, channel_name FROM channels')
    channels = cursor.fetchall()
    conn.close()
    return channels

# --- OBUNANI TEKSHIRISH ---
async def check_sub_all(user_id):
    channels = get_channels()
    not_subscribed = []
    for ch_id, ch_link, ch_name in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status not in ['member', 'creator', 'administrator', 'restricted']:
                not_subscribed.append((ch_name, ch_link))
        except:
            not_subscribed.append((ch_name, ch_link))
    return not_subscribed

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
            await bot.send_message(int(args), f"🎉 Yangi do'stingiz obuna bo'ldi! Hisobingizga {BONUS_AMOUNT} so'm qo'shildi.")
        except:
            pass

    not_sub = await check_sub_all(user_id)
    if not_sub:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for name, link in not_sub:
            markup.add(types.InlineKeyboardButton(f"🔔 {name}", url=link))
        markup.add(types.InlineKeyboardButton("✅ Obunani tekshirish", callback_data='check_sub'))
        await message.answer("Botdan foydalanish uchun quyidagi barcha kanallarga obuna bo'ling:", reply_markup=markup)
    else:
        await main_menu(message)

async def main_menu(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('💰 Pul ishlash', '👤 Profil')
    markup.row('📞 Admin bilan bog\'lanish')
    if is_admin(message.from_user.id):
        markup.row('⚙️ Admin Panel')
    await message.answer("Asosiy menyu:", reply_markup=markup)

@dp.callback_query_handler(text='check_sub')
async def cb_check_sub(call: types.CallbackQuery):
    not_sub = await check_sub_all(call.from_user.id)
    if not not_sub:
        await call.message.delete()
        await main_menu(call.message)
    else:
        await call.answer("Siz hali hamma kanalga obuna bo'lmadingiz!", show_alert=True)

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

@dp.message_handler(text='📞 Admin bilan bog\'lanish')
async def contact_admin(message: types.Message):
    await message.answer("Admin uchun yubormoqchi bo'lgan xabaringizni yozing:")
    await UserState.waiting_for_message.set()

class UserState(StatesGroup):
    waiting_for_message = State()

@dp.message_handler(state=UserState.waiting_for_message)
async def send_message_to_admin(message: types.Message, state: FSMContext):
    user = message.from_user
    username_text = f"@{user.username}" if user.username else "Username yo'q"
    
    await bot.send_message(
        ADMIN_ID,
        f"📩 **Yangi xabar!**\n\n"
        f"Foydalanuvchi: {user.full_name} ({username_text})\n"
        f"ID: `{user.id}`\n\n"
        f"Xabar: {message.text}"
    )
    await message.answer("Xabaringiz adminga muvaffaqiyatli yuborildi!")
    await state.finish()

# --- ADMIN PANEL ---
@dp.message_handler(text='⚙️ Admin Panel')
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    channels_count = len(get_channels())
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📢 Kanal qo\'shish', '❌ Kanal o\'chirish')
    markup.row('📋 Kanallar ro\'yxati', '📊 Statistika')
    markup.row('📢 Xabar yuborish', '👤 User balansini ko\'rish')
    markup.row('👥 Admin qo\'shish', '🏠 Bosh sahifa')
    await message.answer(f"⚙️ **Admin panel**\n🔊 Kanallar soni: {channels_count} ta", reply_markup=markup)

@dp.message_handler(text='🏠 Bosh sahifa')
async def back_to_main(message: types.Message):
    await main_menu(message)

@dp.message_handler(text='📊 Statistika')
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    conn.close()
    await message.answer(f"📊 **Statistika:**\n\n👥 Jami foydalanuvchilar: {total} ta")

@dp.message_handler(text='📢 Kanal qo\'shish')
async def admin_add_channel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Kanal qo'shish uchun quyidagi formatda yuboring:\n\n"
        "`Kanal_ID | Kanal_Havolasi | Kanal_Nomi`\n\n"
        "Masalan: `-100123456789 | https://t.me/kanal | Yangiliklar`",
        parse_mode="Markdown"
    )
    await AdminState.add_channel.set()

@dp.message_handler(state=AdminState.add_channel)
async def save_new_channel(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split('|')
        ch_id = parts[0].strip()
        ch_link = parts[1].strip()
        ch_name = parts[2].strip()
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO channels (channel_id, channel_link, channel_name) VALUES (?, ?, ?)', (ch_id, ch_link, ch_name))
        conn.commit()
        conn.close()
        
        await message.answer("✅ Kanal muvaffaqiyatli qo'shildi!")
    except:
        await message.answer("❌ Xato format! Qaytadan urinib ko'ring.")
    
    await state.finish()
    await admin_panel(message)

@dp.message_handler(text='📋 Kanallar ro\'yxati')
async def admin_list_channels(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    channels = get_channels()
    if not channels:
        await message.answer("📭 Hozircha kanallar ulanmagan.")
        return
    
    text = "📋 **Ulangan kanallar:**\n\n"
    for ch_id, ch_link, ch_name in channels:
        text += f"📌 {ch_name}\n🔗 {ch_link}\n🆔 `{ch_id}`\n\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message_handler(text='❌ Kanal o\'chirish')
async def admin_del_channel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("O'chirmoqchi bo'lgan kanalning **Kanal_ID** raqamini yuboring (Masalan: `-100123456789`):")
    await AdminState.del_channel.set()

@dp.message_handler(state=AdminState.del_channel)
async def remove_channel(message: types.Message, state: FSMContext):
    ch_id = message.text.strip()
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE channel_id = ?', (ch_id,))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Kanal ro'yxatdan o'chirildi!")
    await state.finish()
    await admin_panel(message)

@dp.message_handler(text='📢 Xabar yuborish')
async def admin_broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:")
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

@dp.message_handler(text='👤 User balansini ko\'rish')
async def admin_check_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Foydalanuvchining **Telegram ID** raqamini yuboring:")
    await AdminState.check_user.set()

@dp.message_handler(state=AdminState.check_user)
async def show_user_info(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    target_id = int(message.text)
    user_data = get_user(target_id)
    if user_data:
        await message.answer(f"👤 ID: `{target_id}`\n💳 Balans: {user_data[0]} so'm\n👥 Takliflar: {user_data[1]} ta", parse_mode="Markdown")
    else:
        await message.answer("❌ Topilmadi.")
    await state.finish()
    await admin_panel(message)

@dp.message_handler(text='👥 Admin qo\'shish')
async def admin_add_new(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Bu amalni faqat asosiy admin bajara oladi!")
        return
    await message.answer("Yangi adminning Telegram ID raqamini yuboring:")
    await AdminState.add_admin.set()

@dp.message_handler(state=AdminState.add_admin)
async def save_new_admin(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    new_admin_id = int(message.text)
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO admins (admin_id) VALUES (?)', (new_admin_id,))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ ID `{new_admin_id}` bo'lgan foydalanuvchi admin qilindi!", parse_mode="Markdown")
    await state.finish()
    await admin_panel(message)

if __name__ == '__main__':
    db_start()
    executor.start_polling(dp, skip_updates=True)
