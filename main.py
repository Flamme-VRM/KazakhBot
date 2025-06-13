"""
AlatauLLM - Kazakh AI Assistant Telegram Bot
Author: Shyngisbek Asylkhan
GitHub: https://github.com/Flamme-VRM
Description: AI assistant bot for Kazakh students with IELTS/SAT/TOEFL preparation support
"""

import asyncio
import os
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
import google.generativeai as genai

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def show_banner():
    banner = r"""
 _____ _                                   __     ______  __  __ 
|  ___| | __ _ _ __ ___  _ __ ___   ___    \ \   / /  _ \|  \/  |
| |_  | |/ _` | '_ ` _ \| '_ ` _ \ / _ \____\ \ / /| |_) | |\/| |
|  _| | | (_| | | | | | | | | | | |  __/_____\ V / |  _ <| |  | |
|_|   |_|\__,_|_| |_| |_|_| |_| |_|\___|      \_/  |_| \_\_|  |_|
    """
    print(banner)
    logger.info("AlatauLLM bot starting up...")

load_dotenv(".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

LLM_API_KEY = os.getenv("LLM_API_KEY")

genai.configure(api_key=LLM_API_KEY)
model = genai.GenerativeModel(os.getenv("MODEL"))

SYSTEM_PROMPT = """You are AlatauLLM. You're a helpful AI assistant for Kazakh students.
  - Always respond in Kazakh language
  - You can understand and help with content in any language (English, Russian, etc.)
  - Help with IELTS, SAT, TOEFL preparation and academic questions
  - Provide assessments, explanations, and guidance in Kazakh
  - Be helpful and educational while responding in Қазақ тілінде"""

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_history = {}

async def get_ai_response(user_id: int, text: str) -> str:
    try:
        if user_id not in user_history:
            user_history[user_id] = []

        user_history[user_id].append(f'User: {text}')
        
        recent_history = user_history[user_id][-10:]
        full_prompt = SYSTEM_PROMPT + "\n\nConversation History: \n" + "\n".join(recent_history)

        response = model.generate_content(full_prompt)
        user_history[user_id].append(f"AlatauLLM: {response.text}")

        
        return response.text
    except Exception:
        logger.error("Error generating AI response")
        return "Кешіріңіз, қазір жауап бере алмаймын"

@dp.message(Command("start"))
async def start_command(message: Message):
    greeting = """🇰🇿 Сәлеметсіз бе! AlatauLLM'ға қош келдіңіз!

  Мен қазақстандық студенттерге арналған ИИ көмекшісімін:

  📚 IELTS/SAT/TOEFL дайындығы
  ✍️ Академиялық жазу көмегі  
  📖 Оқу материалдарын түсіндіру
  🎯 Емтихан дайындығы

  Сұрағыңызды жазыңыз - барлық жауаптар қазақ тілінде! 💫"""

    await message.answer(greeting, parse_mode='Markdown')
    
    
@dp.message()
async def echo(message: Message):
    ai_response = await get_ai_response(message.from_user.id, message.text)
    try:
        await message.answer(ai_response, parse_mode='Markdown')
    except Exception:
        logger.error("Error sending markdown response")
        await message.answer(ai_response)


async def main():
    show_bunner()
    logger.info("Bot is ready and polling for messages...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
