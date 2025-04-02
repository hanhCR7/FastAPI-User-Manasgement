# User-Management-FastAPI
Xây dựng ứng dụng quản lý user bằng fastapi và microservice
## Cài các module cần thiết cho cả 3 service
```sh
pip install fastapi uvicorn pydantic python-dotenv aiosmtplib sqlalchemy asyncpg httpx passlib psycopg2 jwt

```

## Đây là project

## Chạy môi trường ảo .venv
```sh
.venv\Scripts\activate
```

Áp dụng cho cả ba Service
## Chạy ứng dụng User Service
```sh
uvicorn main:app --host localhost --port 9000 --reload
```
## Chạy ứng dụng Identity Service
```sh
uvicorn main:app --host localhost --port 9001 --reload
```
## Chạy ứng dụng Email Service
```sh
uvicorn main:app --host localhost --port 9002 --reload
```
