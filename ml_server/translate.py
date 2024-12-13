import asyncio
import json
import httpx

async def chat_with_model(
    message,
    system_message="",
    max_tokens=512,
    temperature=0.7,
    top_p=0.95
):
    messages = [{"role": "system", "content": system_message}]
    messages.append({"role": "user", "content": message})

    data = {
        "model": "Qwen/Qwen2.5-3B-Instruct",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": False
    }
    headers = {
        "Content-Type": "application/json",
    }


    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "http://172.18.0.241:8826/v1/chat/completions",
            headers=headers,
            json=data
        )

    if response.status_code == 200:
        try:
            res = response.json()["choices"][0]["message"]["content"]
            return res.strip()
        except KeyError:
            print("Unexpected response format:", response.json())
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

async def translate(text):
    system_message = (
        "Ты переводчик. Твоя задача — переводить текст с русского на английский. "
        "Возвращай только результат перевода, без дополнительных пояснений или комментариев."
    )
    message = "Переведи этот текст: " + text
    response = await chat_with_model(
        message=message,
        system_message=system_message,
        max_tokens=150,
        temperature=0.7,
        top_p=0.9,
    )

    return response