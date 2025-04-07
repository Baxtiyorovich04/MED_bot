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
    waiting_for_date = State()
    waiting_for_service = State()

async def start_appointment(message: types.Message, state: FSMContext, lang: str):
    try:
        # Create keyboard for service selection with 3 columns
        keyboard = InlineKeyboardBuilder()
        
        # Add service buttons in 3 columns
        for service_id, service in services[lang].items():
            # Shorten service name if needed
            service_name = service['name']
            if len(service_name) > 15:
                service_name = service_name[:15] + "..."
            
            keyboard.button(
                text=service_name,
                callback_data=f"appointment_service_{service_id}"
            )
        
        # Adjust to 3 columns
        keyboard.adjust(3)
        
        # Add back button
        keyboard.button(
            text=translations[lang]['back'],
            callback_data="back_to_main"
        )
        
        await message.answer(
            text=translations[lang]['select_service'],
            reply_markup=keyboard.as_markup()
        )
        
        # Set state to waiting for service selection
        await state.set_state(AppointmentStates.waiting_for_service)
        
    except Exception as e:
        print(f"Error in start_appointment: {e}")
        await message.answer(translations[lang]['error_occurred'])
        await state.clear()

async def process_name(message: types.Message, state: FSMContext, lang: str):
    """Process the user's name"""
    # Store the name in state
    await state.update_data(name=message.text)
    await state.set_state(AppointmentStates.waiting_for_phone)
    
    # Create keyboard with contact button
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=translations[lang]['send_contact'], request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(translations[lang]['enter_phone'], reply_markup=keyboard)

async def process_phone(message: types.Message, state: FSMContext, lang: str):
    try:
        # Get phone number from message
        phone = message.text
        
        # If it's a contact message, get the phone number from contact
        if message.contact:
            phone = message.contact.phone_number
        
        # Format phone number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        # Update state with phone number
        await state.update_data(phone=phone)
        
        # Create keyboard for date selection
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text=translations[lang]['today'],
            callback_data="date_today"
        )
        keyboard.button(
            text=translations[lang]['tomorrow'],
            callback_data="date_tomorrow"
        )
        keyboard.button(
            text=translations[lang]['day_after_tomorrow'],
            callback_data="date_day_after_tomorrow"
        )
        keyboard.button(
            text=translations[lang]['other_date'],
            callback_data="date_other"
        )
        
        # Add back button
        keyboard.button(
            text=translations[lang]['back'],
            callback_data="back_to_main"
        )
        
        # Adjust to 2 columns
        keyboard.adjust(2)
        
        await message.answer(
            text=translations[lang]['select_date'],
            reply_markup=keyboard.as_markup()
        )
        
        # Set state to waiting for date selection
        await state.set_state(AppointmentStates.waiting_for_date)
        
    except Exception as e:
        print(f"Error in process_phone: {e}")
        await message.answer(translations[lang]['error_occurred'])
        await state.clear()

async def process_date(message: types.Message, state: FSMContext, lang: str):
    """Process the selected date"""
    date = message.text
    await state.update_data(date=date)
    await state.set_state(AppointmentStates.waiting_for_service)
    
    # Create service selection keyboard with 2 buttons per row
    keyboard = InlineKeyboardBuilder()
    
    # Get unique services (remove duplicates)
    unique_services = []
    seen_names = set()
    for service in services[lang]['services']:
        if service['name'] not in seen_names:
            seen_names.add(service['name'])
            unique_services.append(service)
    
    # Add buttons with simplified names
    for service in unique_services:
        # Make names shorter
        if lang == 'ru':
            name = service['name'].replace('Консультация ', '').replace('Анализ ', '')
        else:
            name = service['name'].replace('konsultatsiyasi', '').replace('tahlili', '')
        keyboard.button(text=name, callback_data=f"appointment_service_{service['id']}")
    
    keyboard.button(text=translations[lang]['back'], callback_data="back_to_main")
    keyboard.adjust(2)  # Arrange buttons in 2 columns
    
    await message.answer(
        translations[lang]['select_service'],
        reply_markup=keyboard.as_markup()
    )

async def process_service_selection(callback: types.CallbackQuery, state: FSMContext, lang: str):
    try:
        # Get the selected service ID from the callback data
        service_id = callback.data.split('_')[-1]
        
        # Get service details
        service = services[lang][service_id]
        
        # Update state with selected service
        await state.update_data(service=service['name'])
        
        # Get user data
        data = await state.get_data()
        name = data.get('name', 'Не указано')
        phone = data.get('phone', 'Не указан')
        date = data.get('date', 'Не указана')
        
        # Send confirmation to admin
        admin_message = (
            f"📝 Новая запись!\n\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"📅 Дата: {date}\n"
            f"🏥 Услуга: {service['name']}"
        )
        
        # Send to admin
        await callback.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message
        )
        
        # Send confirmation to user
        user_message = translations[lang]['appointment_confirmed']
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text=translations[lang]['make_another_appointment'],
            callback_data="make_another_appointment"
        )
        
        await callback.message.edit_text(
            text=user_message,
            reply_markup=keyboard.as_markup()
        )
        await callback.answer()
        
        # Clear the state
        await state.clear()
        
    except Exception as e:
        print(f"Error in process_service_selection: {e}")
        await callback.answer(translations[lang]['error_occurred'])
        await state.clear()

def get_confirmation_keyboard(lang: str):
    """Create keyboard for appointment confirmation"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=translations[lang]['make_another_appointment'], callback_data="make_another_appointment")
    keyboard.button(text=translations[lang]['back_to_main'], callback_data="back_to_main")
    return keyboard.as_markup() 