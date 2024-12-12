from io import BytesIO

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, ContentType, BufferedInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router

import asyncio
from tg_bot.server_interface import call_upload_image, call_upload_text
import aiohttp

API_TOKEN = "7511149812:AAE9GpapFWdOraNc42OVeHjcbsClohCkJlU"

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()  # используется для хранения данных FSM
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


# принимает file_id и возвращает байты изображения
async def get_image_bytes(file_id: str) -> bytes:
    try:
        # Получаем объект файла
        file = await bot.get_file(file_id)
        file_path = file.file_path

        # Формируем URL для скачивания файла
        download_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path}"

        # Скачиваем файл и получаем его байты
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status == 200:
                    return await response.read()  # Читаем и возвращаем байты файла
                else:
                    raise ValueError(f"Не удалось загрузить файл, статус: {response.status}")
    except Exception as e:
        raise RuntimeError(f"Ошибка при загрузке файла: {e}")


# /start
# @router.message(F.text == "/start")
# async def start_handler(message: Message):
#     await message.answer(
#         "Привет! Пожалуйста, отправьте изображение и (или) текст."
#     )


@router.message(F.content_type == ContentType.TEXT)
async def handle_text(message: Message):
    text = message.text
    username = str(message.from_user.id)

    waiting_message = await message.answer("Обрабатываю ваш запрос, пожалуйста, подождите...")

    try:
        image_bytes = await call_upload_text(username, text)
        if not image_bytes:
            await waiting_message.edit_text("Вы еще не отправили картинку")
            return

        image_stream = BytesIO(image_bytes)
        image_stream.seek(0)
        photo = BufferedInputFile(image_stream.read(), filename="image.jpg")

        await waiting_message.delete()
        await message.answer_photo(photo=photo, caption="Вот ваше изображение!")
    except Exception as e:
        await waiting_message.edit_text(f"Произошла ошибка: {str(e)}")



# обработка изображений
@router.message(F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message):
    photo = message.photo[-1]
    file_id = photo.file_id
    username = str(message.from_user.id)

    image = await get_image_bytes(file_id)
    await call_upload_image(username, image)

    await message.answer("Ваше изображение отправлено.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
