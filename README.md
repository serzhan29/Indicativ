📘 Индикативный план запуска Django-проекта для учителей
Этот проект разработан на Django и использует PostgreSQL и Redis. Ниже представлены инструкции по запуску проекта как локально, так и с использованием Docker.


Создайте и активируйте виртуальное окружение.
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # macOS/Linux

2. Установить зависимости:
pip install -r requirements.txt

3.Убедитесь, что Redis установлен и запущен
На Windows
Установите Memurai или используйте WSL с Redis 
(sudo apt install redis-server).
redis-server

🚀 Запуск проекта
1. Применить миграции
python manage.py makemigrations
python manage.py migrate

DOCKER:
🚀 Как запустить
1. Собрать и запустить контейнеры:
docker-compose up --build
2. Применить миграции:
docker-compose exec web python manage.py migrate
3. Создать суперпользователя:
docker-compose exec web python manage.py createsuperuser
4. Открыть сайт:
Открой в браузере http://localhost:8000

Админка: http://localhost:8000/admin

🧹 Остановка и удаление контейнеров
docker-compose down


Страница авторизаций
<img width="1913" height="838" alt="image" src="https://github.com/user-attachments/assets/011e135e-4ea2-43f4-b8e6-bf89341281c3" />
