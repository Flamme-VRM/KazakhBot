import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message

BOT_TOKEN = "7559883590:AAFPH_3SDgN2OKvePVOJmHC7_AkiMHnXuLE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message()
async def echo(message: Message):
    await message.answer(message.text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

