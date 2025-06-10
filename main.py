import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message()
async def echo(message: Message):
    await message.answer(message.text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

