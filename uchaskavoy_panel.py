from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from admin_panel import manage_panel
from database import (
    get_uchaskavoy_by_tg_id,
    get_murojaatlar_by_uchaskavoy,
    get_murojaatlar_by_user,
    get_user_role, DB_NAME
)
from fuqarolik_panel import cmd_start
import sqlite3

router = Router()


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

        await message.answer(
            f"Assalomu alaykum, <b>{uchaskavoy[1]}</b>!\n"
            f"Siz <b>{uchaskavoy[3]}</b> mahallasi profilaktika inspektori ekansiz.",
            reply_markup=kb.as_markup()
        )

    elif role == "admin":
        await manage_panel(message)


    elif role == "fuqaro":
        await cmd_start(message, state)


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
        kb.button(text=f"👤 {user_id[0]}", callback_data=f"user_murojaat:{user_id[1]}")

    await callback.message.answer("Murojaat yuborganlar:", reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data.startswith("user_murojaat:"))
async def show_user_murojaatlar(callback: types.CallbackQuery):
    uchaskavoy = get_uchaskavoy_by_tg_id(callback.from_user.id)
    if not uchaskavoy:
        await callback.answer("❌ Siz profilaktika inspektori", show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    murojaatlar = get_murojaatlar_by_user(user_id, uchaskavoy[0])

    if not murojaatlar:
        await callback.message.answer("ℹ️ Bu foydalanuvchidan hali murojaatlar yo‘q.")
        return

    for murojaat_id, content_type, content, holat in murojaatlar:
        # 🔘 Tugmani holatga qarab tayyorlaymiz
        if holat == "kutilmoqda":
            button_text = "✅ Bajarildi"
            new_status = "bajarildi"
            holat_emoji = "🕓"
        else:
            button_text = "🕓 Kutilmoqda"
            new_status = "kutilmoqda"
            holat_emoji = "✅"

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, callback_data=f"toggle_status:{murojaat_id}:{new_status}")]
        ])

        caption_text = (
            f"<b>{holat_emoji} Holat:</b> <i>{holat.capitalize()}</i>\n"
        )

        # Xabarni turi bo‘yicha yuboramiz
        if content_type == "text":
            await callback.message.answer(
                f"📝 <b>Matnli murojaat:</b>\n\n{content}\n\n{caption_text}",
                parse_mode="HTML",
                reply_markup=markup
            )

        elif content_type == "photo":
            await callback.message.answer_photo(
                photo=content,
                caption=f"📸 <b>Rasmli murojaat</b>\n\n{caption_text}",
                parse_mode="HTML",
                reply_markup=markup
            )

        elif content_type == "video":
            await callback.message.answer_video(
                video=content,
                caption=f"🎥 <b>Video murojaat</b>\n\n{caption_text}",
                parse_mode="HTML",
                reply_markup=markup
            )

        elif content_type == "document":
            await callback.message.answer_document(
                document=content,
                caption=f"📄 <b>Fayl murojaat</b>\n\n{caption_text}",
                parse_mode="HTML",
                reply_markup=markup
            )

        elif content_type == "voice":
            await callback.message.answer_voice(
                voice=content,
                caption=f"🎙 <b>Ovozli murojaat</b>\n\n{caption_text}",
                parse_mode="HTML",
                reply_markup=markup
            )

        elif content_type == "location":
            lat, lon = map(float, content.split(","))
            await callback.message.answer_location(latitude=lat, longitude=lon)
            await callback.message.answer(
                f"📍 <b>Joylashuv yuborildi</b>\n\n{caption_text}",
                parse_mode="HTML",
                reply_markup=markup
            )


@router.callback_query(lambda c: c.data.startswith("toggle_status:"))
async def toggle_murojaat_status(callback: types.CallbackQuery):
    murojaat_id = int(callback.data.split(":")[1])

    # 🔍 Ma’lumotni olish
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT content, turi, holat FROM murojaatlar WHERE id = ?", (murojaat_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        await callback.answer("❌ Murojaat topilmadi.")
        return

    content, turi, holat = row
    yangi_holat = "bajarildi" if holat == "kutilmoqda" else "kutilmoqda"

    # 🔄 Bazani yangilash
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE murojaatlar SET holat = ? WHERE id = ?", (yangi_holat, murojaat_id))
    conn.commit()
    conn.close()

    # 🔘 Tugma va holat belgisi
    button_text = "🕓 Kutilmoqda" if yangi_holat == "bajarildi" else "✅ Bajarildi"
    holat_emoji = "✅" if yangi_holat == "bajarildi" else "🕓"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=button_text, callback_data=f"toggle_status:{murojaat_id}")]
        ]
    )

    # 🔹 Matn / caption yangilash
    caption_text = f"{holat_emoji} <b>Holat:</b> <i>{yangi_holat.capitalize()}</i>"

    try:
        if turi == "text":
            await callback.message.edit_text(
                f"📝 <b>Matnli murojaat:</b>\n\n{content}\n\n{caption_text}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_caption(
                caption=caption_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception:
        # Ba’zan caption bo‘lmagan holatlarda xato bo‘lishi mumkin
        await callback.answer("🔄 Holat yangilandi (ko‘rinish avtomatik o‘zgartirildi).")

    await callback.answer(f"✅ Holat '{yangi_holat}' deb o‘zgartirildi.")