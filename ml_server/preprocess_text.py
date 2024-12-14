import httpx


async def generate_image_prompt(messages, system_message):
    processed_messages = []

    # Обрабатываем последовательность сообщений
    for i, message in enumerate(messages):
        if i < len(messages) - 1:
            # Помечаем предыдущие действия как выполненные
            processed_messages.append(
                {"role": "assistant", "content": f"The instruction '{message}' has been completed."}
            )
        else:
            # Последнее сообщение пользователя добавляем напрямую
            processed_messages.append({"role": "user", "content": message})

    data = {
        "model": "Qwen/Qwen2.5-3B-Instruct",
        "messages": [{"role": "system", "content": system_message}] + processed_messages,
        "max_tokens": 50,
        "temperature": 0.3,  # Снижаем уровень креативности
        "top_p": 0.9,       # Ограничиваем вероятностное распределение
    }
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "http://172.18.0.241:8826/v1/chat/completions",
            headers=headers,
            json=data,
        )

    if response.status_code == 200:
        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except KeyError:
            print("Unexpected response format:", response.json())
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


# Пример вызова
async def preprocess_text(user_messages):
    system_message = (
        "You are an assistant for an image editing model. Your task is to generate a clear and concise prompt "
        "in English for the image editing model. Focus on precision and simplicity. Use previous instructions only "
        "as context for understanding the latest one. Assume previous instructions have already been completed. "
        "Do not add unnecessary adjectives, descriptions, or embellishments. Your response must focus exclusively "
        "on the latest instruction, generating a single straightforward sentence in English."
    )
    prompt = await generate_image_prompt(user_messages, system_message)
    return prompt
