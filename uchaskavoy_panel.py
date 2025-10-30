from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
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

contact_location_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)


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
        kb.button(text=f"👤 {user_id[0]}", callback_data=f"toggle_status:{user_id[1]}")

    await callback.message.answer("Murojaat yuborganlar:", reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data.startswith("toggle_status:"))
async def toggle_murojaat_status(callback: types.CallbackQuery):
    import sqlite3
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from database import DB_NAME

    foydalanuvchi_id = int(callback.data.split(":")[1])

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 🔹 1. Murojaat ma’lumotlarini olish
    c.execute("""
              SELECT id, foydalanuvchi_id, turi, content, holat, telefon, location
              FROM murojaatlar
              WHERE foydalanuvchi_id = ?
              """, (foydalanuvchi_id,))
    row = c.fetchone()
    print(row)

    if not row:
        await callback.answer("❌ Murojaat topilmadi.")
        conn.close()
        return

    murojaat_id, foydalanuvchi_id, turi, content, holat, telefon, location = row

    # 🔹 2. Foydalanuvchining FIO sini uchaskavoy jadvalidan olish
    c.execute("SELECT fio FROM uchaskavoy WHERE tg_id = ?", (foydalanuvchi_id,))
    user_row = c.fetchone()
    fio = user_row[0] if user_row else "Noma’lum fuqaro"

    # 🔹 3. Holatni o‘zgartirish
    yangi_holat = "bajarildi" if holat == "kutilmoqda" else "kutilmoqda"
    c.execute("UPDATE murojaatlar SET holat = ? WHERE id = ?", (yangi_holat, murojaat_id))
    conn.commit()
    conn.close()

    # 🔹 4. Tugmalar
    button_text = "🕓 Kutilmoqda" if yangi_holat == "bajarildi" else "✅ Bajarildi"
    holat_emoji = "✅" if yangi_holat == "bajarildi" else "🕓"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=button_text, callback_data=f"toggle_status:{foydalanuvchi_id}")]
        ]
    )

    # 🔹 5. Qo‘shimcha ma’lumotlar (telefon, lokatsiya)
    info_text = f"<b>👤 F.I.Sh.:</b> {fio}\n"
    if telefon:
        info_text += f"<b>📞 Telefon:</b> <a href='tel:{telefon}'>{telefon}</a>\n"
    if location:
        try:
            lat, lon = location.split(",")
            info_text += f"<b>📍 Joylashuv:</b> <a href='https://maps.google.com/?q={lat},{lon}'>Ko‘rish</a>\n"
        except:
            pass

    info_text += f"\n<b>{holat_emoji} Holat:</b> <i>{yangi_holat.capitalize()}</i>\n───────────────"

    # 🔹 6. Turi bo‘yicha xabarni yangilash
    try:
        if turi == "text":
            await callback.message.edit_text(
                f"📝 <b>Matnli murojaat:</b>\n\n{content}\n\n{info_text}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif turi == "photo":
            await callback.message.edit_caption(
                caption=f"📸 <b>Rasmli murojaat</b>\n\n{info_text}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif turi == "video":
            await callback.message.edit_caption(
                caption=f"🎥 <b>Videomurojaat</b>\n\n{info_text}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif turi == "document":
            await callback.message.edit_caption(
                caption=f"📄 <b>Fayl murojaat</b>\n\n{info_text}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif turi == "voice":
            await callback.message.edit_caption(
                caption=f"🎙 <b>Ovozli murojaat</b>\n\n{info_text}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception:
        # Agar edit_caption ishlamasa (masalan, eski xabar bo‘lsa)
        await callback.message.answer(
            f"🔄 <b>Yangilangan murojaat</b>\n\n{info_text}",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    await callback.answer(f"✅ Holat '{yangi_holat}' deb o‘zgartirildi.")

# @router.callback_query(lambda c: c.data.startswith("user_murojaat:"))
# async def show_user_murojaatlar(callback: types.CallbackQuery):
#     uchaskavoy = get_uchaskavoy_by_tg_id(callback.from_user.id)
#     if not uchaskavoy:
#         await callback.answer("❌ Siz profilaktika inspektori emassiz", show_alert=True)
#         return
#
#     user_id = int(callback.data.split(":")[1])
#
#     # 🧩 1. Foydalanuvchi ma’lumotlarini olish
#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute("""
#               SELECT fio, telefon, lat, lon
#               FROM uchaskavoy
#               WHERE id = ?
#               """, (user_id,))
#     user_info = c.fetchone()
#     conn.close()
#
#     if not user_info:
#         await callback.message.answer("Fuqaro ma’lumotlari topilmadi.")
#         return
#
#     fio, telefon, lat, lon = user_info
#
#     # 🧩 2. Foydalanuvchining murojaatlarini olish
#     murojaatlar = get_murojaatlar_by_user(user_id, uchaskavoy[0])
#     if not murojaatlar:
#         await callback.message.answer(f"👤 {fio} tomonidan hali murojaatlar yo‘q.")
#         return
#
#     # 🧩 3. Har bir murojaatni yuborish
#     for murojaat_id, content_type, content, holat in murojaatlar:
#         if holat == "kutilmoqda":
#             button_text = "✅ Bajarildi"
#             new_status = "bajarildi"
#             holat_emoji = "🕓"
#         else:
#             button_text = "🕓 Kutilmoqda"
#             new_status = "kutilmoqda"
#             holat_emoji = "✅"
#
#         markup = InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text=button_text, callback_data=f"toggle_status:{murojaat_id}:{new_status}")]
#         ])
#
#         # 📋 Foydalanuvchi haqida ma’lumotlar
#         info_text = (
#             f"<b>👤 F.I.Sh.:</b> {fio}\n"
#             f"<b>📞 Telefon:</b> <a href='tel:{telefon}'>{telefon}</a>\n"
#             f"<b>📍 Joylashuv:</b> {lat}, {lon}\n\n"
#             f"<b>{holat_emoji} Holat:</b> <i>{holat.capitalize()}</i>\n"
#             f"────────────────────"
#         )
#
#         # 📦 Kontent turiga qarab yuborish
#         if content_type == "text":
#             await callback.message.answer(
#                 f"📝 <b>Matnli murojaat:</b>\n\n{content}\n\n{info_text}",
#                 parse_mode="HTML",
#                 disable_web_page_preview=True,
#                 reply_markup=markup
#             )
#
#         elif content_type == "photo":
#             await callback.message.answer_photo(
#                 photo=content,
#                 caption=f"📸 <b>Rasmli murojaat</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=markup
#             )
#
#         elif content_type == "video":
#             await callback.message.answer_video(
#                 video=content,
#                 caption=f"🎥 <b>Videomurojaat</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=markup
#             )
#
#         elif content_type == "document":
#             await callback.message.answer_document(
#                 document=content,
#                 caption=f"📄 <b>Fayl murojaat</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=markup
#             )
#
#         elif content_type == "voice":
#             await callback.message.answer_voice(
#                 voice=content,
#                 caption=f"🎙 <b>Ovozli murojaat</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=markup
#             )
#
#         elif content_type == "location":
#             lat2, lon2 = map(float, content.split(","))
#             await callback.message.answer_location(latitude=lat2, longitude=lon2)
#             await callback.message.answer(
#                 f"📍 <b>Joylashuv yuborildi</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=markup
#             )
