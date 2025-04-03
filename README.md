# Medical Center Telegram Bot

A Telegram bot for a medical center that provides information about services, contacts, and allows patients to make appointments.

## Features

- Bilingual support (Russian and Uzbek)
- Service catalog with prices
- Contact information with location
- Appointment booking system
- Interactive menus and buttons

## Setup

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your Telegram bot token:

```
BOT_TOKEN=your_bot_token_here
```

4. Update the following files with your specific information:

- `data/contacts.json` - Update clinic address, phone, and location coordinates
- `data/services.json` - Update service categories and prices
- `data/translations.json` - Update translations if needed

## Running the Bot

To start the bot, run:

```bash
python main.py
```

## Project Structure

- `main.py` - Main bot file with handlers and core functionality
- `appointment.py` - Appointment booking system
- `data/` - Directory containing JSON files with bot data
  - `translations.json` - Text translations for both languages
  - `services.json` - Service catalog and prices
  - `contacts.json` - Contact information

## Contributing

Feel free to submit issues and enhancement requests!
