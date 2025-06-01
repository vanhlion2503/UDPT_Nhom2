from persistent import Persistent
import threading
from datetime import datetime
from .book_queue import BookQueue
import sys
import os

# Add parent directory to Python path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_user_logger

class Book(Persistent):
    def __init__(self, title, author):
        self.title = title
        self.author = author
        self.available = True
        self.borrower = None
        self.borrow_date = None
        self.queue = BookQueue()
        self.pending_requests = []  # List of (username, request_time) tuples
        self._v_lock = threading.Lock()  # Volatile attribute (not persisted)
        self._is_locked = False
        self._lock_holder = None

    @property
    def lock(self):
        """Get the lock, creating it if necessary"""
        lock = getattr(self, '_v_lock', None)
        if lock is None:
            lock = self._v_lock = threading.Lock()
        return lock

    def try_lock(self, username):
        """Attempt to lock the book for a transaction"""
        with self.lock:
            if self._is_locked and self._lock_holder != username:
                return False
            self._is_locked = True
            self._lock_holder = username
            self._p_changed = True
            return True

    def release_lock(self):
        """Release the lock after transaction is complete"""
        with self.lock:
            self._is_locked = False
            self._lock_holder = None
            self._p_changed = True

    def join_queue(self, username):
        """Add user to waiting queue"""
        if not self.try_lock(username):
            return False, "Sách đang được người khác thao tác"
            
        try:
            if not hasattr(self, 'queue'):
                self.queue = BookQueue()
                self._p_changed = True
                
            if self.available:
                return False, "Sách đang có sẵn, bạn có thể mượn ngay!"
            if self.borrower == username:
                return False, "Bạn đang mượn quyển sách này!"
                
            # Hỏi xác nhận trước khi thêm vào hàng đợi
            print(f"\nSách '{self.title}' đang được mượn bởi {self.borrower}")
            print("Bạn có muốn được thêm vào hàng đợi không?")
            print("1. Có")
            print("2. Không")
            confirmation = input("👉 Chọn: ")
            if confirmation != "1":
                return False, "Đã hủy thêm vào hàng đợi."
                
            # Kiểm tra lại xem người dùng đã có trong hàng đợi chưa
            if any(user == username for user, _ in self.queue.waiting_list):
                return False, "Bạn đã có trong hàng đợi rồi!"
                
            # Thêm vào hàng đợi
            self.queue.waiting_list.append((username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self._p_changed = True
            
            # Lấy vị trí trong hàng đợi
            position = len(self.queue.waiting_list)
            
            # Thông báo thành công
            return True, f"Bạn đã được thêm vào hàng đợi. Vị trí: {position}"
        finally:
            self.release_lock()

    def check_queue_position(self, username):
        """Check user's position in queue"""
        if not hasattr(self, 'queue'):
            self.queue = BookQueue()
            self._p_changed = True
            return None
            
        position, timestamp = self.queue.get_queue_position(username)
        if position:
            return f"Bạn đang ở vị trí {position} trong hàng đợi (từ {timestamp})"
        return None

    def borrow(self, username):
        """Attempt to borrow the book"""
        if not self.try_lock(username):
            return False, "Sách đang được người khác thao tác"
        
        try:
            if not hasattr(self, 'queue'):
                self.queue = BookQueue()
                self._p_changed = True

            if not self.available:
                if self.borrower == username:
                    return False, "Bạn đã mượn quyển sách này rồi!"
                
                # Kiểm tra hàng đợi
                if not self.queue.is_next_in_line(username):
                    # Nếu sách đang được mượn và người dùng không phải người đầu hàng đợi
                    # thì tự động thêm vào hàng đợi
                    if not any(user == username for user, _ in self.queue.waiting_list):
                        success, message = self.join_queue(username)
                        if success:
                            queue_info = f"\nHàng đợi hiện tại:\n   {self.queue.get_queue_info()}"
                            return False, f"Sách đang được mượn bởi {self.borrower}. {message}{queue_info}"
                        return False, message
                    else:
                        position, timestamp = self.queue.get_queue_position(username)
                        return False, f"Bạn đã ở vị trí {position} trong hàng đợi (từ {timestamp})"
                
                return False, "Sách đã được mượn"
            
            # Nếu sách có sẵn, kiểm tra xem người mượn có phải người đầu hàng đợi không
            if len(self.queue.waiting_list) > 0:
                if not self.queue.is_next_in_line(username):
                    first_in_line = self.queue.waiting_list[0][0]
                    return False, f"Sách này đang được giữ cho {first_in_line} (người đầu hàng đợi)"
            
            self.available = False
            self.borrower = username
            self.borrow_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.queue.remove_from_queue(username)
            self._p_changed = True
            return True, "Mượn sách thành công"
        finally:
            self.release_lock()

    def return_book(self):
        """Return the book and automatically lend to next person in queue"""
        if not self.try_lock(self.borrower or "unknown"):
            return False, "Sách đang được người khác thao tác"
        
        try:
            if not hasattr(self, 'queue'):
                self.queue = BookQueue()
                self._p_changed = True

            if self.available:
                return False, "Sách chưa được mượn"
            
            # Lưu thông tin người trả sách
            previous_borrower = self.borrower
            
            # Kiểm tra hàng đợi trước khi trả sách
            next_in_line = None
            if len(self.queue.waiting_list) > 0:
                next_in_line = self.queue.waiting_list[0][0]
            
            # Trả sách và cập nhật trạng thái
            if next_in_line:
                # Nếu có người trong hàng đợi, chuyển sách trực tiếp cho họ
                self.borrower = next_in_line
                self.borrow_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.queue.remove_from_queue(next_in_line)
                self.available = False  # Sách vẫn được mượn, chỉ đổi người mượn
            else:
                # Nếu không có ai trong hàng đợi, đánh dấu sách là có sẵn
                self.borrower = None
                self.borrow_date = None
                self.available = True
            
            self._p_changed = True
            
            # Nếu có người được mượn sách tự động
            if next_in_line:
                # Thông báo cho người được mượn sách
                logger = get_user_logger(next_in_line)
                logger.info(f"Tự động mượn sách '{self.title}' từ hàng đợi")
                return True, "Trả sách thành công"
            
            return True, "Trả sách thành công"
        finally:
            self.release_lock()

    def request_borrow(self, username):
        """Request to borrow the book (needs admin approval)"""
        if not self.try_lock(username):
            return False, "Sách đang được người khác thao tác"
        
        try:
            if not self.available:
                if self.borrower == username:
                    return False, "Bạn đã mượn quyển sách này rồi!"
                
                # Kiểm tra xem người dùng đã có trong hàng đợi chưa
                if any(user == username for user, _ in self.queue.waiting_list):
                    position, timestamp = self.queue.get_queue_position(username)
                    return False, f"Bạn đã ở vị trí {position} trong hàng đợi (từ {timestamp})"
                
                # Kiểm tra xem người dùng đã có yêu cầu mượn đang chờ duyệt chưa
                if any(user == username for user, _ in self.pending_requests):
                    return False, "Bạn đã có yêu cầu mượn sách đang chờ duyệt!"
                
                # Thêm vào hàng đợi
                print(f"\nSách '{self.title}' đang được mượn bởi {self.borrower}")
                print("Bạn có muốn được thêm vào hàng đợi không?")
                print("1. Có")
                print("2. Không")
                confirmation = input("👉 Chọn: ")
                if confirmation == "1":
                    self.queue.waiting_list.append((username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    self._p_changed = True
                    return True, f"Bạn đã được thêm vào hàng đợi. Vị trí: {len(self.queue.waiting_list)}"
                return False, "Đã hủy thêm vào hàng đợi."
            
            # Kiểm tra xem người dùng đã có yêu cầu mượn đang chờ duyệt chưa
            if any(user == username for user, _ in self.pending_requests):
                return False, "Bạn đã có yêu cầu mượn sách đang chờ duyệt!"
            
            # Kiểm tra xem có yêu cầu nào đang chờ duyệt không
            if self.pending_requests:
                print(f"\nHiện có {len(self.pending_requests)} yêu cầu mượn sách đang chờ duyệt.")
                print("Bạn có muốn thêm vào danh sách chờ không?")
                print("1. Có")
                print("2. Không")
                confirmation = input("👉 Chọn: ")
                if confirmation != "1":
                    return False, "Đã hủy yêu cầu mượn sách."
            
            # Thêm yêu cầu mượn mới
            request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.pending_requests.append((username, request_time))
            self._p_changed = True
            
            logger = get_user_logger(username)
            logger.info(f"Đã gửi yêu cầu mượn sách: {self.title}")
            
            # Thông báo vị trí trong danh sách chờ
            position = len(self.pending_requests)
            if position > 1:
                return True, f"Yêu cầu mượn sách đã được gửi và đang chờ admin duyệt! (Bạn đang ở vị trí {position} trong danh sách chờ)"
            return True, "Yêu cầu mượn sách đã được gửi và đang chờ admin duyệt!"
        finally:
            self.release_lock()

    def approve_request(self, username, admin_username):
        """Admin approves a borrow request"""
        if not self.try_lock(admin_username):
            return False, "Sách đang được người khác thao tác"
        
        try:
            # Tìm yêu cầu mượn và vị trí của nó
            request = None
            request_index = -1
            for i, req in enumerate(self.pending_requests):
                if req[0] == username:
                    request = req
                    request_index = i
                    break
            
            if not request:
                return False, f"Không tìm thấy yêu cầu mượn sách của {username}"
            
            # Kiểm tra xem có phải yêu cầu đầu tiên không
            if request_index > 0:
                earlier_request = self.pending_requests[0]
                return False, f"Không thể duyệt yêu cầu này vì có yêu cầu trước đó của {earlier_request[0]} (yêu cầu lúc {earlier_request[1]})"
            
            if not self.available:
                # Thêm vào hàng đợi nếu sách đang được mượn
                self.queue.waiting_list.append((username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                self.pending_requests.remove(request)
                self._p_changed = True
                
                logger = get_user_logger(username)
                logger.info(f"Yêu cầu mượn sách '{self.title}' được duyệt nhưng sách đang được mượn. Đã được thêm vào hàng đợi.")
                
                return True, f"Đã duyệt yêu cầu và thêm {username} vào hàng đợi vì sách đang được mượn"
            
            # Cho mượn sách
            self.available = False
            self.borrower = username
            self.borrow_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.pending_requests.remove(request)
            self._p_changed = True
            
            logger = get_user_logger(username)
            logger.info(f"Yêu cầu mượn sách '{self.title}' đã được duyệt")
            
            # Thông báo số yêu cầu còn lại đang chờ
            remaining_requests = len(self.pending_requests)
            if remaining_requests > 0:
                return True, f"Đã duyệt cho {username} mượn sách (còn {remaining_requests} yêu cầu đang chờ)"
            return True, f"Đã duyệt cho {username} mượn sách"
        finally:
            self.release_lock()

    def reject_request(self, username, admin_username, reason=""):
        """Admin rejects a borrow request"""
        if not self.try_lock(admin_username):
            return False, "Sách đang được người khác thao tác"
        
        try:
            # Tìm yêu cầu mượn
            request = None
            for req in self.pending_requests:
                if req[0] == username:
                    request = req
                    break
            
            if not request:
                return False, f"Không tìm thấy yêu cầu mượn sách của {username}"
            
            # Xóa yêu cầu
            self.pending_requests.remove(request)
            self._p_changed = True
            
            logger = get_user_logger(username)
            if reason:
                logger.info(f"Yêu cầu mượn sách '{self.title}' bị từ chối. Lý do: {reason}")
            else:
                logger.info(f"Yêu cầu mượn sách '{self.title}' bị từ chối")
            
            return True, f"Đã từ chối yêu cầu mượn sách của {username}"
        finally:
            self.release_lock()

    def get_pending_requests(self):
        """Get list of pending borrow requests"""
        if not hasattr(self, 'pending_requests'):
            self.pending_requests = []
            self._p_changed = True
        return self.pending_requests

    def __getstate__(self):
        """Custom state for persistence"""
        state = self.__dict__.copy()
        # Remove volatile attributes
        if '_v_lock' in state:
            del state['_v_lock']
        return state

    def __setstate__(self, state):
        """Restore state from persistence"""
        # Initialize default values for new attributes
        self.borrower = None
        self.borrow_date = None
        self._is_locked = False
        self._lock_holder = None
        self.queue = BookQueue()  # Initialize queue for old objects
        self.pending_requests = []  # Initialize pending requests for old objects
        
        # Update with saved state
        self.__dict__.update(state)
        
        # Recreate volatile lock
        self._v_lock = threading.Lock()
