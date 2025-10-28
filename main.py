# BOT_TOKEN = "5660076097:AAG__AmZ73aJHn8a7uBGBMtH8fsRUbqOHOE"

import asyncio
import os
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    create_engine,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# ----------------- CONFIG -----------------
BOT_TOKEN = "5660076097:AAG__AmZ73aJHn8a7uBGBMtH8fsRUbqOHOE"

ADMINS = [
    734373401
]
DATABASE_URL = 'sqlite:///mahalla_bot.db'

Base = declarative_base()

class Neighborhood(Base):
    __tablename__ = 'neighborhoods'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    inspector_id = Column(Integer, ForeignKey('inspectors.id'), nullable=True)

    inspector = relationship('Inspector', back_populates='neighborhood')

class Inspector(Base):
    __tablename__ = 'inspectors'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String, nullable=True)

    neighborhood = relationship('Neighborhood', uselist=False, back_populates='inspector')

class Citizen(Base):
    __tablename__ = 'citizens'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    neighborhood_id = Column(Integer, ForeignKey('neighborhoods.id'), nullable=True)

    neighborhood = relationship('Neighborhood')

class Request(Base):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)
    citizen_id = Column(Integer, ForeignKey('citizens.id'))
    neighborhood_id = Column(Integer, ForeignKey('neighborhoods.id'))
    content_type = Column(String)
    content_text = Column(Text, nullable=True)
    file_id = Column(String, nullable=True)
    location_lat = Column(String, nullable=True)
    location_lon = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    citizen = relationship('Citizen')
    neighborhood = relationship('Neighborhood')

# SQLAlchemy sozlamalari
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)

class RegisterStates(StatesGroup):
    waiting_name = State()
    waiting_neighborhood = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def init_db():
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()

