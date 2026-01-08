import asyncio
import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import requests
import random  # For creative phrases

# Log settings (optional, for debugging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# States for ConversationHandler
LANGUAGE, CURRENCY = range(2)

#  Top 7 cryptocurrencies (ids for CoinGecko API) + their names and symbols
TOP_CRYPTOS = {
    'Bitcoin 💰': {'id': 'bitcoin', 'symbol': 'BTC'},
    'Ethereum 🚀': {'id': 'ethereum', 'symbol': 'ETH'},
    'Tether ⚖️': {'id': 'tether', 'symbol': 'USDT'},
    'XRP 🌊': {'id': 'ripple', 'symbol': 'XRP'},
    'BNB 🔥': {'id': 'binancecoin', 'symbol': 'BNB'},
    'USDC 🔵': {'id': 'usd-coin', 'symbol': 'USDC'},
    'Solana ☀️': {'id': 'solana', 'symbol': 'SOL'}
}

# Translations for two languages
TRANSLATIONS = {
    'en': {
        'welcome': "Welcome! Choose your language: 🇬🇧",
        'select_lang': [["English 🇬🇧", "Українська 🇺🇦"]],
        'select_currency': "Awesome! Now pick a crypto or just type its name/symbol (e.g., BTC) 💹",
        'back': "Back 🔙",
        'info_template': "{name} ({symbol}) {emoji}\nCurrent Price: ${price:.2f} USD\n1h Change: {change_1h:.2f}% {change_emoji}\nMarket Cap: ${market_cap:,.0f}\n24h Volume: ${volume:,.0f}\n24h High: ${high_24h:.2f}\n24h Low: ${low_24h:.2f}\nAll-Time High: ${ath:.2f} (on {ath_date})\n{fun_phrase}",
        'not_found': "Oops, couldn't find that crypto 😕 Try again or pick from buttons!",
        'error': "Whoops, something went wrong! Try later 🛠️",
        'fun_phrases_positive': ["It's blasting off! 🚀", "Mooning hard! 🌕", "You're a crypto wizard! 🧙‍♂️"],
        'fun_phrases_negative': ["A little dip, but it'll bounce! 🏀", "Hold tight! 💪", "Time to buy low? 📉"],
        'fun_phrases_neutral': ["Steady as she goes! ⚓", "Chilling in the market ❄️"]
    },
    'ua': {
        'welcome': "Вітаю! Оберіть мову: 🇺🇦",
        'select_lang': [["English 🇬🇧", "Українська 🇺🇦"]],
        'select_currency': "Чудово! Оберіть крипту або просто напишіть її назву/символ (наприклад, BTC) 💹",
        'back': "Назад 🔙",
        'info_template': "{name} ({symbol}) {emoji}\nПоточна ціна: ${price:.2f} USD\nЗміна за 1г: {change_1h:.2f}% {change_emoji}\nРинкова кап: ${market_cap:,.0f}\nОб'єм за 24г: ${volume:,.0f}\n24г Макс: ${high_24h:.2f}\n24г Мін: ${low_24h:.2f}\nІсторичний макс: ${ath:.2f} (від {ath_date})\n{fun_phrase}",
        'not_found': "Ой, не знайшов таку крипту 😕 Спробуйте ще або оберіть з кнопок!",
        'error': "Упс, щось пішло не так! Спробуйте пізніше 🛠️",
        'fun_phrases_positive': ["Летить вгору! 🚀", "На Місяць! 🌕", "Ти крипто-гуру! 🧙‍♂️"],
        'fun_phrases_negative': ["Трохи просів, але відскочить! 🏀", "Тримайся! 💪", "Час купувати дешево? 📉"],
        'fun_phrases_neutral': ["Стабільно йде! ⚓", "Відпочиває на ринку ❄️"]
    }
}

# Function for retrieving data from CoinGecko
async def get_crypto_data(crypto_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}"
        response = requests.get(url)
        data = response.json()
        return {
            'name': data['name'],
            'symbol': data['symbol'].upper(),
            'price': data['market_data']['current_price']['usd'],
            'change_1h': data['market_data']['price_change_percentage_1h_in_currency']['usd'],
            'market_cap': data['market_data']['market_cap']['usd'],
            'volume': data['market_data']['total_volume']['usd'],
            'high_24h': data['market_data']['high_24h']['usd'],
            'low_24h': data['market_data']['low_24h']['usd'],
            'ath': data['market_data']['ath']['usd'],
            'ath_date': data['market_data']['ath_date']['usd'][:10],  # YYYY-MM-DD
        }
    except:
        return None

