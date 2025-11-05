import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# from main_bot import bot
from database import (
    get_user_role,
    add_fuqarolar,
    get_viloyatlar,
    get_tumanlar,
    get_mahallalar,
    get_uchaskavoy_by_mahalla,
    add_murojaat,
    get_fuqarolar_by_tg_id, get_mahalla_by_tg_id, get_fuqarolar_by_tg_id_2,
)

router = Router()


# === FSM holatlar ===
class FuqarolikRegister(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_viloyat = State()
    waiting_tuman = State()
    waiting_mahalla = State()
    registered = State()
    telefon = State()
    location = State()


# 🔹 Doimiy menyu (fuqaro uchun)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Qayta yangilash")],
    ],
    resize_keyboard=True
)


def normalize_phone(phone: str):
    # Faqat raqamlarni qoldiramiz
    digits = re.sub(r'\D', '', phone)

    # Agar foydalanuvchi 998 bilan boshlasa
    if digits.startswith('998') and len(digits) == 12:
        return f'+{digits}'
    # Agar faqat 9 ta raqam (masalan 901234567)
    elif len(digits) == 9:
        return f'+998{digits}'
    else:
        return None


# === /start komandasi ===
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    role = get_user_role(message.from_user.id)

    # 🧭 Doimiy menyu (ReplyKeyboard, inline emas!)
    # main_menu = ReplyKeyboardMarkup(
    #     keyboard=[
    #         [KeyboardButton(text="🆕 Yangi murojaat yuborish")],
    #         # [KeyboardButton(text="📋 Mening murojaatlarim")],
    #         # [KeyboardButton(text="🔄 Qayta yangilash")]
    #     ],
    #     resize_keyboard=True
    # )

    # 👤 Agar fuqaro yoki yangi foydalanuvchi bo‘lsa
    if role is None or role == "fuqaro":
        fuqaro = get_fuqarolar_by_tg_id_2(message.from_user.id)

        if fuqaro:
            # ✅ Allaqachon ro‘yxatdan o‘tgan
            await state.set_state(FuqarolikRegister.registered)
            await message.answer(
                f"👋 Salom, {fuqaro[1]}!\n"
                f"Siz allaqachon ro‘yxatdan o‘tgansiz ✅\n\n"
                f"Endi murojaatingizni yuborishingiz mumkin:"
            )
        else:
            # 🆕 Yangi fuqaro uchun
            await state.clear()
            await message.answer(
                "👋 Assalomu alaykum!\n"
                "Mazkur bot sizning mahallangiz yoki jamoangiz xavfsizligini\n"
                "ta'minlashga yordam beradi.\n"
                "Sizning xabaringiz va shaxsingiz mutlaqo sir saqlanadi."
                "Xabaringiz faqatgina hudud profilaktika inspektoriga"
                "yetkaziladi va shu orqali huquqbuzatliklarning barvaqt"
                "oldini olinishi mumkin\n\n"
                "Iltimos, ismingizni kiriting:"
            )
            await state.set_state(FuqarolikRegister.waiting_name)
    else:
        await message.answer("⚠️ Ushbu bo‘lim faqat fuqarolar uchun mo‘ljallangan.")


@router.message(lambda msg: msg.text == "🆕 Yangi murojaat yuborish")
async def start_new_murojaat(message: types.Message, state: FSMContext):
    await state.set_state(FuqarolikRegister.registered)

    # Oddiy text sifatida yuborilayotgan xabarni process_murojaat ga uzatamiz
    # Biz text bo'lmagan turini yaratib, shuni yuboramiz
    class MurojaatStart:
        def __init__(self, from_user):
            self.from_user = from_user
            self.text = "new_murojaat"
            self.photo = None
            self.video = None
            self.document = None
            self.voice = None
            self.location = None

    dummy_msg = MurojaatStart(message.from_user)
    await process_murojaat(dummy_msg, state)


