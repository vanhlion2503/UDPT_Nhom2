# 📚 Hệ Thống Thư Viện Mini Phân Tán với ZODB & ZEO
## 📝 Mô tả dự án
Dự án xây dựng một hệ thống thư viện đơn giản, nơi người dùng có thể đăng ký, đăng nhập, mượn và trả sách. Hệ thống hoạt động theo mô hình client-server phân tán sử dụng ZODB làm cơ sở dữ liệu hướng đối tượng và ZEO để phân tán truy cập dữ liệu qua mạng.
##🚀 Tính năng chính
###👤 Quản lý tài khoản
- Đăng ký tài khoản (người dùng thường)

- Đăng nhập / đăng xuất

- Phân quyền admin và user

- Ghi log hoạt động riêng cho từng người dùng

### 📖 Quản lý sách
- Thêm sách (admin)

- Xóa sách (admin)

- Xem danh sách sách

- Mượn sách

- Trả sách

### 🔁 Mượn sách có duyệt
- Người dùng gửi yêu cầu mượn

- Admin duyệt hoặc từ chối yêu cầu

- Ghi nhận thời gian và lịch sử

## 📡 Tính năng phân tán
Client giao tiếp với ZEO server để truy xuất dữ liệu

Hai ZEO server:

accounts.fs (quản lý người dùng)

books.fs (quản lý sách)

Đồng bộ hóa giữa nhiều client thao tác cùng lúc

Cơ chế kiểm tra xung đột (@retry_on_conflict) đảm bảo chỉ 1 người mượn sách thành công khi có nhiều yêu cầu đồng thời

## 📜 Ghi log hoạt động
Mỗi người dùng có file log riêng (dạng .log)

Ghi lại thao tác đăng nhập, mượn, trả, duyệt…

## 🛠️ Yêu cầu hệ thống

- Python 3.x
- ZEO
- ZODB
- Các thư viện Python khác (xem requirements.txt)

## 📌 Công nghệ sử dụng
🗃️ ZODB – cơ sở dữ liệu hướng đối tượng thuần Python

🌐 ZEO – mở rộng ZODB cho hệ thống phân tán nhiều client

🔁 Transaction – kiểm soát giao dịch, rollback nếu xung đột

🧩 Multithreading (tùy chọn) – xử lý đồng thời / chờ sách

## 🛡️ Tính ổn định
Hệ thống sử dụng @retry_on_conflict để đảm bảo giao dịch được xử lý ổn định khi xảy ra tranh chấp giữa các client.

Dữ liệu an toàn trong file .fs, tương đương các cơ sở dữ liệu ACID.

## 📊 Cấu trúc dự án

```
distributed_library_project/
├── client/
│   ├── client_app.py
│   ├── operations.py
│   └── utils.py
├── server/
│   ├── zeo_server.py
│   └── data/
├── .venv/
└── README.md
```

## 🔒 Bảo mật

- Xác thực người dùng
- Phân quyền truy cập
- Ghi log hoạt động
- Bảo vệ dữ liệu phân tán

## 📝 Ghi chú

- Hệ thống sử dụng ZEO để quản lý dữ liệu phân tán
- Dữ liệu được lưu trữ trên nhiều server riêng biệt
- Có cơ chế đồng bộ hóa real-time
- Hỗ trợ nhiều người dùng truy cập đồng thời


