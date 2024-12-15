import socket
import os
import threading
import json
import logging
import time

from modul import Chunk, Respond, NUM_THREADS, SERVER_HOST, SERVER_PORT, FILE_PATH, CHUNK_SIZE, PACKET_SIZE

# Cấu hình log cho server
logging.basicConfig(
    filename='server.log',     # Ghi log vào file 'server.log'
    filemode='w',                  # Chế độ ghi lại, xóa hết file mỗi lần chạy
    encoding='utf-8',              # Mã hóa UTF-8
    level=logging.DEBUG,           # Mức độ ghi log
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class SendThread(threading.Thread):
    def __init__(self, thread_host: str, thread_port: int, file_path: str,
                 thread_id: int, ptr_first: int, ptr_last: int):
        super().__init__()  # Gọi hàm khởi tạo của lớp cha
        self.thread_host = thread_host  # Địa chỉ IP server
        self.thread_port = thread_port  # Cổng bind
        self.file_path = file_path  # Đường dẫn đến file cần gửi
        self.thread_id = thread_id  # ID của thread
        self.ptr_last = ptr_last  # Vị trí kết thúc đọc file
        self.ptr_current = ptr_first  # Vị trí hiện tại đọc file
        self.client_ip = ''  # Địa chỉ IP của client
        self.client_port = 0  # Cổng của client
        self.chunk = Chunk(b'', 0, 0)  # Chunk hiện tại
        self.seq_num = 0  # Số thứ tự của chunk
        self.time_out = 1  # Thời gian chờ ACK: 1s
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Tạo socket
        self.received = Respond()  # file nhận được từ client
        self.size_chunk = CHUNK_SIZE  # Kích thước mỗi chunk: 64KB
        self.delay = 0.005  # Độ trễ

        """ Bind socket """
        self.socket.bind((self.thread_host, self.thread_port))  # Bind socket

    def __str__(self):
        return f"SendThread: {self.thread_id}, {self.ptr_current}, {self.ptr_last}"

    # Hàm đóng kết nối
    def close(self):
        self.socket.close()

    # Hàm đọc file
    def read_file(self) -> bytes:
        # open ở chế dộ rb
        with open(self.file_path, 'rb') as f:
            f.seek(self.ptr_current)  # Di chuyển vị trí con trỏ tới vị trí hiện tại
            # Nếu vị trí hiện tại cộng với kích thước chunk nhỏ hơn vị trí kết thúc
            if self.ptr_current >= self.ptr_last:  # Kiểm tra nếu đã đọc hết file
                return b''  # Nếu hết file thì trả về dữ liệu rỗng

            if self.ptr_current + self.size_chunk < self.ptr_last:
                data = f.read(self.size_chunk)
                self.ptr_current += self.size_chunk  # Cập nhật vị trí hiện tại
            else:
                data = f.read(self.ptr_last - self.ptr_current)
                self.ptr_current = self.ptr_last  # Cập nhật vị trí hiện tại
            return data

    def send_data(self):
        self.seq_num = self.received.acknowledge + 1  # Lấy số thứ tự của chunk
        self.chunk = Chunk(self.read_file(), self.seq_num, self.ptr_current)  # Tạo chunk mới
        self._send_data()  # Gửi dữ liệu

    # Hàm gửi dữ liệu
    def _send_data(self):
        total_size = len(self.chunk.to_bytes)  # Tính kích thước dữ liệu cần gửi
        sent_bytes = 0  # Số byte đã gửi

        while sent_bytes < total_size:
            try:
                packet = self.chunk.to_bytes[sent_bytes:sent_bytes + PACKET_SIZE]  # Tách dữ liệu thành từng chunk
                self.socket.sendto(packet, (self.client_ip, self.client_port))  # Gửi chunk tới client
                sent_bytes += len(packet)  # Cập nhật số byte đã gửi
            except BrokenPipeError as e:
                logging.error(f"Thread {self.thread_id}: {e}")
                break

        self.socket.sendto(b"END", (self.client_ip, self.client_port))  # Gửi tín hiệu kết thúc

    def run(self):
        # Nhận địa chỉ IP và cổng của client
        _, (self.client_ip, self.client_port) = self.socket.recvfrom(PACKET_SIZE)
        logging.debug(f"Thread {self.thread_id}: Connection from {self.client_ip}:{self.client_port}.")

        self.socket.settimeout(self.time_out)  # Thiết lập thời gian chờ
        resend = False  # Đánh dấu cần gửi lại
        while self.ptr_current < self.ptr_last:  # Tiếp tục gửi cho đến khi hết dữ liệu
            try:
                if resend:
                    self._send_data()  # Gửi lại dữ liệu
                    resend = False
                else:
                    self.send_data()  # Gửi dữ liệu

                # Chờ phản hồi từ client
                data, _ = self.socket.recvfrom(PACKET_SIZE)  # Nhận dữ liệu từ client
                self.received.decompose(data)  # Phân tách dữ liệu nhận được

                # Kiểm tra checksum và ACK
                if self.received.get_ack and self.received.checksum == self.chunk.checksum:
                    continue  # Thành công, tiếp tục gửi chunk tiếp theo
                else:
                    logging.info(f"Thread {self.thread_id}: Invalid ACK or checksum, resending chunk {self.seq_num}.")
                    resend = True  # Đánh dấu cần gửi lại

            except socket.timeout:
                # Hết thời gian chờ, gửi lại dữ liệu
                logging.info(f"Thread {self.thread_id}: Timeout, resending {self.chunk}")
                resend = True  # Đánh dấu cần gửi lại

            time.sleep(self.delay)  # Độ trễ (0.001s) cho mỗi gói

        self.socket.sendto(b"exit", (self.client_ip, self.client_port))  # Gửi tín hiệu kết thúc
        logging.info(f"Thread {self.thread_id}: File sent successfully. File name: {self.file_path}.")
        self.close()  # Đóng kết nối


# Hàm đọc file JSON
def extract_file_content(file_path: str) -> bytes:
    try:
        with open(file_path, 'rb') as file:
            data = json.load(file)  # Đọc file JSON
            return json.dumps(data).encode()
    except FileNotFoundError:
        logging.error(f"File {file_path} not found.")
        return b""  # Trả về bytes rỗng nếu tệp không tồn tại
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        return b""  # Trả về bytes rỗng nếu xảy ra lỗi khác


class Server:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT, file_path=FILE_PATH):
        self.host = host  # Địa chỉ IP của server
        self.port = port  # Cổng của server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Tạo socket
        self.files_list = extract_file_content(file_path)  # Danh sách các file có thể download
        self.request = b''  # Request từ client file cần download
        self.files_send = ''  # File đang được gửi
        self.client_ip = ''  # Địa chỉ của client
        self.client_port = 0  # Cổng của client
        self.is_busy = False  # Đánh dấu server đang bận,chỉ nhận duy nhất 1 kết nối

        """ Bind socket """
        self.server_socket.bind((self.host, self.port))  # Bind socket

    # Hàm bắt đầu server
    def start_server(self):
        # Chờ client kết nối
        while True:
            try:
                # Nhận dữ liệu từ client
                data, (self.client_ip, self.client_port) = self.server_socket.recvfrom(PACKET_SIZE)
                self.is_busy = True  # Đánh dấu server đang bận

                if data == b'connection closed':
                    logging.error("Server can be closed.")
                    break

                # Nhận tính hiệu kết nối
                print(f"Received connection from {self.client_ip}:{self.client_port}")
                # Gửi danh sách file tới client
                self.server_socket.sendto(self.files_list, (self.client_ip, self.client_port))
                break
            except Exception as e:
                logging.error(f"Error receiving connection: {e}")

    # Hàm đóng kết nối
    def close(self):
        self.server_socket.close()

    def rebind(self):
        logging.warning("Rebinding server.")
        self.start_server()  # Tiếp tục tìm kiếm client

    def disconnect(self):
        print(f"Connection from {self.client_ip}:{self.client_port} closed.")
        self.is_busy = False  # Đánh dấu server không bận
        self.client_ip = ''  # Đặt lại địa chỉ IP của client
        self.client_port = 0  # Đặt lại cổng của client
        logging.warning(f"Connection from {self.client_ip}:{self.client_port} closed.")

    def shutdown(self):
        if self.host == self.client_ip:
            logging.critical("Server closed.")
            print("Server closed.")
            self.close()  # Đóng kết nối

    # Hàm nhận request từ client là list file cần download
    def get_request(self) -> str:
        try:
            # Giải mã bytes thành chuỗi
            return self.request.decode('utf-8')  # Giải mã bytes thành chuỗi (str) với encoding UTF-8
        except UnicodeDecodeError as e:
            logging.warning(f"Error decoding request: {e}")
            return ''  # Trả về danh sách rỗng nếu có lỗi khi giải mã

    # Kiểm tra sự tồn tại của file
    def is_exist_file(self):
        if not os.path.exists(self.files_send):
            logging.warning(f"File {self.files_send} not found.")
            print(f"File {self.files_send} not found.")
            return False
        return True

    def run(self):
        self.start_server()  # Nhận kết nối của client và gửi file JSON

        while True:
            # Nhận request từ client
            self.request, address = self.server_socket.recvfrom(PACKET_SIZE)

            # Kiểm tra kết nối từ client có phải là kết nối đang xử lý hay không
            if self.is_busy and address != (self.client_ip, self.client_port):
                logging.warning(f"Connection from {address} rejected.")
                continue

            if self.request == b'shutdown':
                self.shutdown()
                break
            elif self.request == b'exit':
                self.disconnect()  # Ngắt kết nối với client
                self.rebind()  # Khởi động lại kết nối
                continue
            else:
                print(f"Received request: {self.get_request()}")

            self.files_send = self.get_request()  # Tách chuỗi thành file cần download

            # Kiểm tra sự tồn tại của file
            if not self.is_exist_file():
                self.files_send = ''  # Đặt lại tên file
                self.server_socket.sendto(b'-1', (self.client_ip, self.client_port))
                continue

            data_size = os.path.getsize(self.files_send)  # Kích thước file

            # Tao thread để gửi file
            threads = []
            for i in range(NUM_THREADS):
                ptr_first = i * data_size // NUM_THREADS
                ptr_last = (i + 1) * data_size // NUM_THREADS
                thread = SendThread(self.host, self.port + i + 1, self.files_send, i + 1, ptr_first, ptr_last)
                threads.append(thread)
                thread.start()

            # Gửi kích thước file
            self.server_socket.sendto(str(data_size).encode(), (self.client_ip, self.client_port))

            for thread in threads:
                thread.join()

            print(f"File sent successfully. File name: {self.files_send}.")
            self.files_send = ''  # Đặt lại tên file


if __name__ == "__main__":
    server = Server(SERVER_HOST, SERVER_PORT, FILE_PATH)
    server.run()
