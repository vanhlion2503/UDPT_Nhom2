from ZEO import ClientStorage
import ZODB
import transaction
from persistent.mapping import PersistentMapping
from operations import *
import threading
import time
import os
import logging
import sys
from datetime import datetime
from queue import Queue
import platform
from utils import get_user_logger

# Tạo thư mục logs trong thư mục hiện tại
current_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(current_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)

# Tạo system logger
system_logger = get_user_logger('system')
system_logger.info("=== Hệ thống thư viện khởi động ===")

# Queue để thông báo cập nhật
update_queue = Queue()
# Thiết lập update_queue cho operations
set_update_queue(update_queue)

# ⚙️ Kết nối ZEO server cho books
books_storage = ClientStorage.ClientStorage(('127.0.0.1', 8001))
books_db = ZODB.DB(books_storage)
books_connection = books_db.open()
books_root = books_connection.root()

# ⚙️ Kết nối ZEO server cho accounts
accounts_storage = ClientStorage.ClientStorage(('127.0.0.1', 8000))
accounts_db = ZODB.DB(accounts_storage)
accounts_connection = accounts_db.open()
accounts_root = accounts_connection.root()

def refresh_display(books_root, current_user, force_sync=False):
    """Cập nhật hiển thị trạng thái sách"""
    if current_user and current_user.is_logged_in:
        if force_sync:
            books_connection.sync()
            transaction.begin()
        print("\n📚 Trạng thái sách hiện tại:")
        list_books(books_root, current_user)

def show_terminal_notification(message):
    """Hiển thị thông báo nổi bật trên terminal"""
    print("\n" + "="*60)
    print("🔔 THÔNG BÁO MỚI!")
    print("-" * 60)
    print(message)
    print("⏰ " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 60 + "\n")

def auto_refresh(books_root, books_connection):
    """Thread cập nhật real-time"""
    last_state = {}  # Lưu trạng thái cuối cùng của mỗi sách
    sync_interval = 0.5  # Giảm thời gian đồng bộ xuống 0.5 giây
    last_sync_time = time.time()
    
    while True:
        try:
            current_time = time.time()
            
            # Kiểm tra xem có cập nhật mới không
            try:
                # Non-blocking check for updates
                has_update = not update_queue.empty()
                if has_update:
                    update_queue.get_nowait()
                    books_connection.sync()
                    transaction.begin()
                    last_sync_time = current_time  # Reset thời gian đồng bộ
                # Nếu đã đến thời gian đồng bộ định kỳ
                elif current_time - last_sync_time >= sync_interval:
                    books_connection.sync()
                    transaction.begin()
                    last_sync_time = current_time
            except Exception as e:
                system_logger.error(f"Lỗi khi đồng bộ: {str(e)}")
                continue

            # Kiểm tra thay đổi
            current_state = {}
            has_changes = False
            
            try:
                # Cập nhật trạng thái sách
                for book_id, book in books_root['books'].items():
                    current_state[book_id] = {
                        'available': book.available,
                        'borrower': book.borrower,
                        'queue': [(u, t) for u, t in book.queue.waiting_list] if hasattr(book, 'queue') else []
                    }
                    
                    # So sánh trạng thái và kiểm tra thay đổi
                    if book_id not in last_state or current_state[book_id] != last_state[book_id]:
                        has_changes = True
                        # Kiểm tra cụ thể những thay đổi
                        if book_id in last_state:
                            old_state = last_state[book_id]
                            # Nếu có thay đổi về người mượn và người đang đăng nhập là người mượn mới
                            if old_state['borrower'] != current_state[book_id]['borrower']:
                                if current_state[book_id]['borrower'] == current_user.username:
                                    show_terminal_notification(
                                        f"📚 Bạn đã được mượn sách '{book_id}'"
                                    )
                
                if has_changes:
                    last_state = current_state.copy()
                    print("\n🔄 Cập nhật trạng thái sách:")
                    for book_id, book in books_root['books'].items():
                        status = "✅ Có sẵn" if book.available else f"❌ Đang mượn bởi {book.borrower}"
                        print(f"- {book.title}: {status}")
                        if hasattr(book, 'queue') and book.queue.waiting_list:
                            print(f"  👥 Hàng đợi: {', '.join([u for u, _ in book.queue.waiting_list])}")
            
            except Exception as e:
                system_logger.error(f"Lỗi khi kiểm tra thay đổi: {str(e)}")
                continue
            
            time.sleep(0.1)  # Giảm thời gian sleep để phản hồi nhanh hơn
            
        except Exception as e:
            system_logger.error(f"Lỗi trong auto_refresh: {str(e)}")
            time.sleep(1)  # Đợi lâu hơn nếu có lỗi

