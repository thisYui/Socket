import socket
import threading
import json
import time
import os
from threading import Lock
import logging
import sys
from modul import SERVER_HOST, SERVER_PORT, Chunk, NUM_THREADS, HEADER_SIZE, PACKET_SIZE

# Cấu hình logger cho client
logging.basicConfig(
    filename='client.log',      # Ghi log vào file 'client.log'
    filemode='w',                   # Chế độ ghi log, xóa hết file mỗi lần chạy
    encoding='utf-8',               # Mã hóa UTF-8
    level=logging.DEBUG,            # Mức độ ghi log
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def get_length_name_file_from_header(header: bytes) -> int:
    return int.from_bytes(header[1:2], byteorder='big')


def get_payload_from_header(header: bytes) -> int:
    return int.from_bytes(header[2:6], byteorder='big')


class MiniThread(threading.Thread):
    def __init__(self, client_socket: socket.socket, _lock_receive: Lock, _lock_write: Lock, _shared_data: dict):
        super().__init__()
        self.client_socket = client_socket  # Socket kết nối với server
        self._lock_receive = _lock_receive  # Lock để tránh xung đột giữa các thread
        self._lock_write = _lock_write  # Lock để tránh xung đột giữa các thread
        self._shared_data = _shared_data  # Dữ liệu chia sẻ giữa các thread
        self.delay = 0.02  # Độ trễ

    def receive_chunk(self, header_size=HEADER_SIZE, buffer_size=PACKET_SIZE) -> bytes:
        """Receive all data from the server in chunks using the walrus operator."""
        with self._lock_receive:
            try:
                header = self.client_socket.recv(header_size)  # Nhận header
                payload = get_payload_from_header(header)  # Lấy payload từ header
                length_name = get_length_name_file_from_header(header)  # Lấy độ dài tên file từ header
                len_data = payload + length_name  # Tổng độ dài dữ liệu cần nhận

                data = b''  # Dữ liệu nhận được
                while len(data) < len_data:
                    packet = self.client_socket.recv(min(buffer_size, len_data - len(data)))
                    if not packet:  # Kết nối đóng giữa chừng
                        raise ConnectionError("Kết nối bị đóng trong khi nhận dữ liệu.")
                    data += packet
                return header + data  # Ghép tất cả các chunk lại thành dữ liệu hoàn chỉnh

            except ConnectionResetError:
                logging.error("Connection reset by server.")
                return b''

            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                return b''

    def write_file(self, file_name: str, data: bytes):
        with self._lock_write:
            with open(file_name, 'ab') as file:
                file.write(data)

    def make_chunk(self) -> Chunk:
        chunk = Chunk(0, 0, 0, 0, '', 0, b'')
        chunk.decompose(self.receive_chunk())  # Giải mã dữ liệu nhận được thành chunk
        return chunk

    def receive_successfully(self) -> bool:
        """ Kiểm tra tất cả thread đã nhận thành công tất cả các part chưa."""
        for i in range(NUM_THREADS):
            if self._shared_data[f'thread_{i + 1}']["successfully"] is False:
                return False
        return True

    def draw_download_part(self, file_name):
        with self._lock_receive:
            # Di chuyển con trỏ lên số dòng bằng số phần (parts)
            sys.stdout.write(f"\033[{NUM_THREADS}F")
            sys.stdout.flush()
            try:
                # Khởi tạo chuỗi tiến trình download
                progress_output = ''
                for i in range(NUM_THREADS):
                    # Tính toán tiến trình của từng phần
                    progress = ((self._shared_data[f'thread_{i + 1}']['count_chunk'])
                                / (self._shared_data[f'thread_{i + 1}']['total']))
                    progress_output += f"Downloading {file_name} part {i + 1} .... {int(progress * 100)}%\n"

                sys.stdout.write(progress_output)  # Ghi chuỗi tiến trình ra stdout
                sys.stdout.flush()  # Ghi ngay lập tức mà không đợi bộ đệm
                time.sleep(self.delay)  # Delay giữa các lần cập nhật
            except ZeroDivisionError:
                logging.error("ZeroDivisionError: division by zero")

    def run(self):
        while self.receive_successfully() is False:
            chunk = self.make_chunk()  # Tạo chunk từ dữ liệu nhận được

            num_id = chunk.get_num_id  # Lấy số ID của chunk
            total = chunk.get_total  # Lấy tổng số chunk
            self._shared_data[f'thread_{num_id}']['total'] = total  # Cập nhật tổng số chunk vào dữ liệu chia sẻ
            self._shared_data[f'thread_{num_id}']['count_chunk'] += 1  # Cập nhật số lượng chunk đã nhận

            self.write_file(f"{num_id}.bin", chunk.get_data)  # Ghi dữ liệu chunk vào file
            self.draw_download_part(chunk.get_file_name)  # Ghi ra các part đang download
            if chunk.get_chunk_id == chunk.get_total:
                self._shared_data[f'thread_{num_id}']["successfully"] = True
                logging.info(f"Thread {num_id} successfully received all chunks in {chunk.get_file_name}.")
                break


class Client:
    def __init__(self, host, port, file_input):
        self.host = host  # Host của server
        self.port = port  # Port của server
        self.file_input = file_input  # File input
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.file_download_current = ''  # File đang download
        self.files_scan = []  # Danh sách file đã scan
        self.files = {'waiting': [], 'downloaded': []}  # Danh sách file
        self.time_waiting = 5  # Thời gian chờ
        self.json_file = {}  # File JSON
        self.is_live = True  # Trạng thái sống
        self.delay = 0.5  # Độ trễ
        self._lock_receive = threading.Lock()  # Lock để tránh xung đột giữa các thread
        self._lock_write = threading.Lock()  # Lock để tránh xung đột giữa các thread
        self._shared_data = {}  # Dữ liệu chia sẻ giữa các thread

    def close(self):
        self.is_live = False  # Đánh dấu client đã ngừng hoạt động
        self.client_socket.close()

    def make_shared_data(self):
        for i in range(NUM_THREADS):
            thread_name = f"thread_{i + 1}"
            self._shared_data[thread_name] = {'count_chunk': 0,
                                              'total': 0,
                                              'successfully': False}

    def connect(self):
        try:
            self.client_socket.connect((self.host, self.port))
            logging.info(f"Connected to server at {self.host}:{self.port}")
            print(f"Connected to server at {self.host}:{self.port}")
        except ConnectionRefusedError:
            logging.error(f"Connection to server at {self.host}:{self.port} refused.")
            print(f"Connection to server at {self.host}:{self.port} refused.")
            exit(1)  # Thoát chương trình nếu không kết nối được

    def get_json_file(self):
        data = self.client_socket.recv(PACKET_SIZE)  # Nhận file JSON từ server
        data = data.decode()  # Chuyển đổi dữ liệu nhận được thành chuỗi

        # Chuyển đổi chuỗi JSON thành dictionary
        self.json_file = json.loads(data)  # Giải mã JSON thành dict

        # In danh sách đó ra terminal
        if 'files' in self.json_file:
            print("Available files:")
            for file in self.json_file['files']:
                print(f"- {file}")

    def send_request(self):
        self.client_socket.sendall(self.file_download_current.encode())
        logging.info(f"Sent request for {self.file_download_current} from {self.host}:{self.port}")
        print(f"Sent request for {self.file_download_current} from {self.host}:{self.port}")

    def thread_scan_file(self):
        while self.is_live:
            self.files_scan = self.scan_file()  # Scan file input
            self.filter_files()  # Lọc file
            if len(self.files['waiting']) != 0 and self.file_download_current == '':
                self.file_download_current = self.files['waiting'][0]  # Lấy file đầu tiên trong danh sách
            logging.debug(f"Scan files: {self.files_scan}")
            logging.debug(f"Files : {self.files['waiting']}")
            time.sleep(self.time_waiting)  # Đợi 5 giây trước quét lần tiếp theo

    def scan_file(self) -> list[str]:
        try:
            with open(self.file_input, 'r') as file:
                lines = file.readlines()  # Đọc tất cả các dòng trong file
                return [line.strip() for line in lines]  # Loại bỏ ký tự xuống dòng '\n' và trả về danh sách
        except FileNotFoundError:
            logging.error(f"File {self.file_input} not found.")
            print(f"File {self.file_input} not found.")
            return []

    def filter_files(self):
        for file in self.files_scan:
            if file not in self.files['waiting'] and file not in self.files['downloaded']:
                self.files['waiting'].append(file)

    def merge_files(self):
        """
        file_current (str): Tên file đầu ra.
        input_files (str): Tên các file đầu vào.
        """
        input_files = []
        for i in range(NUM_THREADS):
            if os.path.exists(f"{i + 1}.bin"):
                input_files.append(f"{i + 1}.bin")

        if ' ' in self.file_download_current:
            file_name, _ = self.file_download_current.split()  # Tách tên file và offset
        else:
            file_name = self.file_download_current

        try:
            with open(file_name, 'wb') as outfile:
                for input_file in input_files:
                    with open(input_file, 'rb') as infile:
                        outfile.write(infile.read())

            # Xóa các file cũ sau khi gộp
            for input_file in input_files:
                try:
                    os.remove(input_file)  # Xóa file
                    logging.info(f"Đã xóa file {input_file}.")
                except OSError as e:
                    logging.error(f"Không thể xóa file {input_file}: {e}")

            logging.info(f"Đã gộp file vào {self.file_download_current} thành công.")
        except FileNotFoundError as e:
            logging.error(f"Lỗi: {e}")
        except Exception as e:
            logging.error(f"Đã xảy ra lỗi: {e}")

    def check_size_file(self, data_size) -> bool:
        if ' ' in self.file_download_current:
            file_name, _ = self.file_download_current.split()  # Tách tên file và offset
        else:
            file_name = self.file_download_current

        if os.path.exists(file_name):
            size = os.path.getsize(file_name)
            if size == data_size:
                return True

        logging.warning(f"File {self.file_download_current} is not downloaded completely. Retry...")
        print(f"File {self.file_download_current} is not downloaded completely. Retry...")
        self.make_shared_data()  # Đặt lại các giá trị
        return False

    def reset(self):
        self.files['downloaded'].append(self.file_download_current)  # Thêm file đã download vào danh sách
        self.files['waiting'].pop(0)  # Xóa file đã download khỏi danh sách chờ

        if len(self.files['waiting']) != 0:
            self.file_download_current = self.files['waiting'][0]  # Lấy file tiếp theo trong danh sách chờ
        else:
            self.file_download_current = ''

        self.make_shared_data()  # Đặt lại các giá trị trong _share

    def run(self):
        self.make_shared_data()  # Tạo dữ liệu chia sẻ giữa các thread
        self.connect()  # Kết nối đến server
        self.get_json_file()  # Nhận danh sách file từ server và in ra terminal

        scan_thread = threading.Thread(target=self.thread_scan_file)  # Tạo thread quét file
        scan_thread.start()  # Bắt đầu quét file

        while True:
            try:
                if self.file_download_current == '':
                    print("\nAll files have been downloaded. Press Ctrl + C to stop client.\n"
                          "Or add more files to input.txt to download.\n")
                while self.file_download_current == '':
                    pass
            except KeyboardInterrupt:
                logging.error("Ctrl + C detected! Stopping client...")
                print("Ctrl + C detected! Stopping client...")
                break

            time.sleep(self.delay)
            self.send_request()  # Gửi yêu cầu download file

            try:
                data_size = self.client_socket.recv(PACKET_SIZE)  # Nhận kích thước dữ liệu
                data_size = int(data_size.decode('utf-8'))  # Chuyển đổi kích thước dữ liệu thành số nguyên
                if data_size <= 0:
                    logging.warning(f"{self.file_download_current} not found or offset is invalid.")
                    print(f"{self.file_download_current} not found or offset is invalid.")
                    self.reset()  # Đặt lại các giá trị
                    continue
                logging.info(f"Received data size: {data_size}")
                print(f"Received data size: {data_size}")
            except Exception as e:
                logging.error(f"Data size Error: {e}, client be closed.")
                print(f"Data size Error: {e}, client be closed.")
                break

            print('\n' * NUM_THREADS)  # In ra số dòng cho các part
            time.sleep(self.delay)

            threads = []
            for i in range(NUM_THREADS):
                thread = MiniThread(self.client_socket, self._lock_receive, self._lock_write, self._shared_data)
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

            self.merge_files()  # Gộp file
            logging.info(self._shared_data)

            # Kiểm tra xem file đã được download đủ kích thước chưa
            if self.check_size_file(data_size) is True:
                print(f"{self.file_download_current} downloaded successfully.\n")
                self.reset()  # Đặt lại các giá trị

        logging.error(f"Socket closed for {self.host}:{self.port}")
        print(f"Socket closed for {self.host}:{self.port}")
        self.client_socket.sendall(b'exit')  # Gửi yêu cầu ngắt kết nối
        self.client_socket.close()


if __name__ == "__main__":
    FILE_INPUT = 'input.txt'

    client = Client(SERVER_HOST, SERVER_PORT, FILE_INPUT)
    client.run()
