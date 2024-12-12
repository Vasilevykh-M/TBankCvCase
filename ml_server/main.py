import base64
import json
import uuid
from io import BytesIO

import requests
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import os
import httpx
from ml_server.config import cfg as config

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

app = FastAPI()

user_image_data = {}
user_text_data = {}

class TextInput(BaseModel):
    username: str
    text: str

async def get_preprocessed_question(message):
    return message
    prompt_for_model = config.prompt_for_question_preprocess_model.format(message)
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "model": 'Qwen/Qwen2.5-3B-Instruct',
        "prompt": prompt_for_model,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(config.ml_llm_worker_url_, headers=headers,
                                     data=json.dumps(data))
    text = message
    if response.status_code == 200:
        try:
            text = " ".join(response.json()["choices"][0]["text"].strip().split())
        except KeyError:
            print("Unexpected response format:", response.json())
    else:
        print(f"Error: {response.status_code}, {response.text}")
    return text


def change_image(image, prompt): # image is file(image = open("img", "rb"))
    URL = config.ml_image_worker_url.format(prompt)
    files = {
        "img_file": image
    }
    response = requests.post(URL, files=files)
    content = response.content
    content_dict = json.loads(content)

    image.close()

    result_image_bytes = bytes(content_dict["generated_image_bytes"], encoding="utf-8")
    decoded_image_bytes = base64.b64decode(result_image_bytes)

    return decoded_image_bytes


async def get_index_from_text(request):
    prompt = config.index_model_prompt.format(request)
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
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(config.ml_llm_worker_url, headers=headers,
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
        image_path = user_image_data[username][index - 1]
    except IndexError:
        image_path = user_image_data[username][-1]
    print(index)
    return open(image_path, "rb")

def save_image(image: bytes, username: str):
    filename = f"{username}_{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(config.UPLOAD_FOLDER, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(image)

    user_image_data[username] = user_image_data.get(username, [])
    user_image_data[username].append(file_path)
    if len(user_image_data[username]) > config.context_length:
        os.remove(user_image_data[username][0])
        user_image_data[username] = user_image_data[username][1:]
    return file_path

@app.post("/upload_image/")
async def upload_image(username: str = Form(...), image: UploadFile = File(...)):
    if not username or not image:
        raise HTTPException(status_code=400, detail="Имя пользователя и файл обязательны")
    clear_history_(username)
    bytes_image = await image.read()
    file_path = save_image(bytes_image, username)

    return JSONResponse(content={"message": "Изображение загружено успешно", "path": file_path})

@app.post("/upload_text/")
async def upload_text(data: TextInput):
    username = data.username
    text = data.text

    if not username or not text:
        raise HTTPException(status_code=400, detail="Имя пользователя и текст обязательны")
    if len(user_image_data.get(username, [])) == 0:
        raise HTTPException(status_code=404, detail="Вы еще не отправили картинку")

    preprocessed_text = await get_preprocessed_question(text)
    print(preprocessed_text)
    user_text_data[username] = user_text_data.get(username, []) + [text]
    if len(user_text_data[username]) > config.text_content_length:
        user_text_data[username] = user_text_data[1:]
    needed_img = await get_needed_image(username, text)
    changed_image = change_image(needed_img, preprocessed_text)
    save_image(changed_image, username)

    image_stream = BytesIO(changed_image)
    return StreamingResponse(image_stream, media_type="image/jpeg")

@app.post("/clear_history/")
async def clear_history(username: str):
    clear_history_(username)
    return JSONResponse(content={"message": "История очищена"})

def clear_history_(username: str):
    for img_path in user_image_data[username]:
        os.remove(img_path)
    user_image_data[username] = []
    user_text_data[username] = []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)