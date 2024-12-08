FILE_PATH = 'data_name.JSON'
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 50000
NUM_THREADS = 4  # Number of threads to use for downloading
CHUNK_SIZE = 512 * 1024  # 512KB chunks
MAX_CLIENTS = 5  # Maximum number of clients to serve


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
        return (f"Chunk ID {self.num_id} number {self.chunk_id} of {self.total_chunks} "
                f"for {self.file_name} , payload {self.payload}, Offset {self.offset}")

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

    @property
    def get_payload(self):
        return self.payload

    def to_bytes(self) -> bytes:
        """
        Convert chunk to bytes for sending over network
        num_id | payload | id | total | length | offset | name |  data
        1B     | 3B       |4B | 4B    | 4B     | 4B    | xB    |  xB
        """
        return self. header_to_bytes() + self.data_to_bytes()

    def header_to_bytes(self) -> bytes:
        """
        Convert chunk to bytes for sending over network
        num_id | payload | id | total | length | offset | name |  data
        1B     | 3B       |4B | 4B    | 4B     | 4B    | xB    |  xB
        """
        header = (self.num_id.to_bytes(1, byteorder='big') +
                  self.payload.to_bytes(3, byteorder='big') +
                  self.chunk_id.to_bytes(4, byteorder='big') +
                  self.total_chunks.to_bytes(4, byteorder='big') +
                  self.length_name.to_bytes(4, byteorder='big') +
                  self.offset.to_bytes(4, byteorder='big'))

        return header

    def data_to_bytes(self) -> bytes:
        return self.file_name.encode() + self.data

    def decompose(self, data: bytes):
        """Extract chunk data from bytes"""
        self.num_id = int.from_bytes(data[0:1], byteorder='big')
        self.payload = int.from_bytes(data[1:4], byteorder='big')
        self.chunk_id = int.from_bytes(data[4:8], byteorder='big')
        self.total_chunks = int.from_bytes(data[8:12], byteorder='big')
        self.length_name = int.from_bytes(data[12:16], byteorder='big')
        self.offset = int.from_bytes(data[16:20], byteorder='big')
        self.file_name = data[20:20 + self.length_name].decode()
        self.data = data[20 + self.length_name:]
        return self
