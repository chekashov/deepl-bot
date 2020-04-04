#!/usr/local/bin/python3
# Copyright 2020 Egor Chekashov

import logging
import configparser
from pathlib import Path as p
# import pyppeteer as pp
from aiogram import Bot, Dispatcher, executor, types

# Main config
config = configparser.ConfigParser()
config.read('../../caf.ini.php')

def debug(msg):
    if DEBUG:
        return NN + '👾 Debug: ' + msg + NN

def ini(section, key):
    return config[section][key].strip('"')

TOKEN = ini('API Settings', 'deepl_token')
EGOR = int(ini('API Settings', 'egor'))
USER_DATA = p('../../deepl-data')
N = '\n'
NN = N * 2
DEBUG = True
config.clear()

# Configure logging
logging.basicConfig(level=logging.INFO)

def user_init(file):
    file.touch()
    config['MAIN'] = {'lang': 'EN'}
    with open(file, 'w') as settings:
        config.write(settings)
    config.clear()

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Handlers
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    uid = message.chat.id
    msg = ""
    if uid != EGOR:
        return
    user_file = p(USER_DATA / f'{uid}.ini')
    if not user_file.exists():
        msg += debug("User file doesn't exist")
        user_init(user_file)
    else:
        msg += debug(f"User file exists <b>{uid}.ini</b>")
    msg += f"Hello, {message.chat.first_name}. Just send me a message "
    msg += "and I'll translate it into English. You can change the "
    msg += "translation /language at any time."
    await message.answer(msg.strip(), parse_mode='html')

@dp.message_handler(commands=['language'])
async def start(message: types.Message):
    uid = message.chat.id
    msg = ""
    if uid != EGOR:
        return
    await message.answer(msg.strip(), parse_mode='html')

@dp.message_handler()
async def echo(message: types.Message):
    uid = message.chat.id
    msg = ""
    if uid != EGOR:
        return
    await message.answer(message.text)

if __name__ == '__main__':
    if not USER_DATA.exists():
        print("There's no directory for storing settings, fixing...")
        USER_DATA.mkdir()
    executor.start_polling(dp, skip_updates=True)