# === Ismni qabul qilish ===
@router.message(FuqarolikRegister.waiting_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) < 3:
        await message.answer("❌ Ism juda qisqa. Qayta kiriting:")
        return

    await state.update_data(name=name)
    await message.answer("📞 Telefon raqamingizni kiriting (masalan: +998901234567):")
    await state.set_state(FuqarolikRegister.waiting_phone)


# === Telefon raqamini qabul qilish ===
@router.message(FuqarolikRegister.waiting_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    phone = normalize_phone(phone)

    if not phone:
        await message.answer("❌ Telefon raqami noto‘g‘ri. Iltimos, +998 bilan kiriting.")
        return

    await state.update_data(phone=phone)
    viloyatlar = get_viloyatlar()

    if not viloyatlar:
        await message.answer("⚠️ Hozircha viloyatlar bazada mavjud emas.")
        return

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=v[1], callback_data=f"fqr_vil_{v[0]}")]
            for v in viloyatlar
        ]
    )
    await message.answer("📍 Viloyatingizni tanlang:", reply_markup=keyboard)
    await state.set_state(FuqarolikRegister.waiting_viloyat)


# === Viloyat tanlash ===
@router.callback_query(F.data.startswith("fqr_vil_"))
async def process_viloyat(callback: types.CallbackQuery, state: FSMContext):
    viloyat_id = int(callback.data.split("_")[2])
    await state.update_data(viloyat_id=viloyat_id)

    tumanlar = get_tumanlar(viloyat_id)
    if not tumanlar:
        await callback.message.edit_text("⚠️ Bu viloyatda tumanlar mavjud emas.")
        return

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=t[1], callback_data=f"fqr_tum_{t[0]}")]
            for t in tumanlar
        ]
    )
    await callback.message.edit_text("🏙 Tumaningizni tanlang:", reply_markup=keyboard)
    await state.set_state(FuqarolikRegister.waiting_tuman)


# === Tuman tanlash ===
@router.callback_query(F.data.startswith("fqr_tum_"))
async def process_tuman(callback: types.CallbackQuery, state: FSMContext):
    tuman_id = int(callback.data.split("_")[2])
    await state.update_data(tuman_id=tuman_id)

    mahallalar = get_mahallalar(tuman_id)
    if not mahallalar:
        await callback.message.edit_text("⚠️ Bu tumanda mahallalar mavjud emas.")
        return

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=m[1], callback_data=f"fqr_mah_{m[0]}")]
            for m in mahallalar
        ]
    )
    await callback.message.edit_text("🏡 Mahallangizni tanlang:", reply_markup=keyboard)
    await state.set_state(FuqarolikRegister.waiting_mahalla)


# === Mahalla tanlash ===
@router.callback_query(F.data.startswith("fqr_mah_"))
async def process_mahalla(callback: types.CallbackQuery, state: FSMContext):
    mahalla_id = int(callback.data.split("_")[2])
    await state.update_data(mahalla_id=mahalla_id)

    data = await state.get_data()
    add_fuqarolar(
        fio=data["name"],
        telefon=data["phone"],
        tg_id=callback.from_user.id,
        mahalla_id=mahalla_id,
        role=None
    )

    await callback.message.edit_text(
        "✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!\n\n"
        "Endi murojaatingizni yuborishingiz mumkin."
    )
    await state.set_state(FuqarolikRegister.registered)


@router.message(F.text == "⬅️ Orqaga")
async def go_back(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == FuqarolikRegister.telefon:
        # Telefon bosqichida orqaga ketsa — murojaat yuborish bosqichiga qaytadi
        await message.answer(
            "📩 Murojaatingizni qaytadan yuborishingiz mumkin.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(FuqarolikRegister.registered)

    elif current_state == FuqarolikRegister.location:
        # Lokatsiya bosqichida orqaga ketsa — telefonni qayta so‘raymiz
        await message.answer(
            "📞 Telefon raqamingizni kiriting:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
                    [KeyboardButton(text="⬅️ Orqaga")]
                ],
                resize_keyboard=True
            )
        )
        await state.set_state(FuqarolikRegister.telefon)

    else:
        await message.answer("🔙 Orqaga qaytish imkoni yo‘q bu bosqichda.")


