from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError
from database import get_all_users
from config import ADMIN_ID
from database import (
    get_viloyatlar,
    get_tumanlar,
    get_mahallalar,
    get_uchaskavoy_by_mahalla,
    add_uchaskavoy,
    update_uchaskavoy,
    delete_uchaskavoy,
)

router = Router()

from aiogram import types, F
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import ADMIN_ID
from database import get_all_users

from database import delete_user_by_tg_id

@router.message(F.text == "/logout")
async def user_logout(message: types.Message):
    tg_id = message.from_user.id
    try:
        delete_user_by_tg_id(tg_id)
        await message.answer("🚪 Siz tizimdan chiqdingiz.\n"
                             "Agar qayta kirishni xohlasangiz, /start buyrug‘ini bosing.")
    except Exception as e:
        print(f"Logout xatolik: {e}")
        await message.answer("⚠️ Chiqishda xatolik yuz berdi. Keyinroq urinib ko‘ring.")


@router.message(F.text == "/yangilash")
async def send_update_to_all(message: types.Message):
    if message.chat.id != ADMIN_ID:
        await message.answer("⚠️ Siz admin emassiz.")
        return

    users = get_all_users()
    total = len(users)
    success = 0
    failed = 0

    await message.answer(f"🔄 Yangilash xabari yuborilmoqda...\n👥 Jami foydalanuvchi: {total}")

    for user in users:
        user_id = user[0]

        # Faqat raqamli ID bo‘lsa yuboramiz
        if not str(user_id).isdigit():
            print(f"⚠️ Noto‘g‘ri ID: {user_id}")
            failed += 1
            continue

        try:
            await message.bot.send_message(
                chat_id=int(user_id),
                text="⚠️ Botga yangilash kiritildi.\n\nIltimos, /start tugmasini bosing 🔁"
            )
            success += 1

        except TelegramForbiddenError:
            # foydalanuvchi botni bloklagan bo‘lishi mumkin
            print(f"🚫 Bloklagan foydalanuvchi: {user_id}")
            failed += 1
            continue

        except TelegramBadRequest:
            # chat not found yoki notog‘ri ID
            print(f"❌ Chat topilmadi: {user_id}")
            failed += 1
            continue

        except Exception as e:
            print(f"⚠️ Xabar yuborishda xatolik ({user_id}): {e}")
            failed += 1
            continue

    await message.answer(
        f"✅ Tugadi!\n\n"
        f"📨 Yuborilgan: {success}\n"
        f"🚫 Yuborilmagan: {failed}\n"
        f"👥 Jami bazada: {total}"
    )



# --- Klaviatura: Orqaga qaytish ---
def cancel_kb():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⬅️ Orqaga qaytish")]
        ],
        resize_keyboard=True
    )


# --- FSM: Uchaskavoy qo‘shish ---
class AddUchaskavoy(StatesGroup):
    waiting_fio = State()
    waiting_phone = State()
    waiting_tg_id = State()


# --- FSM: Uchaskavoy o‘zgartirish ---
class EditUchaskavoy(StatesGroup):
    waiting_fio = State()
    waiting_phone = State()
    waiting_tg_id = State()


# --- Admin panelni ishga tushirish ---
@router.message(F.text == "Mahalla boshqaruvi")
async def manage_panel(message: types.Message):
    if message.chat.id != ADMIN_ID:
        await message.answer("⚠️ Siz admin emassiz.")
        return

    viloyatlar = get_viloyatlar()
    if not viloyatlar:
        await message.answer("📭 Viloyatlar bazada mavjud emas.")
        return

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=v[1], callback_data=f"adm_vil_{v[0]}")] for v in viloyatlar
        ]
    )
    await message.answer("🏢 Viloyatni tanlang:", reply_markup=kb)


# --- Viloyat tanlash ---
@router.callback_query(F.data.startswith("adm_vil_"))
async def select_viloyat(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    viloyat_id = int(callback.data.split("_")[2])
    tumanlar = get_tumanlar(viloyat_id)

    if not tumanlar:
        await callback.message.answer("📭 Bu viloyatda tumanlar mavjud emas.")
        return

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=t[1], callback_data=f"adm_tum_{t[0]}")] for t in tumanlar
        ]
    )
    await callback.message.edit_text("🏙 Tuman tanlang:", reply_markup=kb)


# --- Tuman tanlash ---
@router.callback_query(F.data.startswith("adm_tum_"))
async def select_tuman(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    tuman_id = int(callback.data.split("_")[2])
    mahallalar = get_mahallalar(tuman_id)

    if not mahallalar:
        await callback.message.answer("📭 Bu tumanda mahallalar mavjud emas.")
        return

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=m[1], callback_data=f"adm_mah_{m[0]}")] for m in mahallalar
        ]
    )
    await callback.message.edit_text("🏡 Mahallani tanlang:", reply_markup=kb)


