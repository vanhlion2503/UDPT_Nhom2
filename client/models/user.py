from persistent import Persistent
import hashlib

class User(Persistent):
    def __init__(self, username, password, role='user'):
        self.username = username
        self.password_hash = self._hash_password(password)
        self.role = role  # 'admin' or 'user'
        self.is_logged_in = False

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == self._hash_password(password)

    def has_permission(self, action):
        if self.role == 'admin':
            # Admin có tất cả quyền bao gồm thêm và xóa sách
            return action in ['add', 'delete', 'borrow', 'return', 'list']
        if self.role == 'user':
            # Users chỉ có thể mượn và trả sách
            return action in ['borrow', 'return', 'list']
        return False 