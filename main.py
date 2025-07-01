import asyncio
import tempfile
import re
import os
import logging
import json
import hashlib
from datetime import datetime, timedelta
from pydub import AudioSegment
from typing import Optional, Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, Voice
from dotenv import load_dotenv
import google.generativeai as genai
import redis

from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, AutoTokenizer, pipeline
import torch
import soundfile as sf


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

class SpeechToTextService:

    def __init__(self_stt):

        self_stt.asr_model_name = "abilmansplus/whisper-turbo-ksc2" # <- Можно менять модели
        try:
            self_stt.processor = AutoProcessor.from_pretrained(self_stt.asr_model_name)
            self_stt.asr_model = AutoModelForSpeechSeq2Seq.from_pretrained(self_stt.asr_model_name)

            if torch.cuda.is_available():
                self_stt.asr_model.to("cuda")
                logger.info(f"ASR model '{self_stt.asr_model_name}' moved to GPU.")
            else:
                logger.warning(
                    f"No GPU found. ASR model '{self_stt.asr_model_name}' will run on CPU, which might be slow.")

            logger.info(f"Hugging Face ASR model '{self_stt.asr_model_name}' loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Hugging Face ASR model '{self_stt.asr_model_name}': {e}")
            self_stt.asr_model = None
            self_stt.processor = None

    async def convert_voice_to_text(self_stt, voice_file_path: str, language: str = "kk-KZ") -> str:
        wav_path = None

        try:
            wav_path = await self_stt._convert_to_wav(voice_file_path)


            try:
                audio_input, sample_rate = sf.read(wav_path)

                if sample_rate != 16000:
                    logger.warning(f"Audio sample rate is {sample_rate}Hz, converting to 16kHz for ASR.")
                    audio_segment = AudioSegment.from_file(wav_path)
                    audio_segment = audio_segment.set_frame_rate(16000)
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav_16k_file:
                        temp_wav_path_16k = temp_wav_16k_file.name
                    audio_segment.export(temp_wav_path_16k, format="wav")
                    audio_input, sample_rate = sf.read(temp_wav_path_16k)
                    os.unlink(temp_wav_path_16k)

                input_features = self_stt.processor(
                    audio_input,
                    sampling_rate=sample_rate,
                    return_tensors="pt"
                ).input_features

                if torch.cuda.is_available():
                    input_features = input_features.to("cuda")

                predicted_ids = self_stt.asr_model.generate(
                    input_features,
                    language = "kazakh",
                    task = "transcribe"
                )

                transcription = self_stt.processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
                logger.info(f"Hugging Face ASR successful: {transcription}")

                return transcription

            except Exception as e:
                logger.error(f"Fallback: {e}")

        except Exception as e:
            logger.error(f"Speech recognition (overall) failed: {e}")
            return ""
        finally:
            try:
                if wav_path and os.path.exists(wav_path):
                    os.unlink(wav_path)
                if voice_file_path and os.path.exists(voice_file_path):
                    os.unlink(voice_file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary files: {e}")

    async def _convert_to_wav(self_stt, ogg_path: str) -> str:
        wav_path = ogg_path.replace('.ogg', '.wav')

        def convert():
            audio = AudioSegment.from_ogg(ogg_path)

            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(wav_path, format="wav")

        await asyncio.to_thread(convert)
        return wav_path

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

    def __init__(self, ai_service: AIService, cache_service: CacheService, speech_service: SpeechToTextService):
        self.ai_service = ai_service
        self.cache = cache_service

        self.speech_service = speech_service

    def convert_markdown_to_html(self, text: str) -> str:
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        return text

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

        await message.answer(greeting, parse_mode='HTML')

    async def handle_clear(self, message: Message):
        user_id = message.from_user.id

        try:
            history_key = f"user_history:{user_id}"
            self.cache.client.delete(history_key)
            await message.answer(
                "Мәтін сәтті тазартылды!\n"
                "Енді біз жаңа әңгімені таза парақтан бастай аламыз.",
                parse_mode="HTML"
            )
            logger.info(f"Redis DB was cleared for {user_id}")
        except Exception as e:
            logger.error(f"Error with clearing data for {user_id}: {e} ")
            await message.answer("Мәтінді қазір тазалау мүмкін емес, сәл кейінірек көріңізді өтінеміз")

    async def handle_voice(self, message: Message):
        try:
            voice: Voice = message.voice
            if voice.file_size > 10 * 1024 * 1024:
                await message.answer(
                    "🚫 Аудио файл тым үлкен (10МБ-тан асып кетті)."
                    "Қысқарақ аудио жіберіңіз."
                )
                return

            processing_msg = await message.answer("🎵 Аудионы өңдеп жатырмын...")
            file_info = await message.bot.get_file(voice.file_id)

            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_path = temp_file.name

            await message.bot.download_file(file_info.file_path, temp_path)

            user_session = self.cache.get_user_session(message.from_user.id)
            language = user_session.get('language', 'kk-KZ')

            # --- Использование нового SpeechToTextService ---
            recognized_text = await self.speech_service.convert_voice_to_text(
                temp_path,
                language
            )

            if not recognized_text:
                await processing_msg.edit_text(
                    "😕 Аудионы танымады. Анығырақ сөйлеп, үндірек жіберіңіз."
                )
                return

            await processing_msg.delete()

            ai_response = await self.ai_service.generate_response(
                message.from_user.id,
                recognized_text
            )

            try:
                await message.answer(ai_response, parse_mode='HTML')
            except Exception:
                await message.answer(ai_response)

        except Exception as e:
            logger.error(f"Voice processing error for user {message.from_user.id}: {e}")
            await message.answer(
                "Кешіріңіз, аудионы өңдеуде қате орын алды. "
                "Қайталап көріңіз немесе мәтін түрінде жазыңыз."
            )

    async def handle_message(self, message: Message):
        if message.text.startswith("/"): return
        ai_response = await self.ai_service.generate_response(message.from_user.id, message.text)

        try:
            html_response = self.convert_markdown_to_html(ai_response)
            await message.answer(html_response, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error sending HTML response to user {message.from_user.id}: {e}")
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

        self.speech_service = SpeechToTextService()

        self.message_handler = MessageHandler(self.ai_service, self.cache_service, self.speech_service)

        self.bot = Bot(token=os.getenv("BOT_TOKEN"))
        self.dp = Dispatcher()

        self.dp.message(Command("start"))(self.message_handler.handle_start)
        self.dp.message(Command("clear"))(self.message_handler.handle_clear)
        self.dp.message(F.voice)(self.message_handler.handle_voice)
        self.dp.message()(self.message_handler.handle_message)

    def show_banner(self):
        banner = r"""
 _____ _                                   __     ______  __  __ 
|  ___| | __ _ _ __ ___  _ __ ___   ___    \ \   / /  _ \|  \/  |
| |_  | |/ _` | '_ ` _ \| '_ ` _ \ / _ \____\ \ / /| |_) | |\/| |
|  _| | | (_| | | | | | | | | | | |  __/_____\ V / |  _ <| |  | |
|_|   |\_|\__,_|_| |_| |_|_| |_| |_|\___|      \_/  |_| \_\_|  |_|
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
