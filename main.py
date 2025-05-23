import os
import json
import logging
import sys
import ssl
import certifi
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import ClientTimeout, ClientSession, TCPConnector, ClientError
from aiohttp.client import _RequestContextManager
from appointment import (
    AppointmentStates,
    start_appointment,
    process_name,
    process_phone,
    process_service_selection
)

# Force output to console
print("Starting bot initialization...")

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Force reconfiguration of the root logger
)
logger = logging.getLogger(__name__)

# User language storage (in production, use a database)
user_languages = {}

# Load environment variables
print("Loading environment variables...")
logger.info("Loading environment variables...")
load_dotenv()

# Get token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    error_msg = "Error: BOT_TOKEN not found in environment variables!"
    print(error_msg)
    logger.error(error_msg)
    raise ValueError(error_msg)

# Validate token format
if ":" not in BOT_TOKEN:
    error_msg = "Error: Invalid BOT_TOKEN format! Token should contain ':'"
    print(error_msg)
    logger.error(error_msg)
    raise ValueError(error_msg)

print("Bot token loaded successfully")
logger.info("Bot token loaded successfully")

# Initialize dispatcher
print("Initializing dispatcher...")
logger.info("Initializing dispatcher...")
dp = Dispatcher()

# Load data files
print("Loading data files...")
logger.info("Loading data files...")
try:
    with open('data/translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)
        print("Translations loaded successfully")
        logger.info("Translations loaded successfully")

    with open('data/services.json', 'r', encoding='utf-8') as f:
        services = json.load(f)
        print("Services loaded successfully")
        logger.info("Services loaded successfully")

    with open('data/contacts.json', 'r', encoding='utf-8') as f:
        contacts = json.load(f)
        print("Contacts loaded successfully")
        logger.info("Contacts loaded successfully")
except Exception as e:
    print(f"Error loading data files: {e}")
    logger.error(f"Error loading data files: {e}")
    raise

# Language selection keyboard
def get_language_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Русский 🇷🇺", callback_data="lang_ru")
    keyboard.button(text="O'zbek 🇺🇿", callback_data="lang_uz")
    return keyboard.as_markup()

# Main menu keyboard
def get_main_menu_keyboard(lang):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=translations[lang]['contacts'], callback_data="show_contacts")
    keyboard.button(text=translations[lang]['appointment'], callback_data="start_appointment")
    keyboard.button(text=translations[lang]['about_clinic'], callback_data="about_clinic")
    return keyboard.as_markup()

# Start command handler
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Выберите язык / Tilni tanlang",
        reply_markup=get_language_keyboard()
    )

# Language selection handler
@dp.callback_query(lambda c: c.data.startswith('lang_'))
async def process_language_selection(callback: types.CallbackQuery):
    lang = callback.data.split('_')[1]
    user_id = callback.from_user.id
    
    # Store user's language preference
    user_languages[user_id] = lang
    
    await callback.message.answer(
        translations[lang]['welcome'],
        reply_markup=get_main_menu_keyboard(lang)
    )
    await callback.answer()

