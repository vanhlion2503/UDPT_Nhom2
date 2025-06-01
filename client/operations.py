import logging
from models.book import Book
from models.user import User
import transaction
from functools import wraps
import time
from ZODB.POSException import ConflictError
import os
from utils import get_user_logger

MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

# Biến global để lưu update_queue
_update_queue = None

def set_update_queue(queue):
    """Set update queue từ client_app"""
    global _update_queue
    _update_queue = queue

def notify_update():
    """Thông báo có cập nhật mới"""
    if _update_queue:
        _update_queue.put(True)

def retry_on_conflict(func):
    """Decorator để thử lại khi có conflict"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except ConflictError:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                raise
    return wrapper

def require_auth(action):
    """Decorator to check authentication and authorization"""
    def decorator(func):
        @wraps(func)
        def wrapper(root, current_user, *args, **kwargs):
            if not current_user or not current_user.is_logged_in:
                print("❌ Vui lòng đăng nhập trước!")
                return False
            
            if not current_user.has_permission(action):
                print("❌ Bạn không có quyền thực hiện thao tác này!")
                return False
            
            return func(root, current_user, *args, **kwargs)
        return wrapper
    return decorator

@retry_on_conflict
def login(accounts_root):
    """Đăng nhập"""
    username = input("👤 Tên đăng nhập: ")
    password = input("🔑 Mật khẩu: ")
    
    if username in accounts_root['users']:
        user = accounts_root['users'][username]
        if user.check_password(password):
            user.is_logged_in = True
            transaction.commit()
            return user
    print("⚠️ Tên đăng nhập hoặc mật khẩu không đúng!")
    return None

@retry_on_conflict
def register(accounts_root):
    """Đăng ký tài khoản mới"""
    username = input("👤 Tên đăng nhập: ")
    if username in accounts_root['users']:
        print("⚠️ Tên đăng nhập đã tồn tại!")
        return None
        
    password = input("🔑 Mật khẩu: ")
    user = User(username, password)
    accounts_root['users'][username] = user
    transaction.commit()
    return user

@retry_on_conflict
def add_book(books_root, current_user):
    """Thêm sách mới (chỉ admin)"""
    if current_user.role != 'admin':
        print("⚠️ Bạn không có quyền thực hiện thao tác này!")
        return False
        
    title = input("📚 Tên sách: ")
    author = input("✍️ Tác giả: ")
    
    if title in books_root['books']:
        print("⚠️ Sách đã tồn tại!")
        return False
        
    book = Book(title, author)
    books_root['books'][title] = book
    transaction.commit()
    
    logger = get_user_logger(current_user.username)
    logger.info(f"Thêm sách: {title} - {author}")
    print("✅ Thêm sách thành công!")
    return True

@retry_on_conflict
def delete_book(books_root, current_user):
    """Xóa sách (chỉ admin)"""
    if current_user.role != 'admin':
        print("⚠️ Bạn không có quyền thực hiện thao tác này!")
        return False
        
    title = input("📚 Tên sách cần xóa: ")
    
    if title not in books_root['books']:
        print("⚠️ Sách không tồn tại!")
        return False
        
    book = books_root['books'][title]
    if not book.available:
        print("⚠️ Không thể xóa sách đang được mượn!")
        return False
        
    del books_root['books'][title]
    transaction.commit()
    
    logger = get_user_logger(current_user.username)
    logger.info(f"Xóa sách: {title}")
    print("✅ Xóa sách thành công!")
    return True

@retry_on_conflict
def borrow_book(books_root, current_user):
    """Gửi yêu cầu mượn sách"""
    title = input("📚 Tên sách cần mượn: ")
    
    if title not in books_root['books']:
        print("⚠️ Sách không tồn tại!")
        return False
        
    book = books_root['books'][title]
    success, message = book.request_borrow(current_user.username)
    
    if success:
        transaction.commit()
    
    print(message)
    notify_update()  # Thông báo cập nhật cho tất cả client
    return success

@retry_on_conflict
def approve_borrow_request(books_root, current_user):
    """Duyệt yêu cầu mượn sách (chỉ admin)"""
    if current_user.role != 'admin':
        print("⚠️ Bạn không có quyền thực hiện thao tác này!")
        return False

    # Hiển thị danh sách yêu cầu mượn sách
    has_requests = False
    print("\n📋 Danh sách yêu cầu mượn sách:")
    for title, book in books_root['books'].items():
        pending_requests = book.get_pending_requests()
        if pending_requests:
            has_requests = True
            print(f"\n📚 {title}:")
            for username, request_time in pending_requests:
                print(f"  - {username} (yêu cầu lúc: {request_time})")

    if not has_requests:
        print("⚠️ Không có yêu cầu mượn sách nào!")
        return False

    # Chọn sách và người dùng để duyệt
    title = input("\n📚 Nhập tên sách cần duyệt: ")
    if title not in books_root['books']:
        print("⚠️ Sách không tồn tại!")
        return False

    book = books_root['books'][title]
    username = input("👤 Nhập tên người dùng cần duyệt: ")

    print("\nBạn muốn:")
    print("1. Duyệt yêu cầu")
    print("2. Từ chối yêu cầu")
    choice = input("👉 Chọn: ")

    if choice == "1":
        success, message = book.approve_request(username, current_user.username)
    elif choice == "2":
        reason = input("📝 Lý do từ chối (có thể để trống): ")
        success, message = book.reject_request(username, current_user.username, reason)
    else:
        print("⚠️ Lựa chọn không hợp lệ!")
        return False

    if success:
        transaction.commit()
        notify_update()

    print(message)
    return success

@retry_on_conflict
def return_book(books_root, current_user):
    """Trả sách"""
    title = input("📚 Tên sách cần trả: ")
    
    if title not in books_root['books']:
        print("⚠️ Sách không tồn tại!")
        return False
        
    book = books_root['books'][title]
    if book.available:
        print("⚠️ Sách chưa được mượn!")
        return False
        
    if book.borrower != current_user.username and current_user.role != 'admin':
        print("⚠️ Bạn không phải người mượn sách này!")
        return False
        
    success, message = book.return_book()
    
    if success:
        transaction.commit()
        logger = get_user_logger(current_user.username)
        logger.info(f"Trả sách: {title}")
        notify_update()  # Thông báo cập nhật cho tất cả client
    
    print(message)
    return success

def list_books(books_root, current_user):
    """Liệt kê danh sách sách"""
    if not books_root['books']:
        print("📚 Chưa có sách nào trong thư viện!")
        return
        
    print("\nDanh sách sách:")
    for title, book in books_root['books'].items():
        status = "✅ Có sẵn" if book.available else f"❌ Đang mượn bởi {book.borrower}"
        print(f"- {title} ({book.author}): {status}")
        
        # Hiển thị yêu cầu mượn đang chờ duyệt
        pending_requests = book.get_pending_requests()
        if pending_requests:
            print(f"  📋 Yêu cầu mượn đang chờ duyệt: {', '.join([u for u, _ in pending_requests])}")
        
        # Hiển thị hàng đợi
        if hasattr(book, 'queue') and book.queue.waiting_list:
            print(f"  👥 Hàng đợi: {', '.join([u for u, _ in book.queue.waiting_list])}")

def view_logs(username):
    """Xem lịch sử hoạt động của user"""
    log_file = f'logs/{username}.log'
    if not os.path.exists(log_file):
        print("⚠️ Chưa có lịch sử hoạt động!")
        return
        
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            print("\n📝 Lịch sử hoạt động của bạn:")
            print(f.read())
    except Exception as e:
        print(f"⚠️ Không thể đọc lịch sử hoạt động: {str(e)}")
        system_logger = get_user_logger('system')
        system_logger.error(f"Lỗi khi đọc lịch sử hoạt động của {username}: {str(e)}")
