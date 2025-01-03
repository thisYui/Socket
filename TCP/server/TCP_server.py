import socket
import threading
import os
import json
import logging
import time
from modul import SERVER_HOST, SERVER_PORT, CHUNK_SIZE, FILE_PATH, MAX_CLIENTS, NUM_THREADS, Chunk, PACKET_SIZE


# Cấu hình log cho server
logging.basicConfig(
    filename='server.log',  # Ghi log v�o file 'server.log'
    filemode='w',  # Ch? ?? ghi l?i, x�a h?t file m?i l?n ch?y
    encoding='utf-8',  # Mã hóa UTF-8
    level=logging.DEBUG,  # M?c ?? ghi log
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Hàm đọc file JSON
def extract_file_content(file_path: str) -> bytes:
    try:
        with open(file_path, 'rb') as file:
            data = json.load(file)  # Đọc file JSON
            return json.dumps(data).encode()
    except FileNotFoundError:
        logging.error(f"File {file_path} not found.")
        return b""  # Trả về bytes rỗng nếu file không tồn tại
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        return b""  # Trả về bytes rỗng


class MiniThread(threading.Thread):
    def __init__(self, client_socket, address, num_id, total_chunks: int, length_name: int,
                 file_name: str, ptr_current: int, ptr_last: int, _lock):
        super().__init__()
        self.num_id = num_id  # ID của thread
        self.chunk_id = 0  # ID của chunk
        self.total_chunks = total_chunks  # Tổng số chunk
        self.length_name = length_name  # Độ dài tên file
        self.file_name = file_name  # Tên file
        self.ptr_current = ptr_current  # Vị trí hiện tại
        self.ptr_last = ptr_last  # Vị trí cuối cùng
        self.client_socket = client_socket  # Socket kết nối với client
        self.delay = 0.005  # Độ trễ
        self.client_address = address  # Địa chỉ của client
        self._lock = _lock  # Lock để tránh xung đột giữa các thread
        
    def read_file(self) -> bytes:
        """
        Đọc dữ liệu từ file với con trỏ hiện tại (ptr_current) và con trỏ cuối (ptr_last).
        Mỗi lần đọc tối đa chunk_size bytes (mặc định là 512KB).

        Returns:
            bytes: Dữ liệu đọc được dưới dạng bytes.
        """
        try:
            # Kiểm tra tính hợp lệ của con trỏ
            if self.ptr_current >= self.ptr_last:
                return b""  # Không còn dữ liệu để đọc

            # Điều chỉnh chunk_size nếu vượt quá ptr_last
            read_size = min(CHUNK_SIZE, self.ptr_last - self.ptr_current)

            # Mở file và đọc dữ liệu
            with open(self.file_name, "rb") as f:
                f.seek(self.ptr_current)  # Đưa con trỏ tới vị trí ptr_current
                data = f.read(read_size)  # Đọc dữ liệu

            # Cập nhật ptr_current
            self.ptr_current += len(data)  # Tăng ptr_current với độ dài của dữ liệu đã đọc
            return data

        except FileNotFoundError:
            logging.error(f"File {self.file_name} not found.")
        except Exception as e:
            logging.error(f"Error reading file: {e}")

    def send_chunk(self, chunk: Chunk):
        """ Gửi chunk cho client """
        with self._lock:
            try:
                # Gửi chunk cho client
                self.client_socket.sendall(chunk.header_to_bytes())  # Gửi header của chunk
                self.client_socket.sendall(chunk.data_to_bytes())  # Gửi dữ liệu của chunk
                time.sleep(self.delay)  # Tạo độ trễ
            except Exception as e:
                logging.error(f"Error sending chunk {self.chunk_id} ID:{self.num_id} to {self.client_address}: {e}")
                return False
        
    def run(self):
        """ Gửi một phần của file cho client """
        while self.ptr_current < self.ptr_last:
            self.chunk_id += 1  # Tăng ID của chunk sau mỗi vòng lặp
            chunk = Chunk(self.num_id, self.chunk_id, self.total_chunks, 
                          self.length_name, self.file_name, self.ptr_current, b'')

            data = self.read_file()  # Đọc dữ liệu từ file
            chunk.set_data(data)  # Gán dữ liệu cho chunk
            self.send_chunk(chunk)  # Gửi chunk cho client

        logging.info(f"Sent chunk ID: {self.num_id} to {self.client_address}, name {self.file_name} successfully")
        

class Connection(threading.Thread):
    def __init__(self, client_socket: socket, client_address: (str, int), file_path: str,
                 _shared, chunk_size=CHUNK_SIZE):
        super().__init__()
        self.client_socket = client_socket  # Socket kết nối với client
        self.client_address = client_address  # Địa chỉ của client
        self.json_file = extract_file_content(file_path)  # Nội dung file JSON
        self.chunk_size = chunk_size  # Kích thước chunk
        self.request = b''  # Dữ liệu nhận từ client
        self.file_send = ''  # Tên file client yêu cầu
        self.offset = 0  # Offset client yêu cầu
        self._shared = _shared  # Số lượng client đang kết nối
        self._lock = threading.Lock()  # Lock để tránh xung đột giữa các thread

    def close(self):
        self._shared['count_client'] -= 1  # Giảm số lượng client
        self.client_socket.close()  # Đóng kết nối

    def send_json_file(self):
        """ Gửi file JSON cho client """
        self.client_socket.sendall(self.json_file)  # Gửi toàn bộ file JSON cho client

    # Kiểm tra xem file có tồn tại không
    def is_exist_file(self):
        if not os.path.exists(self.file_send):
            logging.warning(f"File {self.file_send} not found.")
            print(f"File {self.file_send} not found.")
            return False
        return True

    def get_request(self):
        """  Nhận yêu cầu từ client """
        while True:
            try:
                self.request = self.client_socket.recv(PACKET_SIZE)  # Nhận yêu cầu từ client

                # Tính hiệu ngắt kết nối
                if self.request == b'exit' or self.request == b'shutdown':
                    logging.warning(f"Client {self.client_address} disconnected.")
                    break

                if ' ' not in self.request.decode():
                    self.file_send = self.request.decode()  # Chỉ có tên file
                    self.offset = 0  # Offset mặc định là 0
                else:
                    self.file_send, self.offset = self.request.decode().split()  # Tách tên file và offset từ yêu cầu
                    self.offset = int(self.offset)  # Chuyển offset sang kiểu int

                logging.info(f"Received request for {self.file_send} from {self.client_address}")
                print(f"Received request for {self.file_send} from {self.client_address}")

                if not self.is_exist_file():
                    self.client_socket.sendall(b"0")  # Gửi thông báo file không tồn tại
                    logging.warning(f"File {self.file_send} not found.")
                    print(f"File {self.file_send} not found.")
                    continue
                break

            except ValueError:
                logging.error(f"Invalid request from {self.client_address}")
                continue

    def send_data_size(self):
        """ Gửi kích thước dữ liệu cần gửi cho client """
        data_size = os.path.getsize(self.file_send) - self.offset
        try:
            if data_size < 0:
                self.client_socket.sendall(b"0")  # Gửi kích thước dữ liệu cần gửi cho client
                logging.warning(f"Offset is greater than file size")
                return -1
            else:
                self.client_socket.sendall(str(data_size).encode('utf-8'))
            return data_size

        except Exception as e:
            logging.warning(f"Error sending data size: {e}")

    def run(self):
        self.send_json_file()  # Gửi file JSON cho client

        while True:
            self.get_request()  # Nhận yêu cầu từ client

            if self.request == b'exit':
                break  # Nếu không nhận được dữ liệu, ngắt kết nối
            elif self.request == b'shutdown' and self.client_address[0] == SERVER_HOST:
                self._shared['shutdown'] = True  # Server shutdown
                logging.error(f"Server will be shutdown")
                print(f"Server will be shutdown")
                break

            range_data = self.send_data_size()  # Gửi kích thước dữ liệu cần gửi cho client
            if range_data == -1:  # Nếu offset lớn hơn kích thước file
                continue

            # Tạo 4 thread để xử lý 4 phần của file
            threads = []
            for i in range(NUM_THREADS):
                ptr_first = self.offset + i * range_data // NUM_THREADS  # Vị trí bắt đầu của phần i
                ptr_last = self.offset + (i + 1) * range_data // NUM_THREADS  # Vị trí cuối của phần i
                total = (ptr_last - ptr_first - 1) // self.chunk_size + 1  # Tính tổng số chunk cần gửi

                # Tạo thread mới để gửi từng phần của file
                thread = MiniThread(self.client_socket, self.client_address, i + 1, total, len(self.file_send),
                                    self.file_send, ptr_first, ptr_last, self._lock)
                thread.start()  # Bắt đầu gửi dữ liệu
                threads.append(thread)

            for thread in threads:
                thread.join()

            logging.info(f"Sending {self.file_send} to {self.client_address} successfully")
            print(f"Sending {self.file_send} to {self.client_address} successfully")

        logging.error(f"Socket closed for {self.client_address}")
        print(f"Socket closed for {self.client_address}")
        self.close()  # Đóng kết nối


class Server:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT, file_path=FILE_PATH, max_clients=MAX_CLIENTS):
        self.host = host  # Host của server
        self.port = port  # Port của server
        self.file_path = file_path  # Đường dẫn đến file JSON
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Khởi tạo socket
        self._shared = {'shutdown': False, 'count_client': 0}  # Biến kiểm tra server shutdown

        # Bind socket với host và port
        self.server_socket.bind((self.host, self.port))  # Lắng nghe trên IP và cổng đã cấu hình
        self.server_socket.listen(max_clients)  # Lắng nghe tối đa MAX_CLIENTS kết nối đồng thời

    def close(self):
        self.server_socket.close()

    def handle_client(self) -> tuple[socket, tuple[str, int]]:
        """ Hàm xử lý kết nối và giao tiếp với client """
        while self._shared['count_client'] < MAX_CLIENTS and self._shared['shutdown'] is False:
            try:
                # Chấp nhận kết nối từ client
                conn, addr = self.server_socket.accept()  # Chấp nhận kết nối từ client
                self._shared['count_client'] += 1  # Tăng số lượng client
                logging.info(f"Accepted connection from {addr}")
                print(f"Accepted connection from {addr}")
                return conn, addr

            except socket.error as e:
                logging.error(f"Error accepting connection: {e}")
                print(f"Error accepting connection: {e}")
                break

    def run(self):
        while self._shared['shutdown'] is False:
            conn, addr = self.handle_client()  # Xử lý kết nối từ client

            # Tạo một thread mới để xử lý client này
            client = Connection(conn, addr, self.file_path, self._shared)
            client.start()  # Bắt đầu xử lý client

        while self._shared['count_client'] > 0:
            pass  # Đợi tất cả các client đóng kết nối

        logging.critical(f"Server shutdown")
        print(f"Server shutdown")
        self.close()


if __name__ == "__main__":
    server = Server()
    server.run()
