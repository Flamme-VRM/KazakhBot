"""
AlatauLLM - Kazakh AI Assistant Telegram Bot
Author: Shyngisbek Asylkhan
GitHub: https://github.com/Flamme-VRM
Description: AI assistant bot for Kazakh students with ENT/IELTS/SAT/TOEFL preparation support
"""

import asyncio
import os
import logging
import json
import hashlib
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
import google.generativeai as genai
import redis

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

redis_client = None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_user_history_key(user_id: int) -> str:
    return f"user_history:{user_id}"

def get_cache_key(prompt: str) -> str:
    return f"ai_cache:{hashlib.md5(prompt.encode()).hexdigest()}"

def get_user_history(user_id: int) -> list:
    try:
        if redis_client is None:
            return []
        history_json = redis_client.get(get_user_history_key(user_id))
        if history_json:
            return json.loads(history_json)
        return []
    except Exception as e:
        logger.debug(f"Error getting user history from Redis: {e}")
        return []

def save_user_history(user_id: int, history: list):
    try:
        if redis_client is None:
            return
        redis_client.setex(
            get_user_history_key(user_id),
            86400 * 7,
            json.dumps(history[-50:])
        )
    except Exception as e:
        logger.debug(f"Error saving user history to Redis: {e}")

def get_cached_response(prompt: str) -> Optional[str]:
    try:
        if redis_client is None:
            return None
        cached = redis_client.get(get_cache_key(prompt))
        return cached if cached else None
    except Exception as e:
        logger.debug(f"Error getting cached response from Redis: {e}")
        return None

def cache_response(prompt: str, response: str):
    try:
        if redis_client is None:
            return
        redis_client.setex(
            get_cache_key(prompt),
            3600,
            response
        )
    except Exception as e:
        logger.debug(f"Error caching response to Redis: {e}")

def test_redis_connection():
    try:
        if redis_client is None:
            return False
        redis_client.ping()
        logger.info("Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False

def set_user_session(user_id: int, session_data: dict):
    try:
        if redis_client is None:
            return
        redis_client.setex(
            f"user_session:{user_id}",
            3600 * 24,
            json.dumps(session_data)
        )
    except Exception as e:
        logger.debug(f"Error setting user session: {e}")

def get_user_session(user_id: int) -> dict:
    try:
        if redis_client is None:
            return {}
        session_json = redis_client.get(f"user_session:{user_id}")
        if session_json:
            return json.loads(session_json)
        return {}
    except Exception as e:
        logger.debug(f"Error getting user session: {e}")
        return {}


async def get_ai_response(user_id: int, text: str) -> str:
    try:
        user_history = get_user_history(user_id)
        user_history.append(f'User: {text}')

        recent_history = user_history[-10:]
        system_prompt = os.getenv("SYSTEM_PROMPT", "You are AlatauLLM.")
        full_prompt = system_prompt + "\n\nConversation History: \n" + "\n".join(recent_history)

        cached_response = get_cached_response(full_prompt)
        if cached_response:
            logger.info(f"Using cached response for user {user_id}")
            user_history.append(f"AlatauLLM: {cached_response}")
            save_user_history(user_id, user_history)
            return cached_response
        response = await asyncio.to_thread(model.generate_content, full_prompt)
        
        if not response or not response.text:
            logger.error(f"Empty response from AI model for user {user_id}")
            return "Кешіріңіз, жауап алу мүмкін болмады. Қайталап көріңіз."
            
        user_history.append(f"AlatauLLM: {response.text}")
        save_user_history(user_id, user_history)
        cache_response(full_prompt, response.text)
        
        return response.text
        
    except genai.types.BlockedPromptException as e:
        logger.error(f"Content blocked by AI safety filters for user {user_id}: {e}")
        return "Кешіріңіз, сұрақ қауіпсіздік фильтрлерімен бөгелді. Басқаша сұраңыз."
        
    except genai.types.StopCandidateException as e:
        logger.error(f"AI generation stopped for user {user_id}: {e}")
        return "Кешіріңіз, жауап генерациясы тоқтатылды. Қайталап көріңіз."
        
    except Exception as e:
        logger.error(f"Unexpected error generating AI response for user {user_id}: {type(e).__name__}: {str(e)}")
        return "Кешіріңіз, техникалық қате орын алды. Кейінірек қайталап көріңіз."


@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    session_data = {
        "first_name": message.from_user.first_name,
        "username": message.from_user.username,
        "started_at": str(message.date),
        "language": "kk"
    }
    set_user_session(user_id, session_data)
    
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
    except Exception as e:
        logger.error(f"Error sending markdown response to user {message.from_user.id}: {type(e).__name__}: {str(e)}")
        try:
            await message.answer(ai_response)
        except Exception as e2:
            logger.error(f"Failed to send plain text response to user {message.from_user.id}: {type(e2).__name__}: {str(e2)}")
            await message.answer("Кешіріңіз, жауап жіберуде қате орын алды.")


async def main():
    global redis_client
    show_banner()
    
    try:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
        if not test_redis_connection():
            logger.error("Redis connection failed! Bot cannot start without Redis.")
            raise SystemExit("Redis is required for bot operation")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise SystemExit("Redis is required for bot operation")
    
    logger.info("Bot is ready and polling for messages...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
