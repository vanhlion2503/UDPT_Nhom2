# 📚 Hệ Thống Thư Viện Mini Phân Tán với ZODB & ZEO
📝 Mô tả dự án
Dự án xây dựng một hệ thống thư viện đơn giản, nơi người dùng có thể đăng ký, đăng nhập, mượn và trả sách. Hệ thống hoạt động theo mô hình client-server phân tán sử dụng ZODB làm cơ sở dữ liệu hướng đối tượng và ZEO để phân tán truy cập dữ liệu qua mạng.
🚀 Tính năng chính
👤 Quản lý tài khoản
Đăng ký tài khoản (người dùng thường)

Đăng nhập / đăng xuất

Phân quyền admin và user

Ghi log hoạt động riêng cho từng người dùng

📖 Quản lý sách
Thêm sách (admin)

Xóa sách (admin)

Xem danh sách sách

Mượn sách

Trả sách

🔁 Mượn sách có duyệt
Người dùng gửi yêu cầu mượn

Admin duyệt hoặc từ chối yêu cầu

Ghi nhận thời gian và lịch sử

📡 Tính năng phân tán
Client giao tiếp với ZEO server để truy xuất dữ liệu

Hai ZEO server:

accounts.fs (quản lý người dùng)

books.fs (quản lý sách)

Đồng bộ hóa giữa nhiều client thao tác cùng lúc

Cơ chế kiểm tra xung đột (@retry_on_conflict) đảm bảo chỉ 1 người mượn sách thành công khi có nhiều yêu cầu đồng thời

📜 Ghi log hoạt động
Mỗi người dùng có file log riêng (dạng .log)

Ghi lại thao tác đăng nhập, mượn, trả, duyệt…

