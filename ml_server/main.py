import os
import json

import httpx
import base64
import logging
import requests
from time import time
from io import BytesIO
import uvicorn


from fastapi import APIRouter, FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from pydantic import BaseModel

from fusion_brain_api import Text2ImageAPI

from config import cfg as config
from preprocess_text import preprocess_text
from translate import translate


logger = logging.getLogger(__name__)
logging.basicConfig(filename="API.log", encoding="utf-8", level=logging.INFO)

debug = True

prompt1 = (
    "You are a text classification model. Your task is to categorize user instructions about images into one of two categories: "
    '"generation" if the user requests creating a new image, or "redaction" if the user asks to modify or add something to an existing image. '
    "Only return the category name without any explanations or additional text.\n\n"
    "Examples:\n"
    "1. \"Create a picture of a flying dragon.\" → generation\n"
    "2. \"Change the background to blue.\" → redaction\n"
    "3. \"Now generate a new image of a superhero cat.\" → generation\n"
    "4. \"Make the sky in the image brighter.\" → redaction\n\n"
    "Now categorize this input: \"{user_input}\""
)

prompt2 = (
    "You are a text classification model. Your task is to determine whether a user instruction about images falls into one of two categories: "
    '"generation" if the user requests creating a completely new image, or "redaction" if the user asks to edit, modify, or add to an existing image. '
    "Your response must be a single word: either 'generation' or 'redaction'. Do not provide explanations, clarifications, or any additional text.\n\n"
    "Examples:\n"
    "1. \"Create a picture of a flying dragon.\" → generation\n"
    "2. \"Change the background to blue.\" → redaction\n"
    "3. \"Now generate a new image of a superhero cat.\" → generation\n"
    "4. \"Make the sky in the image brighter.\" → redaction\n"
    "5. \"Add a glowing effect to the sun in the picture.\" → redaction\n"
    "6. \"Draw a futuristic cityscape.\" → generation\n\n"
    "Now categorize this input: \"{user_input}\""
)
prompt3 = (
    "You are a text classification model. Your task is to categorize a user's instruction about images into one of two categories: "
    '"generation" if the user requests creating an entirely new image from scratch, or "redaction" if the user asks to modify, edit, or add to an existing image. '
    "Your response must be a single word: either 'generation' or 'redaction'. Do not include explanations, clarifications, or any additional text in your answer.\n\n"
    "Examples:\n"
    "1. \"Create a picture of a flying dragon.\" → generation\n"
    "2. \"Change the background to blue.\" → redaction\n"
    "3. \"Now generate a new image of a superhero cat.\" → generation\n"
    "4. \"Make the sky in the image brighter.\" → redaction\n"
    "5. \"Add a glowing effect to the sun in the picture.\" → redaction\n"
    "6. \"Draw a futuristic cityscape.\" → generation\n"
    "7. \"Replace the tree in the image with a palm tree.\" → redaction\n\n"
    "Now categorize this input: \"{user_input}\""
)


class Context:
    def __init__(self):
        self.user_text = {}
        self.user_image = {}

    def save_image(self, image: base64, username: str):

        if not (username in self.user_image):
            self.user_image[username] = []

        self.user_image[username].append(image)
        if len(self.user_image[username]) > config.context_length:
            self.user_image[username].pop()
        return image

    def clear_history_(self, username: str):
        self.user_image[username] = []
        self.user_text[username] = []

    def get_image(self, user_name, idx):
        if len(self.user_image[user_name]) <= idx - 1:
            image = self.user_image[user_name][-1]
        else:
            image = self.user_image[user_name][idx - 1]

        return image

