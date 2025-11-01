import re

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
                "ta'minlashga yordam beradi.\n\n"
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


# === Murojaat yuborish (matn, media, ovoz, joylashuv) ===
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

    # 🔹 Sticker yuborilgan bo‘lsa, rad etamiz
    if message.sticker:
        await message.answer("❌ Sticker yuborish mumkin emas. Iltimos, matn yoki media yuboring.")
        return

    # 🔹 Murojaat turi va ma’lumotni aniqlaymiz
    turi, content = None, None
    if message.text and message.text != "new_murojaat":
        turi, content = "text", message.text.strip()
    elif message.photo:
        turi, content = "photo", message.photo[-1].file_id
    if message.text:
        turi, content = "text", message.text.strip()
    elif message.photo:
        turi, content = "photo", message.photo[-1].file_id
    elif message.video:
        turi, content = "video", message.video.file_id
    elif message.video_note:  # ✅ Yumaloq video (video note)
        turi, content = "video_note", message.video_note.file_id
    elif message.document:
        turi, content = "document", message.document.file_id
    elif message.voice:
        turi, content = "voice", message.voice.file_id
    elif message.location:
        turi, content = "location", f"{message.location.latitude},{message.location.longitude}"

    # 🔹 Agar hech narsa mos kelmasa
    if not turi:
        await message.answer(
            "⚠️ Bu turdagi faylni qabul qilib bo‘lmaydi. Faqat matn, media, ovoz, lokatsiya yoki video yuboring.")
        return
    # 🔹 FSM ma’lumotni vaqtincha saqlaymiz
    await state.update_data(
        uchaskavoy_id=uchaskavoy[3],
        turi=turi,
        content=content
    )

    # 🔹 Keyingi bosqich — telefon raqamini so‘raymiz
    await message.answer(
        "📞 Iltimos, telefon raqamingizni yuboring.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
                [KeyboardButton(text="⬅️ Orqaga")]
            ],
            resize_keyboard=True
        )
    )

    await state.set_state(FuqarolikRegister.telefon)


# 🔹 2. TELEFON RAQAMINI QABUL QILISH
@router.message(FuqarolikRegister.telefon)
async def process_telefon(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        return
    if message.contact:
        telefon = message.contact.phone_number
    else:
        telefon = message.text.strip()

    await state.update_data(telefon=telefon)

    await message.answer(
        "📍 Endi lokatsiyangizni yuboring.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
                      [KeyboardButton(text="⬅️ Orqaga")]],

            resize_keyboard=True
        )
    )

    await state.set_state(FuqarolikRegister.location)


# 🔹 3. LOKATSIYANI QABUL QILISH VA MA’LUMOTLARNI BAZAGA YOZISH
@router.message(FuqarolikRegister.location)
async def process_location(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        return

    data = await state.get_data()

    uchaskavoy_id = data.get("uchaskavoy_id")
    turi = data.get("turi")
    content = data.get("content")
    telefon = data.get("telefon")

    # Lokatsiyani olish
    if message.location:
        location = f"{message.location.latitude},{message.location.longitude}"
    else:
        location = None

    foydalanuvchi_nick = message.from_user.username or message.from_user.full_name

    # 🔹 Bazaga yozish
    add_murojaat(
        foydalanuvchi_id=message.from_user.id,
        foydalanuvchi_nick=foydalanuvchi_nick,
        uchaskavoy_id=uchaskavoy_id,
        turi=turi,
        content=content,
        telefon=telefon,
        location=location
    )

    await message.answer(
        "✅ Murojaatingiz profilaktika inspektoriga yuborildi. Rahmat!\n"
        "Yangi murojaat yuborish uchun /start tugmasini bosing",
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.clear()
