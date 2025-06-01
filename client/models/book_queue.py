from persistent import Persistent
from persistent.list import PersistentList
from datetime import datetime

class BookQueue(Persistent):
    def __init__(self):
        self.waiting_list = PersistentList()  # List of (username, timestamp)
        
    def add_to_queue(self, username):
        """Add a user to the waiting list"""
        if not any(user == username for user, _ in self.waiting_list):
            self.waiting_list.append((username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self._p_changed = True
            return True, f"Bạn đã được thêm vào hàng đợi. Vị trí: {len(self.waiting_list)}"
        return False, "Bạn đã có trong hàng đợi rồi!"
    
    def remove_from_queue(self, username):
        """Remove a user from the waiting list"""
        for i, (user, _) in enumerate(self.waiting_list):
            if user == username:
                del self.waiting_list[i]
                self._p_changed = True
                return True
        return False
    
    def is_next_in_line(self, username):
        """Check if the user is next in line to borrow the book"""
        return len(self.waiting_list) > 0 and self.waiting_list[0][0] == username
    
    def get_queue_position(self, username):
        """Get user's position in queue"""
        for i, (user, timestamp) in enumerate(self.waiting_list):
            if user == username:
                return i + 1, timestamp
        return None, None
    
    def get_queue_info(self):
        """Get formatted queue information"""
        if not self.waiting_list:
            return "Không có người đợi"
        
        info = []
        for i, (user, timestamp) in enumerate(self.waiting_list, 1):
            info.append(f"{i}. {user} (từ {timestamp})")
        return "\n   ".join(info) 