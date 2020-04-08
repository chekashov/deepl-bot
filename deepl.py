#!/usr/local/bin/python3
# Copyright 2020 Egor Chekashov
# DeepL Telegram v0.4

import logging
import configparser
import time as t
from pathlib import Path as p
import asyncio
import pyppeteer as pp
from aiogram import Bot, Dispatcher, executor, types

VERSION = '0.4'

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


# Config management
logging.basicConfig(level=logging.INFO)

def user_init(uid, lang='en'):
    """ Creates a new (Chat ID).ini file
    """
    file = p(USER_DATA / f'{uid}.ini')
    file.touch()
    if uid != ADMIN:
        config['MAIN'] = {'lang': lang}
    else:
        config['MAIN'] = {'lang': lang,
                          'forward': 'yes',
                          'debug': 'no',
                          'public': 'yes'}
    config['STAT'] = {'version': VERSION,
                      'total': '0'}
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

def set_conf(uid, key, value, sect='MAIN'):
    """ Adds or updates the config key
    """
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    config.set(sect, str(key), str(value))
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

def inc_stat(uid, key):
    """ Increment the config value
    """
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    config.set('STAT', str(key), str(int(ini('STAT', key)) + 1))
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

def get_conf(uid, key, sect='MAIN'):
    """ Returns the config value
    """
    file = p(USER_DATA / f'{uid}.ini')
    config.read(file)
    value = ini(sect, key)
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

def check_ver(uid):
    try:
        ver = get_conf(uid, 'version', 'STAT')
    except KeyError:
        ver = None
    try:
        lang = get_conf(uid, 'lang')
    except KeyError:
        lang = 'en'
    if ver != VERSION:
        p(USER_DATA / f'{uid}.ini').unlink(missing_ok=True)
        user_init(uid, lang)


# Core functions
def get_button(conf, txt):
    icon = '🔳 ' if str_to_bool(get_conf(ADMIN, conf)) else '⬜️ '
    return icon + txt

def update_settings():
    global SETTINGS
    SETTINGS = {
        'forward': [
            get_conf(ADMIN, 'forward'),
            get_button('forward', 'Forward')
        ],
        'debug': [
            get_conf(ADMIN, 'debug'),
            get_button('debug', 'Debug')
        ],
        'public': [
            get_conf(ADMIN, 'public'),
            get_button('public', 'Public')
        ]
    }
    return SETTINGS

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

def collect_buttons(btn_dict, close=False, rw=ROW_WIDTH):
    buttons = types.InlineKeyboardMarkup(row_width=rw)
    if btn_dict is SETTINGS:
        btn_dict = update_settings()
    if close:
        btn_dict['close'] = '❌ Close'
    for r in range(0, len(btn_dict), rw):
        args = ""
        for k in dict(list(btn_dict.items())[0+r:rw+r]):
            if isinstance(btn_dict[k], str):
                args += f'in_btn("{btn_dict[k]}", '
            else:
                args += f'in_btn("{btn_dict[k][1]}", '
            args += f'callback_data="{k}"), '
        args = args.rstrip(', ')
        exec(f"buttons.row({args})", globals(), locals())
    return buttons


# Wrappers
def debug(msg, uid):
    """ Returns a debugging information if enabled
    """
    if get_glob('debug') and (uid == ADMIN or uid in TESTERS):
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
    return str(txt).lower() in ("true", "yes", "on", "1")

def get_glob(key):
    return str_to_bool(SETTINGS[key][0])

def set_glob(key, value):
    global SETTINGS
    if str(value).lower() in ("true", "yes", "on", "1"):
        SETTINGS[key][0] = 'yes'
        set_conf(ADMIN, key, 'yes')
    else:
        SETTINGS[key][0] = 'no'
        set_conf(ADMIN, key, 'no')


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
        TRG_LEN = TRG_JS + '.length > 0'
        await page.waitForFunction(TRG_LEN, timeout=10000)
    except pp.errors.TimeoutError:
        pass
    result = await page.evaluate(TRG_JS)
    # await page.screenshot({'path': 'before_close.png'})
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
        if not get_glob('public') and uid not in TESTERS:
            return
    # If a new user, create an ini file
    if not p(USER_DATA / f'{uid}.ini').exists():
        user_init(uid)
        msg += debug("New user, file was created" + N, uid)
        msg += f"Nice to meet you, {message.chat.first_name}. "
    else:
        check_ver(uid)
        msg += debug(f"User file exists <b>{uid}.ini</b>" + N, uid)
        msg += f"Welcome back, {message.chat.first_name}. "
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
    check_ver(uid)
    msg = ""
    if uid != ADMIN:
        await message.forward(ADMIN, message.text)
        if not get_glob('public') and uid not in TESTERS:
            return
    # Send inline keyboard
    inline_kb = collect_buttons(LANG, close=True)
    msg += f"I'm translating into <b>{LANG[get_conf(uid, 'lang')]}</b>"
    msg += ", but I also know other languages"
    await message.answer(msg, reply_markup=inline_kb, parse_mode='html')