# Contacts handler
@dp.callback_query(lambda c: c.data == "show_contacts")
async def show_contacts(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    keyboard = InlineKeyboardBuilder()
    # Add buttons in a column
    keyboard.button(text=translations[lang]['location'], callback_data="contact_location")
    keyboard.button(text=translations[lang]['video'], callback_data="contact_video")
    keyboard.button(text=translations[lang]['call'], callback_data="contact_call")
    keyboard.button(text=translations[lang]['back'], callback_data="back_to_main")
    
    await callback.message.edit_text(
        translations[lang]['contact_info'],
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

# Contact information handlers
@dp.callback_query(lambda c: c.data.startswith('contact_'))
async def process_contact_info(callback: types.CallbackQuery):
    info_type = callback.data.split('_')[1]
    user_id = callback.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    try:
        if info_type == 'location':
            location = contacts[lang]['location']
            try:
                # Send location first
                await callback.message.answer_location(
                    latitude=location['latitude'],
                    longitude=location['longitude']
                )
                # Then send caption
                await callback.message.answer(translations[lang]['location_caption'])
                
                # Also send video
                video_path = f"data/videos/location.mp4"
                if os.path.exists(video_path):
                    video_file = FSInputFile(video_path)
                    await callback.message.answer_video(
                        video=video_file,
                        caption=translations[lang]['video_caption']
                    )
                else:
                    await callback.message.answer(f"⚠️ Видео недоступно: {video_path}")
            except Exception as e:
                print(f"Error sending location/video: {e}")
                await callback.message.answer(f"⚠️ Ошибка при отправке: {str(e)}")
                
        elif info_type == 'video':
            try:
                video_path = f"data/videos/clinic.mp4"
                if os.path.exists(video_path):
                    video_file = FSInputFile(video_path)
                    await callback.message.answer_video(
                        video=video_file,
                        caption=translations[lang]['video_caption']
                    )
                else:
                    await callback.message.answer(f"⚠️ Видео недоступно: {video_path}")
            except Exception as e:
                print(f"Error sending video: {e}")
                await callback.message.answer(f"⚠️ Ошибка при отправке видео: {str(e)}")
                
        elif info_type == 'call':
            phone = contacts[lang]['phone']
            # Format phone number for URL (remove spaces)
            formatted_phone = phone.replace(" ", "")
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text=translations[lang]['call'], url=f"tg://resolve?phone={formatted_phone.lstrip('+')}")
            await callback.message.answer(
                f"📞 {phone}",
                reply_markup=keyboard.as_markup()
            )
        
        await callback.answer()
    except Exception as e:
        print(f"Error in contact handler: {e}")
        await callback.message.answer(f"⚠️ Произошла ошибка: {str(e)}")
        await callback.answer()

# About clinic handler
@dp.callback_query(lambda c: c.data == "about_clinic")
async def about_clinic(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=translations[lang]['back'], callback_data="back_to_main")
    
    await callback.message.edit_text(
        translations[lang]['about_clinic_text'],
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

# Back button handlers
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    await callback.message.edit_text(
        translations[lang]['welcome'],
        reply_markup=get_main_menu_keyboard(lang)
    )
    await callback.answer()

# Appointment handler
@dp.callback_query(lambda c: c.data == "start_appointment")
async def appointment_start_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_languages.get(user_id, 'ru')
    await start_appointment(callback.message, state, lang)
    await callback.answer()

# Appointment handlers
@dp.message(AppointmentStates.waiting_for_name)
async def appointment_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, 'ru')
    await process_name(message, state, lang)

@dp.message(AppointmentStates.waiting_for_phone)
async def appointment_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, 'ru')
    await process_phone(message, state, lang)

@dp.callback_query(lambda c: c.data == "make_another_appointment")
async def make_another_appointment(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_languages.get(user_id, 'ru')
    await start_appointment(callback.message, state, lang)
    await callback.answer()

async def main():
    bot = None
    session = None
    try:
        print("Starting bot...")
        logger.info("Starting bot...")
        
        # Create SSL context
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Create connector with SSL context
        connector = TCPConnector(ssl=ssl_context)
        
        # Create session with timeout
        timeout = ClientTimeout(total=30)
        session = ClientSession(connector=connector, timeout=timeout)
        
        # Create bot with custom session
        bot = Bot(token=BOT_TOKEN, session=session)
        bot.parse_mode = "HTML"
        
        # Test the bot connection
        try:
            bot_info = await bot.get_me()
            print(f"Bot connected successfully! Bot username: @{bot_info.username}")
            logger.info(f"Bot connected successfully! Bot username: @{bot_info.username}")
        except Exception as e:
            error_msg = f"Failed to connect to Telegram: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            raise
        
        # Start polling with proper cleanup
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=True,
            polling_timeout=30,
            drop_pending_updates=True,
            close_bot_session=True
        )
    except Exception as e:
        error_msg = f"Error starting bot: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        raise
    finally:
        # Close bot session
        if bot:
            await bot.session.close()
        # Close aiohttp session
        if session:
            await session.close()

if __name__ == '__main__':
    try:
        print("Starting application...")
        logger.info("Starting application...")
        import asyncio
        
        # Set longer timeout for Windows
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the main function
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Clean up the event loop
        loop.close()

  
