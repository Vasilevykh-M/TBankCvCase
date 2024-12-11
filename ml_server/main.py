import asyncio
import json
import uuid
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import os
import httpx
from ml_server.config import cfg as config

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


async def get_index_from_text(request):
    prompt = f"""You are a model designed to assist an image generator in determining which image the user wants to modify.
There are three images in the following order: 
- image1: the oldest (two steps ago).
- image2: the previous (one step ago).
- image3: the most recent (latest).

The user's request is: {request}

Respond with the image number the user wants to modify. 
Only output one of these options exactly as written: image1, image2, image3."""
    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "model": 'Qwen/Qwen2.5-3B-Instruct',
        "prompt": prompt,
    }
    d = {"image1": 1, "image2": 2, "image3": 3}
    text = ""
    trys_count = 0
    while text not in ["image1", "image2", "image3"]:
        if trys_count > 5:
            break
        async with httpx.AsyncClient() as client:
            response = await client.post("http://172.18.0.241:8826/v1/completions", headers=headers,
                                         data=json.dumps(data))
        if response.status_code == 200:
            try:
                text = " ".join(response.json()["choices"][0]["text"].strip().split())
            except KeyError:
                print("Unexpected response format:", response.json())
        else:
            print(f"Error: {response.status_code}, {response.text}")
        trys_count += 1
    if text not in d:
        return 3
    return d[text]


async def get_needed_image(username, text):
    index = await get_index_from_text(text)
    try:
        image_path = user_data[username][index - 1]
    except IndexError:
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
    print("upload_text", flush=True)
    username = data.username
    text = data.text

    if not username or not text:
        raise HTTPException(status_code=400, detail="Имя пользователя и текст обязательны")
    if len(user_data.get(username, [])) == 0:
        raise HTTPException(status_code=404, detail="Вы еще не отправили картинку")


    preprocessed_text = await get_preprocessed_question(text)
    needed_img = await get_needed_image(username, text)
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