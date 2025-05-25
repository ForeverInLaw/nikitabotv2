# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Устанавливаем системные зависимости, необходимые для psycopg2 и других библиотек
# Включает gcc для компиляции и libpq-dev для подключения к PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем файл требований первым для более эффективного кеширования Docker
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Создаем пользователя без root-прав
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Открываем порт для веб-части (если используется, например для вебхуков или админ-панели)
EXPOSE 8081

# Определение команды запуска бота
# CMD запускает приложение, когда контейнер стартует
# Если вы используете gunicorn/uvicorn для веб-части, команда будет другой
# Например: CMD ["gunicorn", "main:app", "--workers", "1", "--bind", "0.0.0.0:8080"]
# Для бота, работающего только с polling:
CMD ["python", "bot.py"]
