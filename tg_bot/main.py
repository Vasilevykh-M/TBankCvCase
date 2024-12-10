from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, ContentType
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router

import asyncio

import aiohttp
from certifi import contents

API_TOKEN = "8111695240:AAFbInzzi4LFmta81S-RF-0BtldTDay82hY"

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()  # используется для хранения данных FSM
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


# принимает file_id и возвращает байты изображения
async def get_image_bytes(file_id: str) -> bytes:
    # Получаем объект файла
    file = await bot.get_file(file_id)
    file_path = file.file_path

    # contents  = await bot.download_file(file_path)

    download_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path}"

    # Скачиваем файл и получаем его байты
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url) as response:
            if response.status == 200:
                return await response.content()  # Возвращаем байты изображения
            else:
                raise ValueError(f"Не удалось загрузить файл, статус: {response.status}")


# /start
@router.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer(
        "Привет! Пожалуйста, отправьте изображение и (или) текст."
    )


# функция (пока пустая)
async def f(data: dict):
    print(data)


# обработка текстовых сообщений
@router.message(F.content_type == ContentType.TEXT)
async def handle_text(message: Message):
    user_data = {"text": message.text}  # сохранение текста в словарь
    await f(user_data)  # передача текста в функцию f
    await message.answer("Ваш текст отправлен.")


# обработка изображений
@router.message(F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message):
    # файл изображения
    photo = message.photo[-1]  # последнее изображение
    file_id = photo.file_id

    user_data = {"bytes": get_image_bytes(file_id)}  # сохранение bytes изображения в словарь
    await f(user_data)  # передача картинки в функцию f

    await message.answer("Ваше изображение отправлено.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
