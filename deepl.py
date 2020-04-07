#!/usr/local/bin/python3
# Copyright 2020 Egor Chekashov
# DeepL Telegram v0.3

import logging
import configparser
import time as t
import random as rnd
from pathlib import Path as p
import asyncio
import pyppeteer as pp
from aiogram import Bot, Dispatcher, executor, types


# Main config
def ini(section, key):
    """ Removes double quotes when parsing an ini file
    """
    return config[section][key].strip('"')

config = configparser.ConfigParser()
config.read('../../caf.ini.php')
TOKEN = ini('API Settings', 'deepl_token')
ADMIN = int(ini('API Settings', 'egor'))
TESTERS = (
    int(ini('API Settings', 'jenya')),
    int(ini('API Settings', 'vika'))
)
USER_DATA = p('../../deepl-data')
config.clear()

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

BASE_URL = "https://www.deepl.com/translator"
TRG = '[dl-test="translator-target-input"]'
TRG_JS = "document.querySelector('" + TRG + "').value"
ROW_WIDTH = 2 # Inline keyboard
N = "\n"
LANG = {
    'de': 'German',
    'fr': 'French',
    'es': 'Spanish',
    'it': 'Italian',
    'nl': 'Dutch',
    'pl': 'Polish',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'en': 'English',
    # 'pt-br': 'Portuguese (Brazilian)'
}
PHRASES = (
    "All right, let\'s see 🔎",
    "Give me a second, please ⏱",
    "Looking for better options 👀",
    "Great, new challenge 💪",
    "I\'ll be right back 🏃",
    "I need to think about it 🤔"
)


# Configure logging
logging.basicConfig(level=logging.INFO)

def user_init(file, uid):
    """ Creates a new (Chat ID).ini file
    """
    file.touch()
    if uid != ADMIN:
        config['MAIN'] = {'lang': 'en'}
    else:
        config['MAIN'] = {'lang': 'en',
                          'forward': 'yes',
                          'debug': 'yes',
                          'public': 'no'}
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

def set_conf(uid, key, value):
    """ Adds or updates the config key
    """
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    config.set('MAIN', str(key), str(value))
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

def get_conf(uid, key):
    """ Returns the config value
    """
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    value = ini('MAIN', key)
    config.clear()
    return value

def del_conf(uid, key):
    """ Removes the config key
    """
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    config.remove_option('MAIN', str(key))
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

def get_button(conf, txt):
    icon = '🔳 ' if str_to_bool(get_conf(ADMIN, conf)) else '⬜️ '
    return icon + txt

def sec_to_time(sec):
    """ Returns the formatted time H:MM:SS
    """
    sec = round(sec) if sec > 59 else sec
    h, m, s = 0, 0, 0
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    ftime = ""
    ftime += f"{h:d}:" if h else ""
    ftime += f"{m:02d}:" if m else ""
    ftime += f"{s:02d}" if h and m else f"{s:.2f} sec"
    return ftime


# Wrappers
def debug(msg, uid):
    """ Returns a debugging information if enabled
    """
    if DEBUG and (uid == ADMIN or uid in TESTERS):
        return '🛠 ' + msg + N
    return ""

def in_btn(*args, **kwargs):
    """ Alias for aiogram method
    """
    return types.InlineKeyboardButton(*args, **kwargs)

def filter_output(txt):
    txt = txt.replace(" .", "")
    return txt

def str_to_bool(txt):
    return str(txt.lower()) in ("true", "yes", "on", "1")


# Extract via pyppeteer
async def open_browser():
    browser = await pp.launch()
    page = await browser.pages()
    page = page[0]
    await page.goto(BASE_URL)
    await browser.disconnect()
    return [browser, browser.wsEndpoint]

browser, browser_ep = asyncio.run(open_browser())

async def translate(uid, txt):
    # Define variables
    global browser_ep
    browser = await pp.connect(browserWSEndpoint=browser_ep)
    page = await browser.newPage()
    lang = get_conf(uid, 'lang')
    # Sanitize input
    txt = txt.replace('\n', '%0A')
    txt = txt.replace('\t', '%09')
    txt = txt.replace('#', '%23')
    # Execute
    await page.goto(f"{BASE_URL}#*/{lang}/{txt}")
    try:
        await page.waitForFunction(TRG_JS + '.length > 0', timeout=2000)
    except pp.errors.TimeoutError:
        pass
    result = await page.evaluate(TRG_JS)
    await page.close()
    await browser.disconnect()
    return result


