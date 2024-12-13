import base64
import os

from dotenv import load_dotenv

import httpx

load_dotenv()

api_port = os.getenv('API_PORT')
api_url = f"http://localhost:{api_port}"
debug = True


async def call_upload_text(username, text):
    async with httpx.AsyncClient(timeout=200.0) as client:
        payload = {"username": username, "text": text}
        response = await client.post(f"{api_url}/upload_text/", json=payload, )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise Exception(f"Ошибка: {response.status_code}, {response.text}")
        if debug:
            response_json = response.json()
            edited_prompt = response_json.get("edited_prompt")
            image_base64 = response_json.get("image_base64")
            if not image_base64:
                raise Exception("Ответ не содержит изображение в Base64 формате")
            image_bytes = base64.b64decode(image_base64)

            return {"edited_prompt": edited_prompt, "image_bytes": image_bytes}
        return response.content


async def call_upload_image(username, image_file: bytes):
    async with httpx.AsyncClient(timeout=10.0) as client:
        files = {"image": image_file}
        data = {"username": username}
        response = await client.post(f"{api_url}/upload_image/", data=data, files=files)
        if response.status_code != 200:
            raise Exception(f"Ошибка: {response.status_code}, {response.text}")
        return response.json().get("message")