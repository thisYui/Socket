import socket

host = '127.0.0.1'
port = 50000


def close_server():
    """
    Cần 2 socket cùng lúc vì khi nhận socket dầu tiên biến shutdown sẽ được đặt thành False
    nhưng vẫn có 1 socket đang lăng nghe tại thời điểm đó,
    chúng ta cần thêm 1 socket nữa để gửi lệnh shutdown cho server đảm bảo server sẽ dừng hoàn toàn
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        _ = s.recv(1024)  # Lấy file json
        s.sendall(b'shutdown')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        _ = s.recv(1024)  # Lấy file json
        s.sendall(b'shutdown')


if __name__ == '__main__':
    close_server()