@dp.callback_query_handler(lambda cb: cb.data == 'close')
async def callback_close(query: types.CallbackQuery):
    """ Handles callback after changing settings via admin menu
    """
    # Required block
    uid = query.message.chat.id
    check_ver(uid)
    msg_id = query.message.message_id
    btn = query.data
    await query.answer("Cleaning up ✨")
    await bot.delete_message(uid, msg_id)


@dp.callback_query_handler(lambda cb: cb.data in LANG.keys())
async def callback_lang(query: types.CallbackQuery):
    """ Handles callback after language selection
    """
    # Required block
    uid = query.message.chat.id
    check_ver(uid)
    msg_id = query.message.message_id
    btn = query.data
    # Apply new settings
    msg = ""
    msg += debug("uid = " + str(uid), uid)
    msg += debug("msg_id = " + str(msg_id), uid)
    msg += debug("btn = " + str(btn) + N, uid)
    msg += f"Now I'll be translating into <b>{LANG[btn]}</b>"
    set_conf(uid, 'lang', btn)
    await query.answer("Good choice 👌")
    await bot.edit_message_text(msg, uid, msg_id, parse_mode='html')


@dp.callback_query_handler(lambda cb: cb.data in SETTINGS.keys())
async def callback_admin(query: types.CallbackQuery):
    """ Handles callback after changing settings via admin menu
    """
    # Required block
    uid = query.message.chat.id
    check_ver(uid)
    msg_id = query.message.message_id
    btn = query.data
    # Apply new settings
    new_val = 0 if get_glob(btn) else 1
    msg = query.message.text
    set_glob(btn, new_val)
    await query.answer("Settings saved 👌")
    inline_kb = collect_buttons(SETTINGS, close=True)
    await bot.edit_message_text(msg, ADMIN, msg_id,
        reply_markup=inline_kb)


@dp.message_handler(commands=['a'])
async def admin_menu(message: types.Message):
    """ Sends an interactive message with admin settings
    """
    # Required block
    uid = message.chat.id
    check_ver(uid)
    if uid != ADMIN:
        await message.forward(ADMIN, message.text)
        return
    # Send inline keyboard
    inline_kb = collect_buttons(SETTINGS, close=True)
    await message.answer("Welcome back, Commander",
                         reply_markup=inline_kb)


@dp.message_handler()
async def echo_result(message: types.Message):
    """ Translates a previous message if it was not a command
    """
    # Required block
    uid = message.chat.id
    check_ver(uid)
    msg = ""
    if uid != ADMIN:
        await message.forward(ADMIN, message.text)
        if not get_glob('public') and uid not in TESTERS:
            return
    sent = await message.answer('📝')
    t_start = t.time()
    result = await translate(uid, message.text)
    t_diff = (t.time() - t_start)
    if filter_output(result):
        msg += debug(f"Translation took {sec_to_time(t_diff)}" + N, uid)
        msg += filter_output(result)
        sent = await bot.edit_message_text(msg, uid, sent.message_id)
        if uid != ADMIN:
            await bot.forward_message(ADMIN, sent.chat.id,
                sent.message_id)
    else:
        await bot.delete_message(sent.chat.id, sent.message_id)
    inc_stat(uid, 'total')


if __name__ == '__main__':
    if not USER_DATA.exists():
        print("There's no directory for storing settings, creating...")
        USER_DATA.mkdir()
    if not p(USER_DATA / f'{ADMIN}.ini').exists():
        print("There's no admin defaults, creating...")
        user_init(ADMIN)
    SETTINGS = {}
    update_settings()
    executor.start_polling(dp, skip_updates=True)
