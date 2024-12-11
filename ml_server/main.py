import asyncio
import uuid
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import os
import httpx
from ml_server import config

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

app = FastAPI()

user_data = {}

class TextInput(BaseModel):
    username: str
    text: str

async def get_preprocessed_question(message):
    prompt_for_model = config.prompt_for_question_preprocess_model.format(message)
    await asyncio.sleep(0.1)
    return "pupupu..."
    # data = {
    #     "model": "unsloth/Llama-3.2-3B-Instruct",
    #     "messages": [{"role": "user", "content": prompt_for_model}]
    # }
    # headers = {"Content-Type": "application/json"}
    #
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(config.ml_server_url, json=data, headers=headers)
    #     if response.status_code == 200:
    #         return response.json().get("answer", message)
    #     else:
    #         return message

async def change_image(image, text):
    await asyncio.sleep(0.1)
    return image
    # async with httpx.AsyncClient() as client:
    #     with open(image_path, "rb") as image:
    #         files = {'image': ("image.jpg", image, "image/jpeg")}
    #         data = {
    #             "model": "MGIE",
    #             "messages": [{"role": "user", "content": text}]
    #         }
    #         response = await client.post(config.ml_server_url, files=files, data=data)
    #         response.raise_for_status()
    #         return response.json()["img"]

def get_needed_image(username, text):
    model_prompt = config.prompt_for_choosing_image.format(text)
    image_path = user_data[username][-1]
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    return img_bytes

def save_image(image: bytes, username: str):
    filename = f"{username}_{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(config.UPLOAD_FOLDER, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(image)

    user_data[username] = user_data.get(username, [])
    user_data[username].append(file_path)
    if len(user_data[username]) > config.context_length:
        os.remove(user_data[username][0])
        user_data[username] = user_data[username][1:]
    return file_path

@app.post("/upload_image/")
async def upload_image(username: str = Form(...), image: UploadFile = File(...)):
    if not username or not image:
        raise HTTPException(status_code=400, detail="Имя пользователя и файл обязательны")
    bytes_image = await image.read()
    file_path = save_image(bytes_image, username)

    return JSONResponse(content={"message": "Изображение загружено успешно", "path": file_path})

@app.post("/upload_text/")
async def upload_text(data: TextInput):
    username = data.username
    text = data.text

    if not username or not text:
        raise HTTPException(status_code=400, detail="Имя пользователя и текст обязательны")
    if len(user_data.get(username, [])) == 0:
        raise HTTPException(status_code=404, detail="Вы еще не отправили картинку")


    preprocessed_text = await get_preprocessed_question(text)
    needed_img = get_needed_image(username, text)
    changed_image = await change_image(needed_img, preprocessed_text)
    save_image(changed_image, username)

    image_stream = BytesIO(changed_image)
    return StreamingResponse(image_stream, media_type="image/jpeg")

@app.post("/clear_history/")
async def clear_history(username: str):
    for img_path in user_data[username]:
        os.remove(img_path)
    user_data[username] = []
    return JSONResponse(content={"message": "История очищена"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)