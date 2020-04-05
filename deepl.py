#!/usr/local/bin/python3
# Copyright 2020 Egor Chekashov
# DeepL Telegram v0.1

import logging
import configparser
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
ADMINS = [int(ini('API Settings', 'egor'))]
ADMINS += [int(ini('API Settings', 'jenya'))]
ADMINS += [int(ini('API Settings', 'vika'))]
USER_DATA = p('../../deepl-data')
config.clear()

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

BASE_URL = "https://www.deepl.com/translator"
SELECTOR = '[dl-test="translator-target-input"]'
JS_STR = "document.querySelector('" + SELECTOR + "').value"
DEBUG = True
PUBLIC = False
ROW_WIDTH = 2
N = "\n"
LANG = {
    'en': 'English',
    'de': 'German',
    'fr': 'French',
    'es': 'Spanish',
    'it': 'Italian',
    'nl': 'Dutch',
    'pl': 'Polish',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'pt': 'Portuguese',
    'pt-br': 'Portuguese (BR)'
}
PHRASES = (
    "Got it, let me see"
)


# Configure logging
logging.basicConfig(level=logging.INFO)

def user_init(file):
    file.touch()
    config['MAIN'] = {'lang': 'en'}
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

def set_conf(uid, key, value):
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    config.set('MAIN', str(key), str(value))
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

def get_conf(uid, key):
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    value = ini('MAIN', key)
    config.clear()
    return value

def del_conf(uid, key):
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    config.remove_option('MAIN', str(key))
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()


# Wrappers
def debug(msg):
    """ Returns a message if debug is enabled
    """
    if DEBUG:
        return '👾 Debug: ' + msg + N
    return ""

def in_btn(*args, **kwargs):
    return types.InlineKeyboardButton(*args, **kwargs)


# Extract via pyppeteer
async def translate(uid, txt):
    lang = get_conf(uid, 'lang')
    browser = await pp.launch()
    page = await browser.newPage()
    await page.goto(f"{BASE_URL}#*/{lang}/{txt}")
    await page.waitForFunction(JS_STR + '.length > 0')
    result = await page.evaluate(JS_STR)
    await browser.close()
    return result


# Handlers
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    # Required block
    uid = message.chat.id
    msg = ""
    if not uid in ADMINS:
        await message.forward(ADMINS[0], message.text)
        if not PUBLIC:
            return
    file = p(USER_DATA / f'{uid}.ini')
    # If a new user, create an ini file
    if not file.exists():
        user_init(file)
        msg += debug("New user, file was created" + N)
        msg += f"Nice to meet you, {message.chat.first_name}. "
    else:
        msg += debug(f"User file exists <b>{uid}.ini</b>" + N)
        msg += f"Welcome back, {message.chat.first_name}. "
    # Join and send a message
    msg += "Just send me a message and I'll translate it into English. "
    msg += "You can change the translation /language at any time."
    await message.answer(msg, parse_mode='html')


@dp.message_handler(commands=['language'])
async def language(message: types.Message):
    # Required block
    uid = message.chat.id
    if not uid in ADMINS:
        await message.forward(ADMINS[0], message.text)
        if not PUBLIC:
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
    await query.answer("Good choice 👌")
    uid = query.message.chat.id
    msg_id = query.message.message_id
    btn = query.data
    msg = ""
    msg += debug("uid = " + str(uid))
    msg += debug("msg_id = " + str(msg_id))
    msg += debug("btn = " + str(btn) + N)
    msg += f"Now I'll be translating into {LANG[btn]}"
    set_conf(uid, 'lang', btn)
    await bot.edit_message_text(msg, uid, msg_id)


@dp.message_handler()
async def echo(message: types.Message):
    # Required block
    uid = message.chat.id
    msg = "1"
    if not uid in ADMINS:
        await message.forward(ADMINS[0], message.text)
        if not PUBLIC:
            return
    msg = await translate(uid, message.text)
    await message.answer(msg)


if __name__ == '__main__':
    if not USER_DATA.exists():
        print("There's no directory for storing settings, creating...")
        USER_DATA.mkdir()
    executor.start_polling(dp, skip_updates=True)
