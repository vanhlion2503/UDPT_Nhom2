from ZEO import ClientStorage
import ZODB
import transaction
from models.user import User

def read_accounts():
    # Kết nối đến ZEO server cho accounts
    accounts_storage = ClientStorage.ClientStorage(('127.0.0.1', 8000))
    accounts_db = ZODB.DB(accounts_storage)
    accounts_connection = accounts_db.open()
    accounts_root = accounts_connection.root()

    print("\n=== THÔNG TIN TÀI KHOẢN ===")
    if 'users' in accounts_root:
        for username, user in accounts_root['users'].items():
            print(f"\n👤 Tên đăng nhập: {user.username}")
            print(f"🔑 Mật khẩu (hash): {user.password_hash}")
            print(f"👑 Vai trò: {user.role}")
            print(f"📱 Trạng thái đăng nhập: {'Đã đăng nhập' if user.is_logged_in else 'Chưa đăng nhập'}")
            print("-" * 50)
    else:
        print("Chưa có tài khoản nào trong hệ thống!")

    accounts_connection.close()
    accounts_db.close()

if __name__ == '__main__':
    read_accounts() 