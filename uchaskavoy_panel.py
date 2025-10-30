from aiogram import Router, types
from aiogram.filters import Command, StateFilter, CommandStart
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

uchaskavoy_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📩 Murojaatlar"),
            KeyboardButton(text="📝 Xabar yuborish")
        ],
        [
            KeyboardButton(text="🔄 Yangilash")
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Kerakli bo‘limni tanlang..."
)


class UchaskavoySendMessage(StatesGroup):
    waiting_content = State()


class UchaskavoyReply(StatesGroup):
    waiting_reply = State()


# === 🟢 START buyrug'i ===
@router.message(CommandStart())
async def user_start(message: types.Message, state: FSMContext):
    role = get_user_role(message.from_user.id)

    if role == "uchaskavoy":
        uchaskavoy = get_uchaskavoy_by_tg_id(message.from_user.id)
        if not uchaskavoy:
            await message.answer("❌ Siz uchaskavoy sifatida ro‘yxatdan o‘tmagansiz.")
            return

        await message.answer(
            f"👮‍♂️ Assalomu alaykum, <b>{uchaskavoy[1]}</b>!\n"
            f"Siz <b>{uchaskavoy[3]}</b> mahallasi profilaktika inspektorisiz.",
            reply_markup=uchaskavoy_menu,
            parse_mode="HTML"
        )

    elif role == "admin":
        await manage_panel(message)

    elif role == "fuqaro":
        await cmd_start(message, state)


# 🔹 Yangilash tugmasi
@router.message(lambda message: message.text == "🔄 Yangilash")
async def refresh_panel(message: types.Message):
    uchaskavoy = get_uchaskavoy_by_tg_id(message.from_user.id)
    if not uchaskavoy:
        await message.answer("❌ Siz uchaskavoy sifatida ro‘yxatdan o‘tmagansiz.")
        return

    await message.answer(
        f"🔄 Panel yangilandi!\n\n"
        f"👮‍♂️ <b>{uchaskavoy[1]}</b>\n"
        f"🏘 Mahalla: <b>{uchaskavoy[3]}</b>",
        reply_markup=uchaskavoy_menu,
        parse_mode="HTML"
    )


@router.message(lambda message: message.text == "📝 Xabar yuborish")
async def start_sending_message(message: types.Message, state: FSMContext):
    uchaskavoy = get_uchaskavoy_by_tg_id(message.from_user.id)
    if not uchaskavoy:
        await message.answer("❌ Siz uchaskavoy sifatida ro‘yxatdan o‘tmagansiz.")
        return

    await message.answer(
        "📨 Yubormoqchi bo‘lgan xabaringizni yuboring.\n"
        "Matn, rasm, video, audio yoki hujjat yuborishingiz mumkin.",
        # ❌ Bu joyni olib tashlaymiz:
        # reply_markup=types.ReplyKeyboardRemove()
        # ✅ o‘rniga menyuni qayta qo‘yamiz:
        reply_markup=uchaskavoy_menu
    )

    await state.set_state(UchaskavoySendMessage.waiting_content)


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

    await message.answer(f"✅ Xabar {sent_count} fuqaroga yuborildi")
    await state.clear()


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


