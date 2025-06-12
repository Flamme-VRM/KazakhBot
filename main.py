import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

LLM_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=LLM_API_KEY)
model = genai.GenerativeModel(os.getenv("MODEL"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def st(message: Message):
    ai_response = await get_ai_response(message.from_user.id, message.text)
    await message.answer(ai_response)

@dp.message()
async def echo(message: Message):
    await message.answer(message.text)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