# ---------- ADMIN COMMANDLAR ----------
@dp.message(Command('add_neighborhood'))
async def add_neighborhood_handler(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply('Siz admin emassiz.')
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply('Foydalanish: /add_neighborhood <nomi>')
        return
    name = args[1].strip()
    session = get_session()
    try:
        nb = Neighborhood(name=name)
        session.add(nb)
        session.commit()
        await message.reply(f'Mahalla qo‘shildi: {name} (id={nb.id})')
    except Exception:
        session.rollback()
        await message.reply('Xatolik: bu nom allaqachon mavjud.')
    finally:
        session.close()

@dp.message(Command('list_neighborhoods'))
async def list_neighborhoods(message: types.Message):
    session = get_session()
    nbs = session.query(Neighborhood).all()
    if not nbs:
        await message.reply('Mahallalar mavjud emas.')
    else:
        text = 'Mahallalar:\n'
        for n in nbs:
            insp = f'{n.inspector.telegram_id}' if n.inspector else '—'
            text += f'id={n.id} | {n.name} | inspektor: {insp}\n'
        await message.reply(text)
    session.close()

@dp.message(Command('assign_inspector'))
async def assign_inspector(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.reply('Siz admin emassiz.')
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply('Foydalanish: /assign_inspector <neighborhood_id> <inspector_tg_id>')
        return
    nb_id = int(parts[1])
    insp_tid = int(parts[2])
    session = get_session()
    nb = session.query(Neighborhood).filter_by(id=nb_id).first()
    if not nb:
        await message.reply('Bunday mahalla topilmadi.')
        session.close()
        return
    inspector = session.query(Inspector).filter_by(telegram_id=insp_tid).first()
    if not inspector:
        inspector = Inspector(telegram_id=insp_tid)
        session.add(inspector)
        session.commit()
    nb.inspector = inspector
    session.add(nb)
    session.commit()
    await message.reply(f'Inspektor {insp_tid} mahalla {nb.name} ga biriktirildi.')
    session.close()

# ---------- USER REGISTRATSIYA ----------
@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    session = get_session()
    citizen = session.query(Citizen).filter_by(telegram_id=message.from_user.id).first()
    if citizen:
        await message.reply('Siz ro‘yxatdan o‘tgansiz. Endi murojaat yuborishingiz mumkin.')
    else:
        await message.reply('Assalomu alaykum! To‘liq ismingizni yuboring:')
        await state.set_state(RegisterStates.waiting_name)
    session.close()

@dp.message(StateFilter(RegisterStates.waiting_name))
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(full_name=name)
    session = get_session()
    nbs = session.query(Neighborhood).all()
    if not nbs:
        await message.reply('Mahallalar mavjud emas. Admin bilan bog‘laning.')
        await state.clear()
        session.close()
        return
    kb = InlineKeyboardMarkup(row_width=1)
    for n in nbs:
        kb.add(InlineKeyboardButton(text=n.name, callback_data=f'reg_nb:{n.id}'))
    await message.reply('Qaysi mahallada yashaysiz?', reply_markup=kb)
    await state.set_state(RegisterStates.waiting_neighborhood)
    session.close()

@dp.callback_query(F.data.startswith('reg_nb:'), StateFilter(RegisterStates.waiting_neighborhood))
async def reg_select_neighborhood(callback: types.CallbackQuery, state: FSMContext):
    nb_id = int(callback.data.split(':', 1)[1])
    data = await state.get_data()
    full_name = data.get('full_name')
    session = get_session()
    nb = session.query(Neighborhood).filter_by(id=nb_id).first()
    if not nb:
        await callback.message.answer('Tanlangan mahalla topilmadi.')
        await state.clear()
        session.close()
        return
    citizen = Citizen(telegram_id=callback.from_user.id, full_name=full_name, neighborhood=nb)
    session.add(citizen)
    session.commit()
    await callback.message.answer(f'Registratsiya muvaffaqiyatli!\nIsm: {full_name}\nMahalla: {nb.name}')
    await state.clear()
    session.close()
    await callback.answer()

# ---------- MUROJAATLAR ----------
@dp.message()
async def handle_user_request(message: types.Message):
    session = get_session()
    citizen = session.query(Citizen).filter_by(telegram_id=message.from_user.id).first()
    if not citizen:
        await message.reply('Avval ro‘yxatdan o‘ting: /start')
        session.close()
        return
    nb = citizen.neighborhood
    if not nb or not nb.inspector:
        await message.reply('Sizning mahallangizga inspektor biriktirilmagan.')
        session.close()
        return

    content_type, content_text, file_id, loc_lat, loc_lon = 'text', None, None, None, None

    if message.text:
        content_text = message.text
    elif message.voice:
        content_type, file_id = 'voice', message.voice.file_id
    elif message.audio:
        content_type, file_id = 'audio', message.audio.file_id
    elif message.photo:
        content_type, file_id = 'photo', message.photo[-1].file_id
    elif message.document:
        content_type, file_id = 'document', message.document.file_id
    elif message.location:
        content_type, loc_lat, loc_lon = 'location', str(message.location.latitude), str(message.location.longitude)

    req = Request(
        citizen=citizen,
        neighborhood=nb,
        content_type=content_type,
        content_text=content_text,
        file_id=file_id,
        location_lat=loc_lat,
        location_lon=loc_lon,
        created_at=datetime.utcnow(),
    )
    session.add(req)
    session.commit()

    inspector_tg = nb.inspector.telegram_id
    header = (f"📩 Yangi murojaat (id={req.id})\n"
              f"👤 {citizen.full_name}\n🏠 {nb.name}\n🕓 {req.created_at:%Y-%m-%d %H:%M:%S}\n")

    try:
        await bot.send_message(inspector_tg, header)
        if content_type == 'text':
            await bot.send_message(inspector_tg, content_text)
        elif content_type == 'voice':
            await bot.send_voice(inspector_tg, file_id)
        elif content_type == 'audio':
            await bot.send_audio(inspector_tg, file_id)
        elif content_type == 'photo':
            await bot.send_photo(inspector_tg, file_id)
        elif content_type == 'document':
            await bot.send_document(inspector_tg, file_id)
        elif content_type == 'location':
            await bot.send_location(inspector_tg, float(loc_lat), float(loc_lon))
    except Exception as e:
        await message.reply('Murojaat qabul qilindi, ammo inspektorga yuborilmadi.')
        for admin in ADMINS:
            await bot.send_message(admin, f'Xatolik: {e}')
        session.close()
        return

    await message.reply('✅ Murojaatingiz yuborildi.')
    session.close()

async def main():
    init_db()
    print('Bot ishga tushdi...')
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        asyncio.run(bot.session.close())

