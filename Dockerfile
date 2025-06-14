# Используем Python-образ
FROM python:3.13

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Открываем порт Django
EXPOSE 8000

# Команда запуска (можно переопределить в docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
