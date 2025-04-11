# 🧑‍💼 User Management System

Hệ thống quản lý người dùng (User Management System) được xây dựng với kiến trúc microservices sử dụng FastAPI. Hệ thống bao gồm 3 services chính:

- **User Service**: Quản lý thông tin người dùng.
- **Identity Service**: Xác thực, phân quyền, quản lý vai trò và bảo mật.
- **Email Service**: Gửi email kích hoạt, OTP, quên mật khẩu.

## 🚀 Tính năng chính

### ✅ User Service (port 9000)
- Tạo, sửa, xóa người dùng
- Lấy danh sách người dùng (có hỗ trợ tìm kiếm & lọc)
- Xuất danh sách người dùng ra file Excel
- Tự động đổi trạng thái người dùng thành "Inactive" sau 15 ngày không đăng nhập

### 🔐 Identity Service (port 9001)
- Đăng ký, đăng nhập, đổi mật khẩu
- Phân quyền và quản lý vai trò người dùng
- Xác thực bằng JWT
- Middleware kiểm tra phân quyền
- Lưu token đã logout vào Redis để blacklist
- Lưu số lần nhập OTP sai vào Redis
- Caching thông tin người dùng và role để giảm truy vấn DB

### 📧 Email Service (port 9002)
- Gửi email kích hoạt tài khoản
- Gửi OTP khi đăng nhập
- Gửi email quên mật khẩu
- Xác thực OTP và token quên mật khẩu

### 🔐 Tăng cường bảo mật (Giai đoạn 1)
- Xác thực 2 bước bằng TOTP
- Khóa tài khoản tạm thời nếu nhập sai OTP nhiều lần
- Phát hiện đăng nhập từ IP mới và gửi email cảnh báo
- Rate limiting với Redis
- Mã hóa dữ liệu nhạy cảm trong database

## 🛠️ Công nghệ sử dụng
- **Backend**: FastAPI
- **Database**: PostgreSQL
- **Caching / Security**: Redis
- **Authentication**: JWT, OTP, TOTP
- **Email**: SMTP
- **Others**: Uvicorn, OpenAPI/Swagger

## ▶️ Khởi chạy project

```bash
cd user-service
.venv\Scripts\activate
uvicorn main:app --host localhost --port 9000 --reload

cd identity-service
.venv\Scripts\activate
uvicorn main:app --host localhost --port 9001 --reload

cd email-service
.venv\Scripts\activate
uvicorn main:app --host localhost --port 9002 --reload
```

## 🧪 Swagger Docs
- User Service: [http://localhost:9000/docs](http://localhost:9000/docs)
- Identity Service: [http://localhost:9001/docs](http://localhost:9001/docs)
- Email Service: [http://localhost:9002/docs](http://localhost:9002/docs)

## 📌 Ghi chú
- Redis được sử dụng để caching, lưu OTP attempts, token blacklist, v.v.
- Các thông tin nhạy cảm cần được mã hóa trước khi lưu database.
- Email Service có thể cấu hình SMTP thông qua biến môi trường.

## 📬 Liên hệ
Nếu bạn có bất kỳ câu hỏi hay muốn đóng góp, vui lòng tạo issue hoặc pull request.
