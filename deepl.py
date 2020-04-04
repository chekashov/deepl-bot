#!/usr/local/bin/python3
# Copyright 2020 Egor Chekashov

import logging
import configparser
import pyppeteer
from aiogram import Bot, Dispatcher, executor, types

# Read config
config = configparser.ConfigParser()
config.read('../../caf.ini.php')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=config['API Settings']['caf_token'])
dp = Dispatcher(bot)

# Handlers
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