class Worker_api:

    def __init__(self):
        self.ctx = Context()

        self.image_generation_api = Text2ImageAPI(
            'https://api-key.fusionbrain.ai/',
            '5BB29EBC2AF2B879CEFBEB84184519E2',
            '15EEC189294AB3F6224EEE5591ADACED'
        )

    def change_image(self, image, prompt):
        URL = config.ml_image_worker_url
        print(type(image))

        data = {
            "img_file": image.decode("utf-8"),
            "prompt": prompt
        }
        response = requests.post(URL, json=data)
        content = response.content
        content_dict = json.loads(content)

        result_image_bytes = bytes(content_dict["generated_image_bytes"], encoding="utf-8")
        decoded_image_bytes = base64.b64decode(result_image_bytes)

        return decoded_image_bytes


    # получение id изображения
    async def get_index_from_text(self, request):
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


        for i in range(5):

            if text in ["image1", "image2", "image3"]:
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


        if text not in d:
            return 3
        return d[text]

    async def get_needed_image(self, username, text):
        index = await self.get_index_from_text(text)

        image = self.ctx.get_image(username, index)

        logger.debug(f"Image index: {index}")
        return image

    def generate_image(self, text):
        model_id = self.image_generation_api.get_model()
        uuid = self.image_generation_api.generate(text, model_id)
        images = self.image_generation_api.check_generation(uuid)
        image_base64 = images[0]
        generated_image = base64.b64decode(image_base64)
        return generated_image

    def save_image(self, image: base64, username: str):

        self.ctx.save_image(image, username)

        return image


    async def validate_one_request(self, request, prompt):
        p = prompt.format(user_input=request)

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "model": 'Qwen/Qwen2.5-3B-Instruct',
            "prompt": p,
        }
        text = ""
        trys_count = 0
        while text not in ["generation", "redaction"]:
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
            g = "generation" in text
            r = "redaction" in text
            if g and not r:
                text = "generation"
            elif not g and r:
                text = "redaction"
            trys_count += 1
        if text == "generation":
            return 1
        else:
            return 0

    async def detect_generation(self, request):
        c = [0, 0]
        for p in [prompt1, prompt2, prompt3]:
            ind = await self.validate_one_request(request, p)
            c[ind] += 1
        if c[0] > 1:
            return 0
        else:
            return 1


    def clear_history_(self, username: str):
        self.ctx.clear_history_(username)

class TextInput(BaseModel):
    username: str
    text: str

class Worker_FastApi:
    def __init__(self):
        self.worker = Worker_api()
        self.router = APIRouter()
        self.router.add_api_route("/upload_image/",  self.upload_image, methods=["POST"])
        self.router.add_api_route("/upload_text/", self.upload_text, methods=["POST"])
        self.router.add_api_route("/clear_history/", self.clear_history, methods=["POST"])
    async def upload_image(self, username: str = Form(...), image: UploadFile = File(...)):
        if not username or not image:
            raise HTTPException(status_code=400, detail="Имя пользователя и файл обязательны")
        self.worker.ctx.clear_history_(username)
        bytes_image = await image.read()

        base64image = base64.b64encode(bytes_image)
        self.worker.save_image(base64image, username)

        return JSONResponse(content={"message": "Изображение загружено успешно"})

    async def upload_text(self, data: TextInput):
        username = data.username
        text = data.text

        if not username or not text:
            raise HTTPException(status_code=400, detail="Имя пользователя и текст обязательны")
        if await self.worker.detect_generation(text):
            logger.info("generation detected")
            generated_image = self.worker.generate_image(text)
            bytes_image = base64.b64encode(generated_image)
            self.worker.save_image(bytes_image, username)
            changed_image = base64.b64decode(bytes_image)
            edited_prompt = text
        else:
            if len(self.worker.ctx.user_image.get(username, [])) == 0:
                raise HTTPException(status_code=400, detail="Вы еще не отправили картинку")

            if username not in self.worker.ctx.user_text:
                self.worker.ctx.user_text[username] = []
            self.worker.ctx.user_text[username].append(text)

            if len(self.worker.ctx.user_text[username]) > config.text_context_length:
                self.worker.ctx.user_text[username] = self.worker.ctx.user_text[username][1:]

            t = time()
            needed_img = await self.worker.get_needed_image(username, text)
            logger.info(f"Time to get image ID: {time() - t}")

            t = time()
            edited_prompt = await preprocess_text(self.worker.ctx.user_text[username])
            # edited_prompt = await translate(self.worker.ctx.user_text[username][-1])
            logger.info(f"Time to preprocess prompt: {time() - t}")
            logger.info(f"Edited prompt: {edited_prompt}")

            t = time()
            changed_image = self.worker.change_image(needed_img, edited_prompt)
            logger.info(f"Time to edit image: {time() - t}")
            bytes_image = base64.b64encode(changed_image)


            self.worker.save_image(bytes_image, username)

        if debug:
            response_json = {
                "edited_prompt": edited_prompt,
                "image_base64": bytes_image.decode('utf-8')
            }
            return JSONResponse(content=response_json)
        else:
            image_stream = BytesIO(changed_image)
            return StreamingResponse(image_stream, media_type="image/jpeg")


    async def clear_history(self, username: str):
        self.worker.clear_history_(username)
        return JSONResponse(content={"message": "История очищена"})


if __name__ == "__main__":
    api = Worker_FastApi()
    app = FastAPI()
    app.include_router(api.router)
    uvicorn.run(app, host="localhost", port=config.port)