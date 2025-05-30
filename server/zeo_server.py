import sys
import subprocess
import os

def run_zeo_server(port, storage_file):
    """Chạy một ZEO server instance cho một storage file cụ thể"""
    cmd = ['runzeo', '-a', f'127.0.0.1:{port}', '-f', storage_file]
    subprocess.Popen(cmd)

def main():
    # Tạo thư mục data nếu chưa tồn tại
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Chạy ZEO server cho accounts storage
    run_zeo_server(8000, 'data/accounts.fs')
    
    # Chạy ZEO server cho books storage
    run_zeo_server(8001, 'data/books.fs')

if __name__ == '__main__':
    main()
