from ZEO import ClientStorage
import ZODB
import transaction
from models.book import Book

def read_books():
    # Kết nối đến ZEO server cho books
    books_storage = ClientStorage.ClientStorage(('127.0.0.1', 8001))
    books_db = ZODB.DB(books_storage)
    books_connection = books_db.open()
    books_root = books_connection.root()

    print("\n=== THÔNG TIN SÁCH ===")
    if 'books' in books_root:
        for title, book in books_root['books'].items():
            print(f"\n📚 Tên sách: {book.title}")
            print(f"✍️ Tác giả: {book.author}")
            print(f"📌 Trạng thái: {'✅ Có sẵn' if book.available else f'❌ Đang mượn bởi {book.borrower}'}")
            if hasattr(book, 'queue') and book.queue.waiting_list:
                print(f"👥 Hàng đợi: {', '.join([u for u, _ in book.queue.waiting_list])}")
            print("-" * 50)
    else:
        print("Chưa có sách nào trong thư viện!")

    books_connection.close()
    books_db.close()

if __name__ == '__main__':
    read_books() 