# Handlers
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    """ Starts the bot and creates a profile if it's a new user
    """
    # Required block
    uid = message.chat.id
    msg = ""
    if uid != ADMIN:
        await message.forward(ADMIN, message.text)
        if not PUBLIC and uid not in TESTERS:
            return
    file = p(USER_DATA / f'{uid}.ini')
    # If a new user, create an ini file
    if not file.exists():
        user_init(file, uid)
        msg += debug("New user, file was created" + N, uid)
        msg += f"Nice to meet you, {message.chat.first_name}. "
    else:
        msg += debug(f"User file exists <b>{uid}.ini</b>" + N, uid)
        msg += f"Welcome back, {message.chat.first_name}. "
    del file
    # Join and send a message
    msg += "Just send me a message and I'll translate it into English. "
    msg += "You can change the translation /language at any time."
    await message.answer(msg, parse_mode='html')


@dp.message_handler(commands=['language'])
async def language(message: types.Message):
    """ Sends an interactive message with language selection
    """
    # Required block
    uid = message.chat.id
    if uid != ADMIN:
        await message.forward(ADMIN, message.text)
        if not PUBLIC and uid not in TESTERS:
            return
    # Collect buttons for the inline keyboard
    inline_kb = types.InlineKeyboardMarkup(row_width=ROW_WIDTH)
    for r in range(0, len(LANG), ROW_WIDTH):
        args = ""
        for key in dict(list(LANG.items())[0+r:ROW_WIDTH+r]):
            args += f'in_btn("{LANG[key]}", callback_data="{key}"), '
        args = args.rstrip(', ')
        exec(f"inline_kb.row({args})", globals(), locals())
    # Send inline keyboard
    await message.answer("Choose a translation language",
                         reply_markup=inline_kb)


@dp.callback_query_handler(lambda cb: cb.data in LANG.keys())
async def inline_kb_answer(query: types.CallbackQuery):
    """ Handles callback after language selection
    """
    await query.answer("Good choice 👌")
    uid = query.message.chat.id
    msg_id = query.message.message_id
    btn = query.data
    msg = ""
    msg += debug("uid = " + str(uid), uid)
    msg += debug("msg_id = " + str(msg_id), uid)
    msg += debug("btn = " + str(btn) + N, uid)
    msg += f"Now I'll be translating into {LANG[btn]}"
    set_conf(uid, 'lang', btn)
    await bot.edit_message_text(msg, uid, msg_id)


@dp.message_handler(commands=['admin'])
async def admin_menu(message: types.Message):
    """ Sends an interactive message with admin settings
    """
    # Required block
    uid = message.chat.id
    if uid != ADMIN:
        await message.forward(ADMIN, message.text)
        return
    # Collect buttons for the inline keyboard
    inline_kb = types.InlineKeyboardMarkup(row_width=ROW_WIDTH)
    for r in range(0, len(SETTINGS), ROW_WIDTH):
        args = ""
        for key in dict(list(SETTINGS.items())[0+r:ROW_WIDTH+r]):
            args += f'in_btn("{SETTINGS[key][1]}", callback_data="{key}"), '
        args = args.rstrip(', ')
        exec(f"inline_kb.row({args})", globals(), locals())
    # Send inline keyboard
    await message.answer("Welcome back, Commander",
                         reply_markup=inline_kb)


@dp.message_handler()
async def echo_result(message: types.Message):
    """ Translates a previous message if it was not a command
    """
    # Required block
    uid = message.chat.id
    msg = ""
    if uid != ADMIN:
        await message.forward(ADMIN, message.text)
        if not PUBLIC and uid not in TESTERS:
            return
    sent = await message.answer(rnd.choice(PHRASES))
    t_start = t.time()
    result = await translate(uid, message.text)
    t_diff = (t.time() - t_start)
    msg += debug(f"Translation took {sec_to_time(t_diff)}" + N, uid)
    msg += filter_output(result)
    if filter_output(result):
        sent = await bot.edit_message_text(msg, uid, sent.message_id)
        if uid != ADMIN:
            await bot.forward_message(ADMIN, sent.chat.id,
                sent.message_id)
    else:
        await bot.delete_message(sent.chat.id, sent.message_id)


if __name__ == '__main__':
    if not USER_DATA.exists():
        print("There's no directory for storing settings, creating...")
        USER_DATA.mkdir()
    file = p(USER_DATA / f'{ADMIN}.ini')
    if not file.exists():
        print("There's no admin defaults, creating...")
        user_init(file, ADMIN)
    del file
    SETTINGS = {
        'forward':  [
                        get_conf(ADMIN, 'forward'),
                        get_button('forward', 'Forward')
                    ],
        'debug':    [
                        get_conf(ADMIN, 'debug'),
                        get_button('debug', 'Debug')
                    ],
        'public':   [
                        get_conf(ADMIN, 'public'),
                        get_button('public', 'Public')
                    ]
    }
    FORWARD = str_to_bool(SETTINGS['forward'][0])
    DEBUG = str_to_bool(SETTINGS['debug'][0])
    PUBLIC = False
    executor.start_polling(dp, skip_updates=True)
