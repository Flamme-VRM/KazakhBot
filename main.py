"""
AsylBILIM - Refactored Architecture

"""

import asyncio
import os
import logging
import json
import hashlib
from typing import Optional, Dict, List

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


class CacheService:
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._test_connection()
    
    def _test_connection(self):
        try:
            self.client.ping()
            logger.info("Redis connection successful")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise SystemExit("Redis is required for bot operation")
    
    def get_user_history(self, user_id: int) -> List[str]:
        try:
            key = f"user_history:{user_id}"
            history_json = self.client.get(key)
            return json.loads(history_json) if history_json else []
        except Exception as e:
            logger.debug(f"Error getting user history: {e}")
            return []
    
    def save_user_history(self, user_id: int, history: List[str]):
        try:
            key = f"user_history:{user_id}"
            self.client.setex(key, 86400 * 7, json.dumps(history[-50:]))
        except Exception as e:
            logger.debug(f"Error saving user history: {e}")
    
    def get_cached_response(self, prompt: str) -> Optional[str]:
        try:
            key = f"ai_cache:{hashlib.md5(prompt.encode()).hexdigest()}"
            return self.client.get(key)
        except Exception as e:
            logger.debug(f"Error getting cached response: {e}")
            return None
    
    def cache_response(self, prompt: str, response: str):
        try:
            key = f"ai_cache:{hashlib.md5(prompt.encode()).hexdigest()}"
            self.client.setex(key, 3600, response)
        except Exception as e:
            logger.debug(f"Error caching response: {e}")
    
    def set_user_session(self, user_id: int, session_data: Dict):
        try:
            key = f"user_session:{user_id}"
            self.client.setex(key, 3600 * 24, json.dumps(session_data))
        except Exception as e:
            logger.debug(f"Error setting user session: {e}")
    
    def get_user_session(self, user_id: int) -> Dict:
        try:
            key = f"user_session:{user_id}"
            session_json = self.client.get(key)
            return json.loads(session_json) if session_json else {}
        except Exception as e:
            logger.debug(f"Error getting user session: {e}")
            return {}


class AIService:
    
    def __init__(self, api_key: str, model_name: str, cache_service: CacheService):
        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(model_name)
        self.cache = cache_service

        self.system_prompt = os.getenv("SYSTEM_PROMPT")

        if not self.system_prompt:
            logger.warning("SYSTEM_PROMPT is missing")
    
    async def generate_response(self, user_id: int, text: str) -> str:
        try:
            history = self.cache.get_user_history(user_id)
            history.append(f'User: {text}')

            recent_history = history[-10:]
            full_prompt = f"{self.system_prompt}\n\nConversation History:\n" + "\n".join(recent_history)

            cached_response = self.cache.get_cached_response(full_prompt)
            if cached_response:
                logger.info(f"Using cached response for user {user_id}")
                history.append(f"AsylBILIM: {cached_response}")
                self.cache.save_user_history(user_id, history)
                return cached_response

            response = await asyncio.to_thread(self.model.generate_content, full_prompt)
            
            if not response or not response.text:
                logger.error(f"Empty response from AI model for user {user_id}")
                return "Кешіріңіз, жауап алу мүмкін болмады. Қайталап көріңіз."

            history.append(f"AsylBILIM: {response.text}")
            self.cache.save_user_history(user_id, history)
            self.cache.cache_response(full_prompt, response.text)
            
            return response.text
            
        except genai.types.BlockedPromptException as e:
            logger.error(f"Content blocked for user {user_id}: {e}")
            return "Кешіріңіз, сұрақ қауіпсіздік фильтрлерімен бөгелді. Басқаша сұраңыз."
            
        except genai.types.StopCandidateException as e:
            logger.error(f"AI generation stopped for user {user_id}: {e}")
            return "Кешіріңіз, жауап генерациясы тоқтатылды. Қайталап көріңіз."
            
        except Exception as e:
            logger.error(f"Unexpected error for user {user_id}: {type(e).__name__}: {str(e)}")
            return "Кешіріңіз, техникалық қате орын алды. Кейінірек қайталап көріңіз."

