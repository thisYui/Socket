import socket
import json
import os
import threading
import logging
from modul import Respond, NUM_THREADS, SERVER_HOST, SERVER_PORT, PACKET_SIZE

# Cấu hình logger cho client
logging.basicConfig(
    filename='client.log',      # Ghi log vào file 'client.log'
    filemode='w',                   # Chế độ ghi lại, xóa hết file mỗi lần chạy
    encoding='utf-8',               # Mã hóa UTF-8
    level=logging.INFO,            # Mức độ ghi log
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def get_data_from_chunk(data: bytes) -> bytes:
    return data[16:]


class ReceiveThread(threading.Thread):
    def __init__(self, server_host: str, server_port: int, thread_id: int):
        super().__init__()
        self.server_host = server_host  # Địa chỉ IP của server tương ứng
        self.server_port = server_port  # Cổng của server tương ứng
        self.thread_id = thread_id  # ID của thread
        self.time_out = 1  # Thời gian chờ: 1s
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.response = Respond()  # Respond từ client

    def close(self):
        self.client_socket.close()

    def write_file(self, data):
        """Ghi dữ liệu vào file."""
        with open(f"{self.thread_id}.bin", 'ab') as f:
            f.write(data)

    def run(self):
        """Chạy thread để nhận dữ liệu và cập nhật tiến trình."""
        self.client_socket.sendto(b'CONNECT', (self.server_host, self.server_port))
        logging.debug(f"Thread {self.thread_id} is running.")

        ack_num = 0  # Số thứ tự của chunk
        self.client_socket.settimeout(self.time_out)
        while True:
            data = b''  # Đọc file vào data khi đã nhận toàn bộ chunk và ghi vào file
            while True:
                try:
                    packet, _ = self.client_socket.recvfrom(PACKET_SIZE)

                    if packet == b'END':  # Nhận tín hiệu kết thúc
                        logging.debug(f"Thread {self.thread_id}: Received END signal.")
                        break
                    if packet == b'exit':  # Kết thúc file
                        logging.warning(f"Thread {self.thread_id} closed.")
                        self.close()
                        return
                    data += packet

                except socket.timeout:
                    logging.warning(f"Thread {self.thread_id}: Timeout. {self.response}. Resending ACK.")

            # Lấy dữ liệu từ packet
            self.response.make_response(data)

            if ack_num > self.response.get_acknowledge:
                logging.warning(f"Thread {self.thread_id}: Duplicate file.")
                continue

            if self.response.get_ack:  # Kiểm tra ACK
                ack_num = self.response.get_acknowledge  # Lấy số thứ tự của chunk
                self.write_file(get_data_from_chunk(data))  # Ghi dữ liệu vào file
            else:
                logging.warning(f"Thread {self.thread_id}: {self.response}.")

            # Gửi ACK cho server
            self.client_socket.sendto(self.response.to_bytes, (self.server_host, self.server_port))


class Client:
    def __init__(self, server_host: str, server_port: int, file_input: str):
        self.server_host = server_host  # Địa chỉ IP của server
        self.server_port = server_port  # Cổng của server
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Tạo socket UDP
        self.file_input = file_input  # File chứa danh sách các file cần tải
        self.file_current = ""  # Tên file đang nhận
        self.files = []  # Danh sách file cần lưu
        self.files_downloaded = []  # Danh sách file đã tải

    def close(self):
        self.client_socket.close()

    def get_json_file(self) -> dict:
        # Gửi yêu cầu lấy danh sách file từ server cũng là yêu cầu kết nối
        self.client_socket.sendto(b'Get_file_list', (self.server_host, self.server_port))

        try:
            data, _ = self.client_socket.recvfrom(PACKET_SIZE)  # Nhận dữ liệu từ server
            data = json.loads(data.decode())  # Giải mã dữ liệu JSON

            # Kiểm tra nếu dữ liệu có trường 'files'
            if 'files' in data:
                return data  # Trả về dữ liệu chứa danh sách file
            else:
                logging.error("Error: Invalid JSON data received.")
                return {}
        except json.JSONDecodeError:
            logging.error("Error: Invalid JSON data received.")
            return {}
        except Exception as e:
            logging.error(f"Error: {e}")
            return {}

    def read_file(self) -> list[str]:
        lines = []
        try:
            with open(self.file_input, "r", encoding="utf-8") as file:
                lines = file.readlines()
            # Loại bỏ ký tự xuống dòng nếu cần
            lines = [line.strip() for line in lines]
        except FileNotFoundError:
            logging.error(f"File '{self.file_input}' không tồn tại!")
        except Exception as e:
            logging.error(f"Lỗi xảy ra: {e}")
        return lines

    def merge_files(self):
        """
        file_current (str): Tên file đầu ra.
        input_files (str): Tên các file đầu vào.
        """
        input_files = []
        for i in range(NUM_THREADS):
            if os.path.exists(f"{i + 1}.bin"):
                input_files.append(f"{i + 1}.bin")

        try:
            with open(self.file_current, 'wb') as outfile:
                for input_file in input_files:
                    with open(input_file, 'rb') as infile:
                        outfile.write(infile.read())

            # Xóa các file cũ sau khi gộp
            for input_file in input_files:
                try:
                    os.remove(input_file)  # Xóa file
                    logging.debug(f"Đã xóa file {input_file}.")
                except OSError as e:
                    logging.error(f"Không thể xóa file {input_file}: {e}")

            logging.info(f"Đã gộp file vào {self.file_current} thành công.")
        except FileNotFoundError as e:
            logging.error(f"Lỗi: {e}")
        except Exception as e:
            logging.error(f"Đã xảy ra lỗi: {e}")

    def get_information(self):
        # Sever khi nhận kết nối, server sẽ gửi cho client 1 file JSON chứa danh sách các file có thể download
        json_file = self.get_json_file()  # Nhận danh sách các file từ server

        # In danh sách đó ra terminal
        if 'files' in json_file:
            print("Available files:")
            for file in json_file['files']:
                print(f"- {file}")

    def filter_files(self):
        """
        Lọc ra các file đã tải thành công.
        """
        lst_files = self.read_file()
        print(lst_files)
        for i in lst_files:
            if i not in self.files_downloaded:
                self.files.append(i)  # Thêm file vào danh sách cần tải

    def run(self):
        self.get_information()  # Lấy thông tin từ server

        # người dùng đọc file json và chọn các file cần lưu
        print("\nPlease please enter the file list into input.txt. "
              "Press Enter to continue.")
        while True:
            if input() == '':
                break

        self.files = self.read_file()  # Đọc file
        while True:
            if not self.files:
                print(f"\nNo files to download. If there are no further requests please press enter to exit."
                      f"If so, delete the previous requests and add the new ones. After that, input 'more' and Enter.\n"
                      f"Do you want to continue? (Press Enter to exit, type 'more' to continue): \n > ", end='')

                if input().lower() == 'more':
                    self.filter_files()  # Đọc file và lọc ra các file đã tải thành công
                    continue
                else:
                    logging.warning("Client closed.")
                    break  # Dừng client

            self.file_current = self.files.pop(0)  # Lấy file đầu tiên trong danh sách

            # Gửi tên file cần nhận
            print(f"Requesting file: {self.file_current}")
            self.client_socket.sendto(self.file_current.encode('utf-8'), (self.server_host, self.server_port))

            data, _ = self.client_socket.recvfrom(PACKET_SIZE)  # Nhận kích thước dữ liệu của file
            data_size_file_current = int(data.decode())  # Chuyển dữ liệu từ bytes sang int
            logging.info(f"Data size: {data_size_file_current}")  # In kích thước dữ liệu

            if data_size_file_current < 0:
                print(f"File {self.file_current} not found.")
                self.file_current = ""  # Đặt file_current thành rỗng để kiểm tra file tiếp theo
                continue

            '''
            Các port của các thread bên phía server cách đều nhau 1 đơn vị
            có tổng cộng NUM_THREADS thread
            '''
            threads = []
            for i in range(NUM_THREADS):
                thread = ReceiveThread(self.server_host, self.server_port + 1 + i, i + 1)
                threads.append(thread)
                thread.start()

            # Chờ cho đến khi tất cả các thread đã hoàn thành
            for thread in threads:
                thread.join()

            logging.info("Merging files...")  # Gộp các file thành một file duy nhất
            self.merge_files()  # Gộp các file do các thread nhận được thành một file duy nhất
            self.files_downloaded.append(self.file_current)  # Thêm file đã tải vào danh sách
            self.file_current = ""  # Đặt file_current thành rỗng để kiểm tra file tiếp theo

        self.client_socket.sendto(b'exit', (self.server_host, self.server_port))  # Gửi tín hiệu kết thúc
        self.close()  # Đóng kết nối


if __name__ == "__main__":
    FILE_INPUT = 'input.txt'  # File chứa danh sách các file cần download

    # Tạo và chạy client
    client = Client(SERVER_HOST, SERVER_PORT, FILE_INPUT)
    client.run()