# === MUROJAATNI QABUL QILISH BOSQICHI ===
@router.message(FuqarolikRegister.registered)
async def process_murojaat(message: types.Message, state: FSMContext):
    fuqaro = get_mahalla_by_tg_id(message.from_user.id)
    if not fuqaro:
        await message.answer("⚠️ Siz ro‘yxatdan o‘tmagansiz. Iltimos, /start buyrug‘ini bosing.")
        return

    mahalla_id = fuqaro[0]
    uchaskavoy = get_uchaskavoy_by_mahalla(mahalla_id)
    if not uchaskavoy:
        await message.answer("⚠️ Ushbu mahallaga profilaktika inspektori biriktirilmagan.")
        return

    # 🔹 Murojaat turi aniqlanadi
    turi, content = None, None
    if message.text and message.text != "new_murojaat":
        turi, content = "text", message.text.strip()
    elif message.photo:
        turi, content = "photo", message.photo[-1].file_id
    elif message.video:
        turi, content = "video", message.video.file_id
    elif message.video_note:
        turi, content = "video_note", message.video_note.file_id
    elif message.document:
        turi, content = "document", message.document.file_id
    elif message.voice:
        turi, content = "voice", message.voice.file_id
    elif message.location:
        turi, content = "location", f"{message.location.latitude},{message.location.longitude}"

    if not turi:
        await message.answer("⚠️ Faqat matn, media, ovoz yoki joylashuv yuborish mumkin.")
        return

    await state.update_data(
        uchaskavoy_id=uchaskavoy[0],
        turi=turi,
        content=content
    )

    # 🔹 3 ta tugmali menyu
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="⏭ Keyingi bosqich")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "📱 Telefon raqamingizni yuborishingiz mumkin, agar xohlasangiz keyingi bosqichga o‘ting:",
        reply_markup=markup
    )

    await state.set_state(FuqarolikRegister.telefon)  # ✅ to‘g‘ri


