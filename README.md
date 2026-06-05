Библиотеки
pip install redis fastapi uvicorn 
Запуск
docker compose up -d
uvicorn main:app --reload    
Тестим
http://127.0.0.1:8000/docs Сваггер
http://localhost:5540 Редис
