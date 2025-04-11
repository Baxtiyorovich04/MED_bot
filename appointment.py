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
        await message.answer(translations[lang]['enter_name'])
        await state.set_state(AppointmentStates.waiting_for_name)
    except Exception as e:
        print(f"Error in start_appointment: {e}")
        await message.answer(translations[lang]['error_occurred'])
        await state.clear()

async def process_name(message: types.Message, state: FSMContext, lang: str):
    """Process the user's name"""
    try:
        # Store the name in state
        await state.update_data(name=message.text)
        
        # Create keyboard with contact button
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=translations[lang]['share_contact'], request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        # Send message with contact button
        await message.answer(
            translations[lang]['enter_phone'],
            reply_markup=keyboard
        )
        
        # Set state to waiting for phone
        await state.set_state(AppointmentStates.waiting_for_phone)
        
    except Exception as e:
        print(f"Error in process_name: {e}")
        await message.answer(translations[lang]['error_occurred'])
        await state.clear()

async def process_phone(message: types.Message, state: FSMContext, lang: str):
    try:
        # Get phone number from message
        if message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text.strip()
        
        # Format phone number
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        if not phone.startswith('+'):
            phone = '+' + phone
        
        # Store the formatted phone number
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
        
        # Remove the contact keyboard
        remove_keyboard = types.ReplyKeyboardRemove()
        
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
    try:
        # Get the date from callback data
        if message.text.startswith('date_'):
            date_type = message.text.split('_')[1]
            if date_type == 'today':
                date = translations[lang]['today']
            elif date_type == 'tomorrow':
                date = translations[lang]['tomorrow']
            elif date_type == 'day_after_tomorrow':
                date = translations[lang]['day_after_tomorrow']
            else:
                date = translations[lang]['other_date']
        else:
            date = message.text
            
        # Store the date in state
        await state.update_data(date=date)
        
        # Create service selection keyboard with 2 buttons per row
        keyboard = InlineKeyboardBuilder()
        
        # Add service buttons in 2 columns
        for service_id, service in services[lang].items():
            # Shorten service name if needed
            service_name = service['name']
            if len(service_name) > 20:  # Allow slightly longer names
                service_name = service_name[:20] + "..."
            
            keyboard.button(
                text=service_name,
                callback_data=f"appointment_service_{service_id}"
            )
        
        # Adjust to 2 columns and add back button
        keyboard.adjust(2)
        keyboard.button(text=translations[lang]['back'], callback_data="back_to_main")
        
        # Send service selection message
        await message.answer(
            translations[lang]['select_service'],
            reply_markup=keyboard.as_markup()
        )
        
        # Set state to waiting for service
        await state.set_state(AppointmentStates.waiting_for_service)
    except Exception as e:
        print(f"Error in process_date: {e}")
        await message.answer(translations[lang]['error_occurred'])
        await state.clear()

async def process_service_selection(callback: types.CallbackQuery, state: FSMContext, lang: str):
    try:
        # Get the selected service ID from the callback data
        service_id = callback.data.split('_')[-1]
        
        # Get service details
        service = services[lang][service_id]
        
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
        if ADMIN_ID:
            await callback.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message
            )
        
        # Send confirmation to user
        user_message = "✅ Запись подтверждена!\nСкоро администраторы с вами свяжутся."
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