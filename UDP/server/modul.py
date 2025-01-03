import zlib

FILE_PATH = 'data_name.JSON'
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 40000
NUM_THREADS = 8
CHUNK_SIZE = 64*1024
PACKET_SIZE = 1024


class Respond:
    def __init__(self):
        self.ACK = False  # ACK
        self.acknowledge = 0  # Số thứ tự của chunk
        self.checksum = 0  # Checksum của chunk

    def __str__(self):
        return f"Respond: {self.ACK}, {self.acknowledge}, {self.checksum}"

    # Lấy dữ liệu từ bytes đã nhận và chuyển nó trở lại thành Chunk
    def make_response(self, data: bytes):
        chunk = Chunk(b'', 0, 0)  # Tạo một chunk mới
        chunk.decompose(data)  # Tách dữ liệu thành chunk

        # Kiểm tra checksum và payload
        self.ACK = chunk.check_client_checksum(data)  # Kiểm tra checksum của client
        self.acknowledge = chunk.get_seq_num  # Lấy số thứ tự của chunk
        self.checksum = chunk.get_checksum  # Lấy checksum của chunk

    @property
    def get_ack(self):
        return self.ACK

    @property
    def get_acknowledge(self):
        return self.acknowledge

    @property
    def get_checksum(self):
        return self.checksum

    @property
    def to_bytes(self) -> bytes:
        """
        Flags | Acknowledgement  Number | checksum
        """
        return (self.ACK.to_bytes(1, byteorder='big')
                + self.acknowledge.to_bytes(4, byteorder='big')
                + self.checksum.to_bytes(4, byteorder='big'))

    # Dùng để phục hồi từ bytes thành Respond
    def decompose(self, data: bytes):
        self.ACK = bool(data[0])
        self.acknowledge = int.from_bytes(data[1:5], byteorder='big')
        self.checksum = int.from_bytes(data[5:9], byteorder='big')
        return self


class Chunk:
    def __init__(self, data=b'', seq_num=0, offset=0):
        self.seq_num = seq_num  # Số thứ tự của chunk
        self.checksum = zlib.crc32(data)  # Tính checksum
        self.offset = offset  # Vị trí của chunk trong file
        self.payload = len(data)  # Số byte dữ liệu
        self.data = data  # Dữ liệu của chunk

    def __str__(self):
        return f"Chunk: {self.seq_num}, {self.offset}, {self.checksum}, {self.payload}"

    @property
    def get_seq_num(self):
        return self.seq_num

    @property
    def get_checksum(self):
        return self.checksum

    @property
    def get_data(self):
        return self.data

    @property
    def to_bytes(self) -> bytes:
        """
        seq_num (4 bytes) | checksum (4 bytes) | offset (4 bytes) | payload (4 bytes) | data (n bytes)
        seq_num: số thứ tự của chunk
        checksum: giá trị checksum của dữ liệu
        offset: vị trí của chunk trong file
        payload: số byte data trong chunk
        data: dữ liệu
        """

        # Chuyển header thành bytes
        header = (self.seq_num.to_bytes(4, byteorder='big')
                  + self.checksum.to_bytes(4, byteorder='big')
                  + self.offset.to_bytes(4, byteorder='big')
                  + self.payload.to_bytes(4, byteorder='big'))

        # Ghép header và dữ liệu
        return header + self.data

    # Kiểm tra ACK
    def check_client_checksum(self, data: bytes) -> bool:
        check_sum_from_data = zlib.crc32(data[16:])
        return check_sum_from_data == self.checksum

    # Dùng để phục hồi từ bytes thành Chunk
    def decompose(self, data: bytes):
        self.seq_num = int.from_bytes(data[0:4], byteorder='big')
        self.checksum = int.from_bytes(data[4:8], byteorder='big')
        self.offset = int.from_bytes(data[8:12], byteorder='big')
        self.payload = int.from_bytes(data[12:16], byteorder='big')
        self.data = data[16:]
        return self
