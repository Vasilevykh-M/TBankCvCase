#!/bin/bash

# Список названий виртуальных окружений и их зависимостей
envs=("env1" "env2" "env3" "env4")
requirements=("requirements1.txt" "requirements2.txt" "requirements3.txt" "requirements4.txt")
apps=("tg_bot/main.py" "ml_server/main.py" "mgie_api/main.py" "vllm serve "Qwen/Qwen2.5-3B-Instruct" --gpu-memory-utilization 0.28 --max-model-len 4096 --device cuda --dtype=float16 --port 8001 --trust-remote-code")

# Проверка на наличие Python и pip
if ! command -v python3 &> /dev/null; then
    echo "Python не установлен. Пожалуйста, установите Python."
    exit 1
fi

if ! command -v pip &> /dev/null; then
    echo "pip не установлен. Пожалуйста, установите pip."
    exit 1
fi

# Процесс создания и настройки каждого виртуального окружения
for i in "${!envs[@]}"; do
    env="${envs[$i]}"
    req="${requirements[$i]}"
    app="${apps[$i]}"

    # Проверка, существует ли уже виртуальное окружение
    if [ -d "$env" ]; then
        echo "Виртуальное окружение $env уже существует. Пропускаем создание."
    else
        echo "Создаю виртуальное окружение $env..."
        python3 -m venv "$env"
    fi

    # Активируем виртуальное окружение
    echo "Активирую виртуальное окружение $env..."
    source "$env/bin/activate"

    # Установка зависимостей
    if [ -f "$req" ]; then
        echo "Устанавливаю зависимости из $req..."
        pip install -r "$req"
    else
        echo "Файл $req не найден. Пропускаю установку зависимостей."
    fi

    # Запуск приложения
    if [ -f "$app" ]; then
        echo "Запускаю приложение $app в $env..."
        python "$app" &
    else
        echo "Файл приложения $app не найден. Пропускаю запуск."
    fi

    # Деактивируем виртуальное окружение
    deactivate
    echo "Виртуальное окружение $env настроено и приложение запущено."
done

echo "Все виртуальные окружения настроены и приложения запущены."