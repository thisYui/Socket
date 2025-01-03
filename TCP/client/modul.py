FILE_PATH = 'data_name.JSON'
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 50000
NUM_THREADS = 4  # Number of threads to use for downloading
CHUNK_SIZE = 512 * 1024  # 512KB chunks
PACKET_SIZE = 1024  # 1KB packets
MAX_CLIENTS = 5  # Maximum number of clients to serve
HEADER_SIZE = 18  # Header size in bytes


class Chunk:
    def __init__(self, num_id: int, chunk_id: int, total_chunks: int, length_name: int,
                 file_name: str, offset: int, data: bytes):
        self.num_id = num_id  # Unique ID
        self.chunk_id = chunk_id  # Chunk index
        self.total_chunks = total_chunks  # Total number of chunks
        self.length_name = length_name  # Length of file name
        self.offset = offset  # Offset in file
        self.payload = len(data)  # Length of data
        self.file_name = file_name  # File name
        self.data = data  # Chunk data

    def __str__(self):
        return (f"Chunk ID {self.num_id} number {self.chunk_id} of "
                f"{self.total_chunks} for {self.file_name} , payload {self.payload}")

    @property
    def get_num_id(self):
        return self.num_id

    @property
    def get_total(self):
        return self.total_chunks

    @property
    def get_chunk_id(self):
        return self.chunk_id

    @property
    def get_file_name(self):
        return self.file_name

    @property
    def get_data(self):
        return self.data

    def set_data(self, data: bytes):
        self.data = data
        self.payload = len(data)

    @property
    def get_payload(self):
        return self.payload

    def to_bytes(self) -> bytes:
        """
        Convert chunk to bytes for sending over network
        num_id | length | payload | id | total | offset | name |  data
        1B     | 1B     | 4B       |4B | 4B    | 4B    | xB    |  xB
        """
        return self.header_to_bytes() + self.data_to_bytes()

    def header_to_bytes(self) -> bytes:
        """
        Convert chunk to bytes for sending over network
        num_id | length | payload | id | total | offset | name |  data
        1B     | 1B     | 4B       |4B | 4B    | 4B    | xB    |  xB
        """
        header = (self.num_id.to_bytes(1, byteorder='big') +
                  self.length_name.to_bytes(1, byteorder='big') +
                  self.payload.to_bytes(4, byteorder='big') +
                  self.chunk_id.to_bytes(4, byteorder='big') +
                  self.total_chunks.to_bytes(4, byteorder='big') +
                  self.offset.to_bytes(4, byteorder='big'))

        return header

    def data_to_bytes(self) -> bytes:
        return self.file_name.encode() + self.data

    def decompose(self, data: bytes):
        """Extract chunk data from bytes"""
        self.num_id = int.from_bytes(data[0:1], byteorder='big')
        self.length_name = int.from_bytes(data[1:2], byteorder='big')
        self.payload = int.from_bytes(data[2:6], byteorder='big')
        self.chunk_id = int.from_bytes(data[6:10], byteorder='big')
        self.total_chunks = int.from_bytes(data[10:14], byteorder='big')
        self.offset = int.from_bytes(data[14:18], byteorder='big')
        self.file_name = data[18:18 + self.length_name].decode()
        self.data = data[18 + self.length_name:]
        return self