# 🔹 2. TELEFON RAQAMINI QABUL QILISH
@router.message(FuqarolikRegister.telefon)
async def process_telefon(message: types.Message, state: FSMContext):
    # 🔙 Orqaga bosilganda
    if message.text == "⬅️ Orqaga":
        await message.answer(
            "📩 Murojaatingizni qaytadan yuborishingiz mumkin.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(FuqarolikRegister.registered)
        return

    # ❌ Bekor qilish
    if message.text == "❌ Bekor qilish":
        await message.answer("❌ Murojaat bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        await state.set_state(FuqarolikRegister.registered)
        return

    # ⏭ Keyingi bosqich — telefon kiritmasdan lokatsiyaga o'tadi
    if message.text == "⏭ Keyingi bosqich":
        await state.update_data(telefon=None)
        await message.answer(
            "📍 Lokatsiyangizni yuborishingiz mumkin, agar xohlasangiz murojaatni yakunlang:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
                    [KeyboardButton(text="✅ Murojaatni yakunlash")],
                    [KeyboardButton(text="❌ Bekor qilish")]
                ],
                resize_keyboard=True
            )
        )
        await state.set_state(FuqarolikRegister.location)
        return

    # 📞 Telefon raqam yuborilgan holat
    telefon = None
    if message.contact:
        telefon = message.contact.phone_number
    elif message.text and message.text.startswith("+998"):
        telefon = message.text.strip()
    else:
        await message.answer(
            "📞 Telefon raqamingizni yuboring yoki '⏭ Keyingi bosqich' tugmasini bosing.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
                    [KeyboardButton(text="⏭ Keyingi bosqich")],
                    [KeyboardButton(text="❌ Bekor qilish")]
                ],
                resize_keyboard=True
            )
        )
        return

    # 🔸 Raqam saqlanadi va lokatsiya bosqichiga o‘tiladi
    await state.update_data(telefon=telefon)
    await message.answer(
        "📍 Lokatsiyangizni yuborishingiz mumkin, agar xohlasangiz murojaatni yakunlang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
                [KeyboardButton(text="✅ Murojaatni yakunlash")],
                [KeyboardButton(text="❌ Bekor qilish")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(FuqarolikRegister.location)


# 🔹 3. LOKATSIYANI QABUL QILISH VA MA’LUMOTLARNI BAZAGA YOZISH
@router.message(FuqarolikRegister.location)
async def process_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    location = None

    # 🔙 Orqaga bosilganda — telefon bosqichiga qaytadi
    if message.text == "⬅️ Orqaga":
        await message.answer(
            "📞 Telefon raqamingizni kiriting:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
                    [KeyboardButton(text="⏭ Keyingi bosqich")],
                    [KeyboardButton(text="❌ Bekor qilish")]
                ],
                resize_keyboard=True
            )
        )
        await state.set_state(FuqarolikRegister.telefon)
        return

    # ❌ Bekor qilish
    if message.text == "❌ Bekor qilish":
        await message.answer("❌ Murojaat bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await state.set_state(FuqarolikRegister.registered)
        return

    # ✅ Murojaatni yakunlash (lokatsiyasiz)
    if message.text == "✅ Murojaatni yakunlash":
        location = None

    # 📍 Lokatsiya yuborilgan holat
    elif message.location:
        location = f"{message.location.latitude},{message.location.longitude}"

    else:
        await message.answer(
            "📍 Lokatsiyani yuboring yoki '✅ Murojaatni yakunlash' tugmasini bosing.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
                    [KeyboardButton(text="✅ Murojaatni yakunlash")],
                    [KeyboardButton(text="❌ Bekor qilish")]
                ],
                resize_keyboard=True
            )
        )
        return

    # 🔹 Murojaatni bazaga yozish
    uchaskavoy_id = data.get("uchaskavoy_id")
    turi = data.get("turi")
    content = data.get("content")
    telefon = data.get("telefon")
    foydalanuvchi_nick = message.from_user.username or message.from_user.full_name

    m_id = add_murojaat(
        foydalanuvchi_id=message.from_user.id,
        foydalanuvchi_nick=foydalanuvchi_nick,
        uchaskavoy_id=uchaskavoy_id,
        turi=turi,
        content=content,
        telefon=telefon,
        location=location
    )
    print(m_id)
    # await message.answer(
    #     "✅ Murojaatingiz profilaktika inspektoriga yuborildi. Rahmat!\n"
    #     "Yangi murojaat yuborish uchun /start tugmasini bosing",
    #     reply_markup=types.ReplyKeyboardRemove()
    # )
    try:
        fuqaro = get_mahalla_by_tg_id(message.from_user.id)
        if not fuqaro:
            await message.answer("⚠️ Sizning mahalla ma’lumotingiz topilmadi. /start ni qayta bosing.")
            return

        mahalla_id = fuqaro[0]
        uchaskavoy = get_uchaskavoy_by_mahalla(mahalla_id)
        print(uchaskavoy)

        if uchaskavoy:
            # location — bu funksiya boshida aniqlangan local o'zgaruvchi (string yoki None)
            # message.location bo'lmasligi mumkin, shuning uchun local `location`ni ishlatamiz
            lat, lon = None, None
            if location:
                # location odatda "lat,lon" ko'rinishida saqlangan
                try:
                    lat_str, lon_str = str(location).split(",")
                    lat = lat_str.strip()
                    lon = lon_str.strip()
                except Exception:
                    lat, lon = None, None

            inspector_tg_id = uchaskavoy[3]  # tg_id ustuni
            foydalanuvchi_nick = message.from_user.username or message.from_user.full_name

            # Bosh matn — joylashuv havolasi faqat mavjud bo'lsa qo'shiladi
            loc_link = f"<a href='https://www.google.com/maps?q={lat},{lon}'>Ko‘rish</a>" if lat and lon else "Yo'q"
            murojaat_text = (
                f"📩 <b>Yangi murojaat!</b>\n\n"
                f"👤 <b>Fuqaro:</b> @{foydalanuvchi_nick}\n"
                f"📞 <b>Telefon:</b> {telefon}\n"
                f"📍 <b>Joylashuv:</b> {loc_link}\n\n"
                f"<b>Turi:</b> {turi}\n"
            )
            bot = message.bot
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Javob berish", callback_data=f"reply_to:{m_id}")]
                ]
            )

            # media turiga qarab yuborish — content deb olingan qiymatdan foydalanamiz
            if turi == "text":
                full_text = murojaat_text + f"📝 <b>Xabar:</b> {content}"
                await bot.send_message(inspector_tg_id, full_text, parse_mode="HTML", reply_markup=keyboard)

            elif turi == "photo":
                # content — file_id
                await bot.send_photo(inspector_tg_id, content, caption=murojaat_text, parse_mode="HTML",
                                     reply_markup=keyboard)

            elif turi == "video":
                await bot.send_video(inspector_tg_id, content, caption=murojaat_text, parse_mode="HTML",
                                     reply_markup=keyboard)

            elif turi == "video_note":
                # video_note odatda file_id bilan yuboriladi
                await bot.send_video_note(inspector_tg_id, content, reply_markup=keyboard)
                # agar joylashuv bo'lsa uni alohida xabar sifatida yuborish mumkin
                if lat and lon:
                    await bot.send_message(inspector_tg_id,
                                           f"📍 <a href='https://www.google.com/maps?q={lat},{lon}'>Joyni ko'rish</a>",
                                           parse_mode="HTML", reply_markup=keyboard)

            elif turi == "document":
                await bot.send_document(inspector_tg_id, content, caption=murojaat_text, parse_mode="HTML",
                                        reply_markup=keyboard)

            elif turi == "voice":
                await bot.send_voice(inspector_tg_id, content, caption=murojaat_text, parse_mode="HTML",
                                     reply_markup=keyboard)

            elif turi == "location":
                # content bu yerda "lat,lon" string ekan — to'g'ri formatda yuboramiz
                if content and "," in content:
                    try:
                        lat_c, lon_c = content.split(",", 1)
                        loc_msg = (
                            f"📍 <b>Joylashuv:</b> "
                            f"<a href='https://www.google.com/maps?q={lat_c.strip()},{lon_c.strip()}'>Ko‘rish</a>"
                        )
                        await bot.send_message(inspector_tg_id, loc_msg, parse_mode="HTML", reply_markup=keyboard)
                    except Exception:
                        # fallback: agar parsingda muammo bo'lsa oddiy matn yuborish
                        await bot.send_message(inspector_tg_id, "📍 Joylashuv ma'lumotida xato.", reply_markup=keyboard)
                else:
                    await bot.send_message(inspector_tg_id, "📍 Joylashuv ma'lumotlari mavjud emas.",
                                           reply_markup=keyboard)

    except Exception as e:
        print(f"❌ Inspektorga yuborishda xato: {e}")

    await state.clear()

    await message.answer(
        "✅ Murojaatingiz profilaktika inspektoriga yuborildi.\n"
        "Rahmat! Yana murojaat yuborishingiz mumkin.",
        reply_markup=ReplyKeyboardRemove()
    )

    # 🔹 Holatni qayta boshlaymiz — fuqaro yangi murojaat yuborishi mumkin
    await state.set_state(FuqarolikRegister.registered)
