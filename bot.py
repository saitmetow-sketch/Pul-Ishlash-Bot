import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === SOZLAMALAR ===
# Token Render muhitidan (Environment Variables) olinadi
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8588301820  # Sizning ID raqamingiz

if not BOT_TOKEN:
    raise ValueError("Xatolik: BOT_TOKEN topilmadi! Render'da Environment Variables ga BOT_TOKEN qo'shing.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Bazalar
users_db = {}     # Foydalanuvchilar balansini saqlash
channels_db = []  # Majburiy obuna kanallari

class AdminStates(StatesGroup):
    waiting_for_channel = State()

# === FUNKSIYALAR ===
async def check_subscriptions(user_id: int) -> bool:
    """Majburiy obunani tekshirish"""
    for channel in channels_db:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

# === MENYU VA KOMANDALAR ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {"balance": 0.0}

    if not await check_subscriptions(user_id):
        buttons = [[InlineKeyboardButton(text="📢 Obuna bo'lish", url=f"https://t.me/{ch.replace('@', '')}")] for ch in channels_db]
        buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
        await message.answer("⚠️ Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return
    await show_menu(message)

async def show_menu(message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Pul ishlash", callback_data="earn"), InlineKeyboardButton(text="📤 Pul chiqarish", callback_data="withdraw")],
        [InlineKeyboardButton(text="👤 Kabinet", callback_data="cabinet"), InlineKeyboardButton(text="👨‍💻 Adminga murojaat", callback_data="contact")]
    ])
    if message.from_user.id == ADMIN_ID:
        markup.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin")])
    
    text = f"Xush kelibsiz!\nID: {message.from_user.id}\nBalans: {users_db.get(message.from_user.id, {}).get('balance', 0.0)} so'm"
    if isinstance(message, types.CallbackQuery): await message.message.edit_text(text, reply_markup=markup)
    else: await message.answer(text, reply_markup=markup)

# === CALLBACKS (Tugmalar) ===
@dp.callback_query(F.data == "check_sub")
async def check_sub_cb(cb: types.CallbackQuery):
    if await check_subscriptions(cb.from_user.id): await show_menu(cb)
    else: await cb.answer("Siz hali obuna bo'lmadingiz!", show_alert=True)

@dp.callback_query(F.data == "admin")
async def admin_panel(cb: types.CallbackQuery):
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_ch"), InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")]])
    await cb.message.edit_text(f"Admin panel. Jami foydalanuvchi: {len(users_db)}", reply_markup=markup)

@dp.callback_query(F.data == "add_ch")
async def add_ch(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("Kanal username'sini yuboring (@bilan):")
    await state.set_state(AdminStates.waiting_for_channel)

@dp.message(AdminStates.waiting_for_channel)
async def save_ch(msg: types.Message, state: FSMContext):
    channels_db.append(msg.text)
    await state.clear()
    await msg.answer("✅ Kanal qo'shildi!")

# === BOTNI UYG'OQ SAQLASH (KEEP-ALIVE) ===
async def web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot ishlayapti!"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()

async def main():
    asyncio.create_task(web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