class MessageHandler:
    
    def __init__(self, ai_service: AIService, cache_service: CacheService):
        self.ai_service = ai_service
        self.cache = cache_service
    
    async def handle_start(self, message: Message):
        user_id = message.from_user.id
        session_data = {
            "first_name": message.from_user.first_name,
            "username": message.from_user.username,
            "started_at": str(message.date),
            "language": "kk"
        }
        self.cache.set_user_session(user_id, session_data)
        
        greeting = """🇰🇿 Сәлеметсіз бе! AsylBILIM'ге қош келдіңіз!

Мен қазақстандық студенттерге арналған ИИ көмекшісімін:

📚 ЕНТ/IELTS/SAT/TOEFL дайындығы
✍️ Академиялық жазу көмегі  
📖 Оқу материалдарын түсіндіру
🎯 Емтихан дайындығы

Сұрағыңызды жазыңыз - барлық жауаптар қазақ тілінде! 💫"""

        await message.answer(greeting, parse_mode='Markdown')


    async def handle_clear(self, message: Message):
        user_id = message.from_user.id

        try:

            history_key = f"user_history:{user_id}"
            self.cache.client.delete(history_key)
            await message.answer(
                "Мәтін сәтті тазартылды!\n"
                 "Енді біз жаңа әңгімені таза парақтан бастай аламыз.",
                 parse_mode ="Markdown"
            )


            logger.info(f"Redis DB was cleared for {user_id}")

        except Exception as e:
            logger.error(f"Error with clearing data for {user_id}: {e} ")
            await message.answer("Мәтінді қазір тазалау мүмкін емес, сәл кейінірек көріңізді өтінеміз")

    async def handle_message(self, message: Message):
        if message.text.startswith("/"): return
        ai_response = await self.ai_service.generate_response(message.from_user.id, message.text)
        
        try:
            await message.answer(ai_response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending markdown response to user {message.from_user.id}: {e}")
            try:
                await message.answer(ai_response)
            except Exception as e2:
                logger.error(f"Failed to send plain text response to user {message.from_user.id}: {e2}")
                await message.answer("Кешіріңіз, жауап жіберуде қате орын алды.")

class AsylBilim:
    
    def __init__(self):
        load_dotenv(".env")

        self.cache_service = CacheService(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0))
        )
        
        self.ai_service = AIService(
            api_key=os.getenv("LLM_API_KEY"),
            model_name=os.getenv("MODEL"),
            cache_service=self.cache_service
        )
        
        self.message_handler = MessageHandler(self.ai_service, self.cache_service)

        self.bot = Bot(token=os.getenv("BOT_TOKEN"))
        self.dp = Dispatcher()



        self.dp.message(Command("start"))(self.message_handler.handle_start)
        self.dp.message(Command("clear"))(self.message_handler.handle_clear)

        self.dp.message()(self.message_handler.handle_message)

    def show_banner(self):
        banner = r"""
 _____ _                                   __     ______  __  __ 
|  ___| | __ _ _ __ ___  _ __ ___   ___    \ \   / /  _ \|  \/  |
| |_  | |/ _` | '_ ` _ \| '_ ` _ \ / _ \____\ \ / /| |_) | |\/| |
|  _| | | (_| | | | | | | | | | | |  __/_____\ V / |  _ <| |  | |
|_|   |_|\__,_|_| |_| |_|_| |_| |_|\___|      \_/  |_| \_\_|  |_|
        """
        print(banner)
        logger.info("AsylBILIM bot starting up...")
    
    async def start(self):
        self.show_banner()
        logger.info("Bot is ready and polling for messages...")
        await self.dp.start_polling(self.bot)


async def main():
    bot = AsylBilim()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
