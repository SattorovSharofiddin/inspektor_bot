from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from admin_panel import manage_panel
from database import (
    get_uchaskavoy_by_tg_id,
    get_murojaatlar_by_uchaskavoy,
    get_murojaatlar_by_user,
    get_user_role, DB_NAME, add_murojaat, get_fuqarolar_by_uchaskavoy
)
from fuqarolik_panel import cmd_start
import sqlite3

router = Router()

contact_location_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)


class UchaskavoySendMessage(StatesGroup):
    waiting_content = State()


class UchaskavoyReply(StatesGroup):
    waiting_reply = State()


@router.message(Command("start"))
async def user_start(message: types.Message, state: FSMContext):
    role = get_user_role(message.from_user.id)

    if role == "uchaskavoy":
        uchaskavoy = get_uchaskavoy_by_tg_id(message.from_user.id)
        if not uchaskavoy:
            await message.answer("Siz profilaktika inspektori sifatida ro'yxatdan o'tmagansiz.")
            return

        kb = InlineKeyboardBuilder()
        kb.button(text="📩 Murojaatlar", callback_data="show_murojaatlar")
        kb.button(text="📝 Xabar yuborish", callback_data="send_message")  # <-- Yangi tugma

        await message.answer(
            f"Assalomu alaykum, <b>{uchaskavoy[1]}</b>!\n"
            f"Siz <b>{uchaskavoy[3]}</b> mahallasi profilaktika inspektori ekansiz.",
            reply_markup=kb.as_markup()
        )

    elif role == "admin":
        await manage_panel(message)

    elif role == "fuqaro":
        await cmd_start(message, state)


@router.callback_query(lambda c: c.data == "send_message")
async def send_message_start(callback: types.CallbackQuery, state: FSMContext):
    uchaskavoy = get_uchaskavoy_by_tg_id(callback.from_user.id)
    if not uchaskavoy:
        await callback.answer("❌ Siz uchaskavoy sifatida ro'yxatdan o'tmagansiz.", show_alert=True)
        return

    await callback.message.answer(
        "📨 Yubormoqchi bo‘lgan xabaringizni yuboring.\n"
        "Matn, rasm, video, audio yoki hujjat yuborishingiz mumkin."
    )
    await state.set_state(UchaskavoySendMessage.waiting_content)
    await callback.answer()


# 🔹 FSM: Xabarni qabul qilish va barcha fuqarolarga yuborish
@router.message(StateFilter(UchaskavoySendMessage.waiting_content))
async def process_message(message: Message, state: FSMContext):
    uchaskavoy = get_uchaskavoy_by_tg_id(message.from_user.id)
    if not uchaskavoy:
        await message.answer("❌ Xatolik yuz berdi.")
        await state.clear()
        return

    fuqarolar = get_fuqarolar_by_uchaskavoy(uchaskavoy[0])
    if not fuqarolar:
        await message.answer("❌ Ushbu mahallada fuqaro topilmadi.")
        await state.clear()
        return

    # 🔹 Xabar turi va kontent aniqlash
    if message.text:
        turi, content = "text", message.text
    elif message.photo:
        turi, content = "photo", message.photo[-1].file_id
    elif message.video:
        turi, content = "video", message.video.file_id
    elif message.document:
        turi, content = "document", message.document.file_id
    elif message.voice:
        turi, content = "voice", message.voice.file_id
    else:
        await message.answer("⚠️ Ushbu turdagi faylni qabul qilib bo‘lmaydi.")
        return

    sent_count = 0
    for f in fuqarolar:
        id = f[0]  # fuqaroning tg_id
        fio = f[1]  # fuqaroning FIO
        tg_id = f[2]
        try:
            if turi == "text":
                await message.bot.send_message(chat_id=tg_id, text=f"📢 Uchaskavoydan xabar:\n\n{content}")
            elif turi == "photo":
                await message.bot.send_photo(chat_id=tg_id, photo=content, caption="📢 Uchaskavoydan xabar")
            elif turi == "video":
                await message.bot.send_video(chat_id=tg_id, video=content, caption="📢 Uchaskavoydan xabar")
            elif turi == "document":
                await message.bot.send_document(chat_id=tg_id, document=content, caption="📢 Uchaskavoydan xabar")
            elif turi == "voice":
                await message.bot.send_voice(chat_id=tg_id, voice=content, caption="📢 Uchaskavoydan xabar")
            sent_count += 1
        except Exception as e:
            print(f"Xabar yuborilmadi {tg_id}: {e}")
            continue

        # 🔹 Bazaga yozish
        add_murojaat(
            foydalanuvchi_id=tg_id,
            foydalanuvchi_nick=fio,
            uchaskavoy_id=uchaskavoy[0],
            turi=turi,
            content=content
        )

    await message.answer(f"✅ Xabar {sent_count} fuqaro/guruhga yuborildi")
    await state.clear()


