# TBankCvCase

![image](https://github.com/user-attachments/assets/4364d198-b243-460d-b301-51bed602f501)

## Обзор
Этот репозиторий содержит код и документацию для кейса, направленной на использование передовых искусственных интеллектов для улучшения генрации изображений и их редактирования с учетом контекста работы с пользователем. Проект использует разнообразные передовые технологии для предоставления персонализированной помощи, ускорения времени ответов и обеспечения точных переводов промтов на любой язык.

## Используемые технологии
- [**Qwen2.5-3B-Instruct**](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct): Агент, управляемый инструкциями для контроля модели генерации в зависимости от контекста чата с пользователем.
- [**ML.MGIE**](https://ml-mgie.com/): Платформа для редактирования изображений в соответствии с конкретными инструкциями.
- [**Kandinsky**](https://www.sberbank.com/promo/kandinsky/): Инструмент для генерации изображений из текстовых описаний.

### Требования

- Python 3.x
- gpu 32 gb

### Контекст

Контекст представлен в виде списка, где каждое сообщение состоит из баз64-кодированного изображения и строки-промта. Длина списка ограничена 3 элементами.

### Обработка контекста

Агент (Qwen2.5-3B-Instruct) анализирует текущий промт и решает, нужно ли генерировать новое изображение или редактировать одно из существующих. Если это новая генерация, вызывается Kandinsky для генерации изображения. Если редактирование, выбирается индекс изображения для редактирования, уточняется промт за счет контекста и переводится на английский с использованием. Затем вызывается ML.MGIE для редактирования изображения.

![image](https://github.com/user-attachments/assets/146718a0-af08-43ba-9540-2e98e40b1bea)

### Примеры генерации:

![image](https://github.com/user-attachments/assets/f444b947-43ad-4a04-92a5-1aaeec63840a)

### Порядок запуска
- Qwen2.5-3B-Instruct, ML.MGIE, Kandinsky
- ml_server/main
- tg_bot/main
