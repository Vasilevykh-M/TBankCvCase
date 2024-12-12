import httpx

api_url = "http://localhost:8000"


async def call_upload_text(username, text):
    async with httpx.AsyncClient(timeout=200.0) as client:
        payload = {"username": username, "text": text}
        response = await client.post(f"{api_url}/upload_text/", json=payload, )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise Exception(f"Ошибка: {response.status_code}, {response.text}")
        image_bytes = response.content

        return image_bytes


async def call_upload_image(username, image_file: bytes):
    async with httpx.AsyncClient() as client:
        files = {"image": image_file}
        data = {"username": username}
        response = await client.post(f"{api_url}/upload_image/", data=data, files=files)
        if response.status_code != 200:
            raise Exception(f"Ошибка: {response.status_code}, {response.text}")
        return response.json().get("message")