# Khởi động thread auto refresh với độ ưu tiên cao
refresh_thread = threading.Thread(target=auto_refresh, args=(books_root, books_connection), daemon=True)
refresh_thread.start()

# Khởi tạo thư viện và users nếu chưa có
if 'books' not in books_root:
    books_root['books'] = PersistentMapping()
    transaction.commit()

if 'users' not in accounts_root:
    accounts_root['users'] = PersistentMapping()
    # Tạo tài khoản admin mặc định
    admin = User('admin', 'admin123', role='admin')
    accounts_root['users']['admin'] = admin
    transaction.commit()

# Xác thực người dùng
current_user = None
while not current_user:
    print("\n1. Đăng nhập")
    print("2. Đăng ký")
    print("0. Thoát")
    
    choice = input("👉 Chọn: ")
    
    if choice == "1":
        current_user = login(accounts_root)
        if current_user:
            logger = get_user_logger(current_user.username)
            logger.info(f"Đăng nhập thành công - Vai trò: {current_user.role}")
            refresh_display(books_root, current_user)  # Hiển thị trạng thái ban đầu
    elif choice == "2":
        new_user = register(accounts_root)
        if new_user:
            # Tự động đăng nhập sau khi đăng ký thành công
            current_user = new_user
            current_user.is_logged_in = True
            transaction.commit()
            
            logger = get_user_logger(current_user.username)
            logger.info(f"Tài khoản được tạo và đăng nhập tự động - Vai trò: {current_user.role}")
            print("✅ Đăng ký thành công và đã tự động đăng nhập!")
            refresh_display(books_root, current_user)  # Hiển thị trạng thái ban đầu
    elif choice == "0":
        system_logger.info("Hệ thống đóng")
        print("👋 Tạm biệt!")
        exit()
    else:
        print("⚠️ Lựa chọn không hợp lệ.")

# Menu thao tác
while True:
    print(f"\n📌 {current_user.username} ({current_user.role}), chọn thao tác:")
    if current_user.role == 'admin':
        print("1. Thêm sách")
        print("2. Xóa sách")
        print("3. Duyệt yêu cầu mượn sách")
        print("4. Mượn sách")
        print("5. Trả sách")
        print("6. Xem tất cả sách")
        print("7. Xem lịch sử hoạt động")
        print("8. Làm mới danh sách")
        print("0. Thoát")
    else:
        print("1. Mượn sách")
        print("2. Trả sách")
        print("3. Xem tất cả sách")
        print("4. Xem lịch sử hoạt động")
        print("5. Làm mới danh sách")
        print("0. Thoát")

    choice = input("👉 Chọn: ")
    logger = get_user_logger(current_user.username)

    if current_user.role == 'admin':
        if choice == "1":
            if add_book(books_root, current_user):
                notify_update()
        elif choice == "2":
            if delete_book(books_root, current_user):
                notify_update()
        elif choice == "3":
            if approve_borrow_request(books_root, current_user):
                notify_update()
        elif choice == "4":
            if borrow_book(books_root, current_user):
                notify_update()
        elif choice == "5":
            if return_book(books_root, current_user):
                notify_update()
        elif choice == "6":
            refresh_display(books_root, current_user, force_sync=True)
        elif choice == "7":
            view_logs(current_user.username)
        elif choice == "8":
            refresh_display(books_root, current_user, force_sync=True)
        elif choice == "0":
            logger.info("Đăng xuất")
            print("👋 Tạm biệt!")
            break
        else:
            print("⚠️ Lựa chọn không hợp lệ.")
    else:
        if choice == "1":
            if borrow_book(books_root, current_user):
                notify_update()
        elif choice == "2":
            if return_book(books_root, current_user):
                notify_update()
        elif choice == "3":
            refresh_display(books_root, current_user, force_sync=True)
        elif choice == "4":
            view_logs(current_user.username)
        elif choice == "5":
            refresh_display(books_root, current_user, force_sync=True)
        elif choice == "0":
            logger.info("Đăng xuất")
            print("👋 Tạm biệt!")
            break
        else:
            print("⚠️ Lựa chọn không hợp lệ.")