@router.callback_query(lambda c: c.data == "show_murojaatlar")
async def show_murojaatlar(callback: types.CallbackQuery):
    uchaskavoy = get_uchaskavoy_by_tg_id(callback.from_user.id)
    if not uchaskavoy:
        await callback.answer("Siz profilaktika inspektori emassiz ❌", show_alert=True)
        return

    data = get_murojaatlar_by_uchaskavoy(uchaskavoy[0])
    if not data:
        await callback.message.answer("Hozircha hech kim murojaat yubormagan.")
        return

    kb = InlineKeyboardBuilder()
    for user_id in data:
        kb.button(text=f"👤 {user_id[0]}", callback_data=f"toggle_status:{user_id[1]}")

    await callback.message.answer("Murojaat yuborganlar:", reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data.startswith("reply_to:"))
async def reply_to_message(callback: types.CallbackQuery, state: FSMContext):
    murojaat_id = int(callback.data.split(":")[1])
    await state.update_data(murojaat_id=murojaat_id)
    await callback.message.answer(
        "✉️ Iltimos, murojaatchiga yubormoqchi bo‘lgan javobingizni kiriting.\n"
        "Matn, rasm, video, audio yoki hujjat yuborishingiz mumkin."
    )
    # ❌ await UchaskavoyReply.waiting_reply.set()
    await state.set_state(UchaskavoyReply.waiting_reply)  # ✅ Shu tarzda
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("toggle_status:"))
async def toggle_murojaat_status(callback: types.CallbackQuery):
    foydalanuvchi_id = int(callback.data.split(":")[1])

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
              SELECT id, foydalanuvchi_id, turi, content, holat, telefon, location
              FROM murojaatlar
              WHERE foydalanuvchi_id = ?
              """, (foydalanuvchi_id,))
    row = c.fetchone()

    if not row:
        await callback.answer("❌ Murojaat topilmadi.")
        conn.close()
        return

    murojaat_id, foydalanuvchi_id, turi, content, holat, telefon, location = row

    # 🔹 Holatni o‘zgartirish
    yangi_holat = "bajarildi" if holat == "kutilmoqda" else "kutilmoqda"
    c.execute("UPDATE murojaatlar SET holat = ? WHERE id = ?", (yangi_holat, murojaat_id))
    conn.commit()
    conn.close()

    # 🔹 Tugmalar: holat + javob berish
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🕓 Kutilmoqda" if yangi_holat == "bajarildi" else "✅ Bajarildi",
                callback_data=f"toggle_status:{foydalanuvchi_id}"
            )],
            [InlineKeyboardButton(
                text="💬 Javob berish",
                callback_data=f"reply_to:{murojaat_id}"
            )]
        ]
    )

    info_text = f"<b>Holat:</b> {yangi_holat.capitalize()}"
    try:
        if turi == "text":
            await callback.message.edit_text(
                f"📝 Murojaat:\n\n{content}\n\n{info_text}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_caption(
                caption=f"{info_text}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception:
        await callback.message.answer(f"🔄 Yangilangan murojaat\n\n{info_text}", reply_markup=keyboard)

    await callback.answer(f"✅ Holat '{yangi_holat}' deb o‘zgartirildi.")


@router.message(StateFilter(UchaskavoyReply.waiting_reply))
async def process_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    murojaat_id = data.get("murojaat_id")
    if not murojaat_id:
        await message.answer("❌ Murojaat topilmadi.")
        await state.clear()
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT foydalanuvchi_id FROM murojaatlar WHERE id = ?", (murojaat_id,))
    row = c.fetchone()
    if not row:
        await message.answer("❌ Murojaatchi topilmadi.")
        conn.close()
        await state.clear()
        return

    foydalanuvchi_id = row[0]

    # 🔹 Javobni yuborish
    try:
        if message.text:
            await message.bot.send_message(foydalanuvchi_id, f"💬 Uchaskavoy javobi:\n\n{message.text}")
        elif message.photo:
            await message.bot.send_photo(foydalanuvchi_id, message.photo[-1].file_id,
                                         caption=message.caption or "💬 Uchaskavoy javobi")
        elif message.video:
            await message.bot.send_video(foydalanuvchi_id, message.video.file_id,
                                         caption=message.caption or "💬 Uchaskavoy javobi")
        elif message.document:
            await message.bot.send_document(foydalanuvchi_id, message.document.file_id,
                                            caption=message.caption or "💬 Uchaskavoy javobi")
        elif message.voice:
            await message.bot.send_voice(foydalanuvchi_id, message.voice.file_id,
                                         caption=message.caption or "💬 Uchaskavoy javobi")
        elif message.location:
            await message.bot.send_location(foydalanuvchi_id, message.location.latitude, message.location.longitude)
    except Exception as e:
        await message.answer(f"❌ Javob yuborishda xatolik yuz berdi: {e}")

    await message.answer("✅ Javob muvaffaqiyatli yuborildi.")
    await state.clear()