@router.message(lambda message: message.text == "📩 Murojaatlar")
async def show_murojaatlar_menu(message: types.Message):
    uchaskavoy = get_uchaskavoy_by_tg_id(message.from_user.id)
    if not uchaskavoy:
        await message.answer("❌ Siz uchaskavoy sifatida ro‘yxatdan o‘tmagansiz.")
        return

    data = get_murojaatlar_by_uchaskavoy(uchaskavoy[0])
    if not data:
        await message.answer("📭 Hozircha hech kim murojaat yubormagan.")
        return

    # Inline tugmalar bilan foydalanuvchilarni chiqaramiz
    buttons = []
    row = []
    for i, user in enumerate(data, start=1):
        foydalanuvchi_nick = user[0] if user[0] else "Noma’lum"
        foydalanuvchi_id = user[1]
        row.append(
            InlineKeyboardButton(
                text=f"👤 {foydalanuvchi_nick[:10]}",
                callback_data=f"show_user_murojaatlar:{foydalanuvchi_id}"
            )
        )
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📋 <b>Murojaat yuborganlar:</b>", parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith("show_user_murojaatlar:"))
async def show_user_murojaatlar(callback: types.CallbackQuery):
    foydalanuvchi_id = int(callback.data.split(":")[1])

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
              SELECT id, foydalanuvchi_nick, turi, content, holat, telefon, location
              FROM murojaatlar
              WHERE foydalanuvchi_id = ?
              ORDER BY id DESC
              """, (foydalanuvchi_id,))
    murojaatlar = c.fetchall()
    conn.close()

    if not murojaatlar:
        await callback.message.answer("❌ Bu foydalanuvchi hech qanday murojaat yubormagan.")
        await callback.answer()
        return

    for row in murojaatlar:
        murojaat_id, nick, turi, content, holat, telefon, location = row

        # button matnini hozirgi holatga qarab aniqlaymiz:
        # agar hozir 'kutilmoqda' bo'lsa — tugma "✅ Bajarildi" bo'ladi (ya'ni bosilganda bajarildi ga o'tadi)
        # agar hozir 'bajarildi' bo'lsa — tugma "🕓 Kutilmoqda" bo'ladi
        if holat == "kutilmoqda":
            button_text = "✅ Bajarildi"
        else:
            button_text = "🕓 Kutilmoqda"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=button_text, callback_data=f"toggle_status:{murojaat_id}")
                ],
                [
                    InlineKeyboardButton(
                        text="💬 Javob berish",
                        callback_data=f"reply_to:{murojaat_id}"
                    )
                ]
            ]
        )

        # Qo'shimcha ma'lumotlar
        info_text = f"<b>👤 Foydalanuvchi:</b> {nick}\n"
        if telefon:
            info_text += f"<b>📞 Telefon:</b> <a href='tel:{telefon}'>{telefon}</a>\n"
        if location:
            try:
                lat, lon = location.split(",")
                info_text += f"<b>📍 Joylashuv:</b> <a href='https://maps.google.com/?q={lat},{lon}'>Ko‘rish</a>\n"
            except:
                pass

        info_text += f"\n<b>Holat:</b> {holat.capitalize()}\n__________________"

        try:
            if turi == "text":
                await callback.message.answer(
                    f"📝 Murojaat:\n\n{content}\n\n{info_text}",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif turi == "photo":
                await callback.message.answer_photo(photo=content, caption=info_text, parse_mode="HTML",
                                                    reply_markup=keyboard)
            elif turi == "video":
                await callback.message.answer_video(video=content, caption=info_text, parse_mode="HTML",
                                                    reply_markup=keyboard)
            elif turi == "document":
                await callback.message.answer_document(document=content, caption=info_text, parse_mode="HTML",
                                                       reply_markup=keyboard)
            elif turi == "voice":
                await callback.message.answer_voice(voice=content, caption=info_text, parse_mode="HTML",
                                                    reply_markup=keyboard)
            else:
                # agar noma'lum turi bo'lsa, matn sifatida yuboramiz
                await callback.message.answer(f"{content}\n\n{info_text}", parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            await callback.message.answer(f"⚠️ Xabar yuborishda xatolik: {e}")

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("toggle_status:"))
async def toggle_status(callback: types.CallbackQuery):
    # callback.data = "toggle_status:<murojaat_id>"
    try:
        murojaat_id = int(callback.data.split(":")[1])
    except:
        await callback.answer("❌ Noto'g'ri ma'lumot.")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
              SELECT id, foydalanuvchi_nick, turi, content, holat, telefon, location
              FROM murojaatlar
              WHERE id = ?
              """, (murojaat_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        await callback.answer("❌ Murojaat topilmadi.")
        return

    _id, nick, turi, content, holat, telefon, location = row

    # yangi holat — teskari:
    yangi_holat = "bajarildi" if holat == "kutilmoqda" else "kutilmoqda"
    c.execute("UPDATE murojaatlar SET holat = ? WHERE id = ?", (yangi_holat, murojaat_id))
    conn.commit()
    conn.close()

    # tugma matnini yangi holatga qarab aniqlaymiz (tugma bosilganda keyingi amal bo'lishi kerak)
    if yangi_holat == "kutilmoqda":
        button_text = "✅ Bajarildi"  # agar hozir kutilmoqda bo'lsa, tugma bosilganda bajarildi kerak
    else:
        button_text = "🕓 Kutilmoqda"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=button_text, callback_data=f"toggle_status:{murojaat_id}")],
            [InlineKeyboardButton(text="💬 Javob berish", callback_data=f"reply_to:{murojaat_id}")]
        ]
    )

    # yangilangan info text
    info_text = f"<b>👤 Foydalanuvchi:</b> {nick}\n"
    if telefon:
        info_text += f"<b>📞 Telefon:</b> <a href='tel:{telefon}'>{telefon}</a>\n"
    if location:
        try:
            lat, lon = location.split(",")
            info_text += f"<b>📍 Joylashuv:</b> <a href='https://maps.google.com/?q={lat},{lon}'>Ko‘rish</a>\n"
        except:
            pass
    info_text += f"\n<b>Holat:</b> {yangi_holat.capitalize()}\n__________________"

    # Xabarni joyida yangilashga harakat qilamiz
    try:
        if turi == "text":
            await callback.message.edit_text(f"📝 Murojaat:\n\n{content}\n\n{info_text}", parse_mode="HTML",
                                             reply_markup=keyboard)
        else:
            # agar media bo'lsa, captionni o'zgartirishga harakat qilamiz
            await callback.message.edit_caption(caption=info_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        # ba'zi holatlarda edit_caption yoki edit_text ishlamasligi mumkin (eskirgan xabar),
        # lekin biz yangi xabar yubormaslikka harakat qilamiz — shuning uchun fallbackda faqat notify qilamiz
        await callback.answer("🔄 Holat yangilandi (xabarni tahrirlash imkoni bo'lmadi).")
        return

    await callback.answer(f"✅ Holat '{yangi_holat}' deb o‘zgartirildi.")

# @router.callback_query(lambda c: c.data.startswith("toggle_status:"))
# async def toggle_murojaat_status(callback: types.CallbackQuery):
#     import sqlite3
#     from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
#     from database import DB_NAME
#
#     murojaat_id = int(callback.data.split(":")[1])
#
#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute("""
#         SELECT foydalanuvchi_id, turi, content, holat, telefon, location
#         FROM murojaatlar
#         WHERE id = ?
#     """, (murojaat_id,))
#     row = c.fetchone()
#
#     if not row:
#         await callback.answer("❌ Murojaat topilmadi.")
#         conn.close()
#         return
#
#     foydalanuvchi_id, turi, content, holat, telefon, location = row
#     yangi_holat = "bajarildi" if holat == "kutilmoqda" else "kutilmoqda"
#
#     # Holatni yangilash
#     c.execute("UPDATE murojaatlar SET holat = ? WHERE id = ?", (yangi_holat, murojaat_id))
#     conn.commit()
#
#     # F.I.Sh. ni uchaskavoy jadvalidan olish
#     c.execute("SELECT fio FROM uchaskavoy WHERE id = ?", (foydalanuvchi_id,))
#     row2 = c.fetchone()
#     conn.close()
#
#     fio = row2[0] if row2 else "Noma’lum fuqaro"
#
#     # Tugma yaratish
#     button_text = "🕓 Kutilmoqda" if yangi_holat == "bajarildi" else "✅ Bajarildi"
#     holat_emoji = "✅" if yangi_holat == "bajarildi" else "🕓"
#
#     keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text=button_text, callback_data=f"toggle_status:{murojaat_id}")]
#         ]
#     )
#
#     # 🔹 Telefon va lokatsiyani qo‘shish
#     info_text = f"<b>👤 F.I.Sh.:</b> {fio}\n"
#     if telefon:
#         info_text += f"<b>📞 Telefon:</b> <a href='tel:{telefon}'>{telefon}</a>\n"
#     if location:
#         try:
#             lat, lon = location.split(",")
#             info_text += f"<b>📍 Joylashuv:</b> <a href='https://maps.google.com/?q={lat},{lon}'>Ko‘rish</a>\n"
#         except:
#             pass
#
#     info_text += f"\n<b>{holat_emoji} Holat:</b> <i>{yangi_holat.capitalize()}</i>\n───────────────"
#
#     # 🔸 Kontent turiga qarab xabarni yangilash
#     try:
#         if turi == "text":
#             await callback.message.edit_text(
#                 f"📝 <b>Matnli murojaat:</b>\n\n{content}\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=keyboard
#             )
#         elif turi == "photo":
#             await callback.message.edit_caption(
#                 caption=f"📸 <b>Rasmli murojaat</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=keyboard
#             )
#         elif turi == "video":
#             await callback.message.edit_caption(
#                 caption=f"🎥 <b>Videomurojaat</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=keyboard
#             )
#         elif turi == "document":
#             await callback.message.edit_caption(
#                 caption=f"📄 <b>Fayl murojaat</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=keyboard
#             )
#         elif turi == "voice":
#             await callback.message.edit_caption(
#                 caption=f"🎙 <b>Ovozli murojaat</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=keyboard
#             )
#         elif turi == "location":
#             lat2, lon2 = map(float, content.split(","))
#             await callback.message.answer_location(latitude=lat2, longitude=lon2)
#             await callback.message.answer(
#                 f"📍 <b>Joylashuv yuborildi</b>\n\n{info_text}",
#                 parse_mode="HTML",
#                 reply_markup=keyboard
#             )
#     except Exception:
#         await callback.message.answer(
#             f"🔄 <b>Yangilangan murojaat</b>\n\n{info_text}",
#             parse_mode="HTML",
#             reply_markup=keyboard
#         )
#
#     await callback.answer(f"✅ Holat '{yangi_holat}' deb o‘zgartirildi.")
