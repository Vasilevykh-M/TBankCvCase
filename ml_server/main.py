import os
import json
import uuid
import httpx
import base64
import logging
import requests
from time import time
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from pydantic import BaseModel

from fusion_brain_api import Text2ImageAPI

from config import cfg as config


logger = logging.getLogger(__name__)
logging.basicConfig(filename="API.log", encoding="utf-8", level=logging.INFO)

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

app = FastAPI()

user_image_data = {}
user_text_data = {}

image_generation_api = Text2ImageAPI(
    'https://api-key.fusionbrain.ai/', 
    '5BB29EBC2AF2B879CEFBEB84184519E2',
    '15EEC189294AB3F6224EEE5591ADACED'
)

class TextInput(BaseModel):
    username: str
    text: str

def change_image(image_bytes, prompt):
    URL = config.ml_image_worker_url.format(prompt)
    files = {
        "img_file": image_bytes
    }
    response = requests.post(URL, files=files)
    content = response.content
    content_dict = json.loads(content)

    image_bytes.close()

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
    json_data = json.dumps(data)

    d = {"image1": 1, "image2": 2, "image3": 3}
    text = ""
    trys_count = 0
    while text not in ["image1", "image2", "image3"]:
        if trys_count > 5:
            break
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                config.ml_llm_worker_url, 
                headers=headers,
                data=json_data
            )
        if response.status_code == 200:
            try:
                text = " ".join(response.json()["choices"][0]["text"].strip().split())
            except KeyError:
                logger.error("Unexpected response format: " + str(response.json()))
        else:
            logger.error(f"Error: {response.status_code}, {response.text}")
        trys_count += 1
    if text not in d:
        return 3
    return d[text]


async def get_summarized_prompt(request):
    prompt = config.summarized_model_prompt.format(request)
    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "model": 'Qwen/Qwen2.5-3B-Instruct',
        "prompt": prompt,
        "max_tokens": 20
    }
    json_data = json.dumps(data)
    text = ""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            config.ml_llm_worker_url, 
            headers=headers,
            data=json_data
        )
    if response.status_code == 200:
        try:
            text = response.json()["choices"][0]["text"]
        except KeyError:
            print("Unexpected response format:", response.json())
    else:
        print(f"Error: {response.status_code}, {response.text}")
    return text 


async def get_needed_image(username, text):
    index = await get_index_from_text(text)

    try:
        image_path = user_image_data[username][index - 1]
    except IndexError:
        image_path = user_image_data[username][-1]

    logger.debug(f"Image index: {index}")
    return open(image_path, "rb")


def generate_image(text):
    model_id = image_generation_api.get_model()
    uuid = image_generation_api.generate(text, model_id)
    images = image_generation_api.check_generation(uuid)
    image_base64 = images[0]
    image_data = base64.b64decode(image_base64)
    return image_data


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

async def detect_generation(request):
    prompt = (
        "You are a text classification model. Your task is to categorize user instructions about images into one of two categories: "
        '"generation" if the user requests creating a new image, or "redaction" if the user asks to modify an existing image. '
        "Only return the category name without any explanations or additional text.\n\n"
        "Examples:\n"
        "1. \"Create a picture of a flying dragon.\" → generation\n"
        "2. \"Change the background to blue.\" → redaction\n"
        "3. \"Now generate a new image of a superhero cat.\" → generation\n"
        "4. \"Make the sky in the image brighter.\" → redaction\n\n"
        "Now categorize this input: \"{user_input}\""
    ).format(user_input=request)

    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "model": 'Qwen/Qwen2.5-3B-Instruct',
        "prompt": prompt,
    }
    text = ""
    trys_count = 0
    while text not in ["generation", "redaction"]:
        if trys_count > 5:
            break
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("http://172.18.0.241:8826/v1/completions", headers=headers,
                                         data=json.dumps(data))
        if response.status_code == 200:
            try:
                text = " ".join(response.json()["choices"][0]["text"].strip().split())
            except KeyError:
                logger.error(f"Unexpected response format: {response.json()}")
        else:
            logger.error(f"Error: {response.status_code}, {response.text}")

        g = "generation" in text
        r = "redaction" in text
        if g and not r:
            text = "generation"
        elif not g and r:
            text = "redaction"
        trys_count += 1
    return text == "generation"



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
    # if await detect_generation(text):
    #     generated_image = generate_image(text)
    #     save_image(generated_image, username)
    #     image_stream = BytesIO(generated_image)
    #     return StreamingResponse(image_stream, media_type="image/jpeg")
    if len(user_image_data.get(username, [])) == 0:
        raise HTTPException(status_code=404, detail="Вы еще не отправили картинку")
    
    if username not in user_text_data:
        user_text_data[username] = []
    user_text_data[username].append(text)

    if len(user_text_data[username]) > config.text_context_length:
        user_text_data[username] = user_text_data[username][1:]

    # t = time()
    # edited_prompt = await get_summarized_prompt(user_text_data[username])
    # logger.info(f"Time to preprocess prompt: {time() - t}")
    # logger.info(f"Edited prompt: {edited_prompt}")
    t = time()
    needed_img = await get_needed_image(username, text)
    logger.info(f"Time to get image ID: {time() - t}")

    t = time()
    # changed_image = change_image(needed_img, edited_prompt)
    changed_image = change_image(needed_img, text)
    logger.info(f"Time to edit image: {time() - t}")

    save_image(changed_image, username)

    image_stream = BytesIO(changed_image)
    return StreamingResponse(image_stream, media_type="image/jpeg")

@app.post("/clear_history/")
async def clear_history(username: str):
    clear_history_(username)
    return JSONResponse(content={"message": "История очищена"})

def clear_history_(username: str):
    for img_path in user_image_data.get(username, []):
        os.remove(img_path)
    user_image_data[username] = []
    user_text_data[username] = []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)