# --- Mahalla tanlash ---
@router.callback_query(F.data.startswith("adm_mah_"))
async def select_mahalla(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    mahalla_id = int(callback.data.split("_")[2])
    uchaskavoy = get_uchaskavoy_by_mahalla(mahalla_id)

    if uchaskavoy:
        text = (
            f"👮‍♂️ Uchaskavoy ma’lumoti:\n\n"
            f"👤 F.I.O: {uchaskavoy[1]}\n"
            f"📞 Telefon: {uchaskavoy[2]}\n"
            f"🆔 Telegram ID: {uchaskavoy[3]}"
        )
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="✏️ O‘zgartirish", callback_data=f"adm_edit_{mahalla_id}")],
                [types.InlineKeyboardButton(text="🗑 O‘chirish", callback_data=f"adm_del_{mahalla_id}")]
            ]
        )
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="➕ Profilaktika inspektorini qo‘shish",
                                            callback_data=f"adm_add_{mahalla_id}")]
            ]
        )
        await callback.message.edit_text("Bu mahallada Profilaktika inspektori yo‘q.", reply_markup=kb)


# --- Qo‘shish jarayoni ---
@router.callback_query(F.data.startswith("adm_add_"))
async def start_add_uchaskavoy(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    mahalla_id = int(callback.data.split("_")[2])
    await state.update_data(mahalla_id=mahalla_id)
    await state.set_state(AddUchaskavoy.waiting_fio)
    await callback.message.answer("👤 Profilaktika inspektori F.I.O.sini kiriting:", reply_markup=cancel_kb())


@router.message(AddUchaskavoy.waiting_fio)
async def add_get_fio(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga qaytish":
        await state.clear()
        await message.answer("❌ Qo‘shish bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
        return

    await state.update_data(fio=message.text)
    await state.set_state(AddUchaskavoy.waiting_phone)
    await message.answer("📞 Telefon raqamini kiriting:", reply_markup=cancel_kb())


@router.message(AddUchaskavoy.waiting_phone)
async def add_get_phone(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga qaytish":
        await state.clear()
        await message.answer("❌ Qo‘shish bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
        return

    await state.update_data(phone=message.text)
    await state.set_state(AddUchaskavoy.waiting_tg_id)
    await message.answer("🆔 Telegram ID raqamini kiriting:", reply_markup=cancel_kb())


@router.message(AddUchaskavoy.waiting_tg_id)
async def add_get_tg_id(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga qaytish":
        await state.clear()
        await message.answer("❌ Qo‘shish bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
        return

    data = await state.get_data()
    add_uchaskavoy(
        fio=data["fio"],
        telefon=data["phone"],
        tg_id=int(message.text),
        mahalla_id=data["mahalla_id"]
    )
    await state.clear()
    await message.answer("✅ Profilaktika inspektori muvaffaqiyatli qo‘shildi!",
                         reply_markup=types.ReplyKeyboardRemove())


# --- O‘zgartirish jarayoni ---
@router.callback_query(F.data.startswith("adm_edit_"))
async def start_edit_uchaskavoy(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    mahalla_id = int(callback.data.split("_")[2])
    uchaskavoy = get_uchaskavoy_by_mahalla(mahalla_id)
    if not uchaskavoy:
        await callback.message.answer("Profilaktika inspektori topilmadi.")
        return

    await state.update_data(mahalla_id=mahalla_id)
    await state.set_state(EditUchaskavoy.waiting_fio)
    await callback.message.answer(f"✏️ Yangi F.I.O. kiriting (hozirgi: {uchaskavoy[1]}):", reply_markup=cancel_kb())


@router.message(EditUchaskavoy.waiting_fio)
async def edit_get_fio(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga qaytish":
        await state.clear()
        await message.answer("❌ O‘zgartirish bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
        return

    await state.update_data(fio=message.text)
    await state.set_state(EditUchaskavoy.waiting_phone)
    await message.answer("📞 Yangi telefon raqamini kiriting:", reply_markup=cancel_kb())


@router.message(EditUchaskavoy.waiting_phone)
async def edit_get_phone(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga qaytish":
        await state.clear()
        await message.answer("❌ O‘zgartirish bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
        return

    await state.update_data(phone=message.text)
    await state.set_state(EditUchaskavoy.waiting_tg_id)
    await message.answer("🆔 Yangi Telegram ID kiriting:", reply_markup=cancel_kb())


@router.message(EditUchaskavoy.waiting_tg_id)
async def edit_get_tg_id(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga qaytish":
        await state.clear()
        await message.answer("❌ O‘zgartirish bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
        return

    data = await state.get_data()
    update_uchaskavoy(
        mahalla_id=data["mahalla_id"],
        fio=data["fio"],
        telefon=data["phone"],
        tg_id=int(message.text)
    )
    await state.clear()
    await message.answer("✅ Profilaktika inspektori yangilandi!", reply_markup=types.ReplyKeyboardRemove())


# --- O‘chirish ---
@router.callback_query(F.data.startswith("adm_del_"))
async def delete_uchaskavoy_cb(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    mahalla_id = int(callback.data.split("_")[2])
    delete_uchaskavoy(mahalla_id)
    await callback.message.answer("🗑 Profilaktika inspektori o‘chirildi.")
