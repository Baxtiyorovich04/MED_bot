from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
import os

# Load data files
with open('data/translations.json', 'r', encoding='utf-8') as f:
    translations = json.load(f)

with open('data/services.json', 'r', encoding='utf-8') as f:
    services = json.load(f)

# Load admin ID from environment variable
try:
    admin_id_str = os.getenv("ADMIN_ID", "0")
    # Remove any comments or extra spaces
    admin_id_str = admin_id_str.split('#')[0].strip()
    ADMIN_ID = int(admin_id_str)
except (ValueError, TypeError):
    print("Warning: Invalid ADMIN_ID in .env file. Admin notifications will be disabled.")
    ADMIN_ID = 0

class AppointmentStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_service = State()

async def start_appointment(message: types.Message, state: FSMContext, lang: str):
    """Start the appointment process"""
    await state.set_state(AppointmentStates.waiting_for_name)
    await message.answer(translations[lang]['enter_name'])

async def process_name(message: types.Message, state: FSMContext, lang: str):
    """Process the user's name"""
    await state.update_data(name=message.text)
    await state.set_state(AppointmentStates.waiting_for_phone)
    await message.answer(translations[lang]['enter_phone'])

async def process_phone(message: types.Message, state: FSMContext, lang: str):
    """Process the user's phone number"""
    await state.update_data(phone=message.text)
    await state.set_state(AppointmentStates.waiting_for_service)
    
    # Create service selection keyboard
    keyboard = InlineKeyboardBuilder()
    for service in services[lang]['services']:
        keyboard.button(text=service['name'], callback_data=f"appointment_service_{service['id']}")
    keyboard.button(text=translations[lang]['back'], callback_data="back_to_main")
    
    await message.answer(
        translations[lang]['select_service'],
        reply_markup=keyboard.as_markup()
    )

async def process_service_selection(callback: types.CallbackQuery, state: FSMContext, lang: str):
    """Process the selected service and forward to admin"""
    service_id = callback.data.split('_')[2]
    data = await state.get_data()
    
    # Find selected service
    selected_service = next(
        (s for s in services[lang]['services'] if s['id'] == service_id),
        None
    )
    
    if not selected_service:
        await callback.answer("Service not found")
        return
    
    # Create appointment message
    appointment_text = (
        f"📝 Новая запись!\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"🏥 Услуга: {selected_service['name']}\n"
        f"💰 Цена: {selected_service['price']}"
    )
    
    # Forward to admin
    if ADMIN_ID:
        try:
            await callback.bot.send_message(
                chat_id=ADMIN_ID,
                text=appointment_text
            )
        except Exception as e:
            print(f"Error sending admin notification: {e}")
    
    # Send confirmation to user
    await callback.message.answer(
        translations[lang]['appointment_confirmed'],
        reply_markup=get_confirmation_keyboard(lang)
    )
    
    await state.clear()
    await callback.answer()

def get_confirmation_keyboard(lang: str):
    """Create keyboard for appointment confirmation"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=translations[lang]['make_another_appointment'], callback_data="make_another_appointment")
    keyboard.button(text=translations[lang]['back_to_main'], callback_data="back_to_main")
    return keyboard.as_markup() 