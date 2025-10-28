import re

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import (
    get_user_role,
    add_fuqarolar,
    get_viloyatlar,
    get_tumanlar,
    get_mahallalar,
    get_uchaskavoy_by_mahalla,
    add_murojaat,
    get_fuqarolar_by_tg_id, get_mahalla_by_tg_id,
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

    # Agar role None bo‘lsa — fuqaro deb qabul qilamiz
    if role is None or role == "fuqaro":
        fuqaro = get_fuqarolar_by_tg_id(message.from_user.id)

        if fuqaro:
            await message.answer(
                f"👋 Salom, {fuqaro[1]}!\n"
                f"Siz allaqachon ro‘yxatdan o‘tgansiz ✅\n\n"
                f"Endi murojaatingizni yuborishingiz mumkin:"
            )
            await state.set_state(FuqarolikRegister.registered)
            return

        # Yangi fuqaro uchun ro‘yxatdan o‘tish
        await state.clear()
        await message.answer(
            "👋 Assalomu alaykum!\n"
            "Fuqarolik tizimiga xush kelibsiz!\n\n"
            "Iltimos, ismingizni kiriting:"
        )
        await state.set_state(FuqarolikRegister.waiting_name)
    else:
        await message.answer("⚠️ Ushbu bo‘lim faqat fuqarolar uchun mo‘ljallangan.")


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


# === Murojaat yuborish (matn, media, ovoz, joylashuv) ===
@router.message(FuqarolikRegister.registered)
async def process_murojaat(message: types.Message, state: FSMContext):
    # FSM dan olish o‘rniga — bazadan olish
    fuqaro = get_mahalla_by_tg_id(message.from_user.id)
    if not fuqaro:
        await message.answer("⚠️ Siz ro‘yxatdan o‘tmagansiz. Iltimos, /start buyrug‘ini bosing.")
        return

    mahalla_id = fuqaro[0]  # get_mahalla_by_tg_id() mahalla_id qaytaradi deb hisoblaymiz

    uchaskavoy = get_uchaskavoy_by_mahalla(mahalla_id)
    if not uchaskavoy:
        await message.answer("⚠️ Ushbu mahallaga uchaskavoy biriktirilmagan.")
        return

    # Murojaat turini aniqlash
    turi, content = None, None

    if message.text:
        turi, content = "text", message.text.strip()
    elif message.photo:
        turi, content = "photo", message.photo[-1].file_id
    elif message.video:
        turi, content = "video", message.video.file_id
    elif message.document:
        turi, content = "document", message.document.file_id
    elif message.voice:
        turi, content = "voice", message.voice.file_id
    elif message.location:
        turi, content = "location", f"{message.location.latitude},{message.location.longitude}"

    if not turi:
        await message.answer("⚠️ Bu turdagi faylni qabul qilib bo‘lmaydi.")
        return

    # foydalanuvchi nickname yoki ismni olish
    foydalanuvchi_nick = message.from_user.username or message.from_user.full_name

    add_murojaat(
        foydalanuvchi_id=message.from_user.id,
        foydalanuvchi_nick=foydalanuvchi_nick,
        uchaskavoy_id=uchaskavoy[0],
        turi=turi,
        content=content,
    )

    await message.answer("✅ Murojaatingiz uchaskavoyga yuborildi. Rahmat!")