# Function to search for id by name or symbol
async def search_crypto(query):
    try:
        url = f"https://api.coingecko.com/api/v3/search?query={query}"
        response = requests.get(url)
        results = response.json()['coins']
        if results:
            return results[0]['id']  
        return None
    except:
        return None

# Handler for /star
async def start(update: Update, context) -> int:
    reply_markup = ReplyKeyboardMarkup(TRANSLATIONS['en']['select_lang'], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(TRANSLATIONS['en']['welcome'], reply_markup=reply_markup)
    return LANGUAGE

# Language selection handler
async def select_language(update: Update, context) -> int:
    text = update.message.text
    if text == "English 🇬🇧":
        context.user_data['lang'] = 'en'
    elif text == "Українська 🇺🇦":
        context.user_data['lang'] = 'ua'
    else:
        await update.message.reply_text("Please choose from buttons! / Будь ласка, оберіть з кнопок!")
        return LANGUAGE

    lang = context.user_data['lang']
    # Keyboard with top crypto + Back (in 3 rows)
    keyboard = [
        [list(TOP_CRYPTOS.keys())[0], list(TOP_CRYPTOS.keys())[1], list(TOP_CRYPTOS.keys())[2]],
        [list(TOP_CRYPTOS.keys())[3], list(TOP_CRYPTOS.keys())[4], list(TOP_CRYPTOS.keys())[5]],
        [list(TOP_CRYPTOS.keys())[6], TRANSLATIONS[lang]['back']]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(TRANSLATIONS[lang]['select_currency'], reply_markup=reply_markup)
    return CURRENCY

# Crypto selection handler (button or text)
async def select_currency(update: Update, context) -> int:
    lang = context.user_data.get('lang', 'en')
    text = update.message.text.strip()

    if text == TRANSLATIONS[lang]['back']:
        return await start(update, context)  # Back to language selection

    # If the button is at the top (remove the emoji for search)
    crypto_name = text.split(' ')[0] if ' ' in text else text
    crypto = TOP_CRYPTOS.get(text) or TOP_CRYPTOS.get(crypto_name + ' ' + text.split(' ')[-1])  

    if crypto:
        crypto_id = crypto['id']
    else:
        # Search by text
        crypto_id = await search_crypto(text)
        if not crypto_id:
            await update.message.reply_text(TRANSLATIONS[lang]['not_found'])
            return CURRENCY

    data = await get_crypto_data(crypto_id)
    if not data:
        await update.message.reply_text(TRANSLATIONS[lang]['error'])
        return CURRENCY

    # Emojis for crypto (from top or default)
    emoji = next((k.split(' ')[-1] for k in TOP_CRYPTOS if TOP_CRYPTOS[k]['id'] == crypto_id), '🌟')

    # Emoji for change
    change_emoji = '📈' if data['change_1h'] > 0 else '📉' if data['change_1h'] < 0 else '⚖️'

    # Creative phrase
    if data['change_1h'] > 0:
        fun_phrase = random.choice(TRANSLATIONS[lang]['fun_phrases_positive'])
    elif data['change_1h'] < 0:
        fun_phrase = random.choice(TRANSLATIONS[lang]['fun_phrases_negative'])
    else:
        fun_phrase = random.choice(TRANSLATIONS[lang]['fun_phrases_neutral'])

    # We are creating a message
    message = TRANSLATIONS[lang]['info_template'].format(
        name=data['name'], symbol=data['symbol'], emoji=emoji, price=data['price'], change_1h=data['change_1h'],
        change_emoji=change_emoji, market_cap=data['market_cap'], volume=data['volume'],
        high_24h=data['high_24h'], low_24h=data['low_24h'], ath=data['ath'], ath_date=data['ath_date'],
        fun_phrase=fun_phrase
    )
    await update.message.reply_text(message)

    # Return to the menu (using the same keyboard)
    return CURRENCY

# Handler cancellation (if necessary)
async def cancel(update: Update, context) -> int:
    await update.message.reply_text("Bye! Use /start to begin again. / До побачення! Використовуйте /start.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main() -> None:
   
    TOKEN = "7710858537:AAGDi5cHnb16e1h7caqLgWy3mifjr3_3DA8" 
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_currency)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
