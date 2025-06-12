import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

LLM_API_KEY = os.getenv("LLM_API_KEY")

genai.configure(api_key=LLM_API_KEY)
model = genai.GenerativeModel(os.getenv("MODEL"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_history = {}

async def get_ai_response(user_id: int, text: str) -> str:
    try:
        if user_id not in user_history:
            user_history[user_id] = []

        user_history[user_id].append(f'User: {text}')
        recent_history = user_history[user_id][-10:]
        full_prompt = "\n\nConversation History: \n" + "\n".join(recent_history)

        response = model.generate_content(full_prompt)
        user_history[user_id].append(f"AlatauLLM: {response.text}")

        return response.text
    except Exception as e:
        return "Кешіріңіз, қазір жауап бере алмаймын"

@dp.message(Command("start"))
async def start_command(message: Message):
    greeting = """🇰🇿 Сәлеметсіз бе! AlatauLLM'ға қош келдіңіз!

Мен сізбен қазақ тілінде сөйлесе алатын ИИ боспанымын. Маған кез келген сұрақ қоя аласыз:

📝 Мәтін жазу және аудару
💬 Қазақ тілінде сұхбат
📚 Білім беру сұрақтары  
🎯 Жалпы көмек

Хабарлама жіберіп, бастайық! 💫"""
    await message.answer(greeting, parse_mode='Markdown')
    
    
@dp.message()
async def echo(message: Message):
    ai_response = await get_ai_response(message.from_user.id, message.text)
    await message.answer(ai_response, parse_mode='Markdown')


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
