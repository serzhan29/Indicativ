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

-🚀 Запуск проекта
1. Применить миграции:
- python manage.py makemigrations
- python manage.py migrate

DOCKER:
-🚀 Как запустить
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
Выбор направлений
<img width="1912" height="825" alt="image" src="https://github.com/user-attachments/assets/2b36a3af-0b0e-4e00-80a8-b46da2864b8c" />
Возможность изменений или обновлений индикаторов
<img width="1893" height="935" alt="image" src="https://github.com/user-attachments/assets/27570424-3727-44fb-8dd8-eb685f451222" />
Возможность скачиваний отчета в виде Word файла
<img width="1247" height="640" alt="image" src="https://github.com/user-attachments/assets/e19f0832-4bf2-46a3-98d4-57069e84e3a4" />


Страница для зам кафедры:
1. Просмотр всех учителей обучающихся в той же кафедре что и сам зам. кафедры
<img width="1852" height="871" alt="image" src="https://github.com/user-attachments/assets/f0a01cad-a553-4200-8944-e8ba3a91b065" />
2. Может скачивать отчеты учителей
3. Имеет возможность смотреть отчеты всех учителей только своей кафедры
4. Может скачать отчеты в виде Word файла
<img width="1871" height="767" alt="image" src="https://github.com/user-attachments/assets/a8f535bb-20cc-4df4-bfb7-e62285b13ba7" />


Страницы для Декана:
1. Имеет возможность смотреть индикаторы всего факультета
<img width="1885" height="955" alt="image" src="https://github.com/user-attachments/assets/6f8bfe23-de40-490b-8de5-8a7972b00285" />
2. Также может скачивать отчеты всех учителей
3. Может смотреть отчеты всех учителей своего факультета
4. Может все это скачать в виде Word файла


