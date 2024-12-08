<<<<<<< HEAD
# TCP
Sever: đọc danh sách các file từ JSON ở trạng tahis listening
Client: gửi yêu kết nối, khi serer chấp nhận kết nối server gửi data JSON cho client

1 thread để listen các kết nối từ client
các thread còn lại mỗi thread nối đến 1 client
các client có 1 file input hiện các file cần tải: input.txt
mối 5s client quét 1 file 1 lần, không tải lại các file đã tải và các file đang tải, không xóa file ghi lại mà ghi tiếp
Client download tuần tự từng file 1
file truyền đa luồng
server kết nối nhiều client

+------------------------+----------+
| Header                 | Data     | 
| num_id : 1 bytes       |          |
| chunk_id : 4 bytes     | data     |       
| total : 4 bytes        |          |       
| length_name : 1 bytes  |          |        
| file_name : max 255    |          |       
| offset : 4 bytes       |          |       
+------------------------+----------+

cấu trúc chunk
{
  "num_id":                 8 bits
  "chunk_id":               32 bits
  "total_chunks":           32 bits
  "length_name":            8 bits (255 kí tự tối đa)
  "file_name":              max 255 (2^8 -1 bytes) mã hóa ASCII
  "offset":                 32 bits
  "data":                   max 512KB
}

kích thước chunk: 512KB hoặc 1024KB
Client: mở 4 kết nối song song để tải file
Phương án: chia data thành các chunk, sau đó các chunk sẽ lần lượt được truyền đi qua 4 thread
Server: gửi data cho client
Client: nhận data từ server và ghi vào file

Server chịu trách nhiệm chia file thành các chunk và gửi cho client
Client chịu trách nhiệm nhận data từ server kiểm tra thứ tự, nối data lại và ghi vào file
chunk_size có thể nhỏ hơn 1048 nếu file không là bội số hay kích thước nhỏ hơn 1048
nếu muốn kích thước chuẩn chunk thêm padding và để đủ 1048 

màn hình hiện danh sách các file trong JSON và dung lượng
khi tải hiện % từng part hay từng thread
        Downloading File5.zip part 1 ....  45%
        Downloading File5.zip part 2 ....  15%
        Downloading File5.zip part 3 ....  25%
        Downloading File5.zip part 4 ....  85%
có thể thay bằng thanh progress hoặc hiện cả 2
về phần ngắt kết nối có thể bổ sung sau


Sau khi tải xong file kiểm tra tổng dung lượng file tải về vowis đã đọc trong input.txt
dùng os.path kiểm tra mở file thành công hay ko

# UDP
mỗi server chỉ phục vụ 1 client

+------------------------+-----------------+-------+
| Header                 | Data            |  END  |
| Sequence : 4 bytes     | data            |       |
| checksum : 2 bytes     |                 |       |
| payload : 3 bytes      |                 |       |
| offset : 4 bytes       |                 |       |
+------------------------+-----------------+-------+

cấu trúc chunk server
{
    "sequence_number":      32 bits,
    "checksum":             16 bits,
    "Payload_size":         32 bits,
    "Offset":               32 bits,
    "Data":                 512KB
}

+------------------------+-----------------+-------+
| Header                 | Data            |  END  |
| Acknowledge : 4 bytes  |                 |       |
| checksum : 2 bytes     |                 |       |
| Flags : 1 bytes        |                 |       |
+------------------------+-----------------+-------+

data của client
{
    "Flag":                    8 bits,
    "Acknowledge_number":      32 bits,
    "checksum":                32 bits,
}

Sequence Number	: Đánh số thứ tự gói dữ liệu để phân biệt các gói và đảm bảo đúng thứ tự tại phía nhận.
Acknowledgment Number : Số thứ tự của gói đã được xác nhận (ACK) hoặc yêu cầu gửi lại (NAK).
Checksum : Mã kiểm tra dùng để phát hiện lỗi trong gói dữ liệu.
Flags : Các cờ trạng thái điều khiển, gồm các giá trị như SYN, FIN, ACK, NAK, Retransmit...
Payload Size : Kích thước dữ liệu và chỉ phần dữ liệu trong gói.
Timeout : Thời gian timeout tối đa (tùy chọn, có thể quy định giá trị mặc định ở tầng ứng dụng).

ACK: Xác nhận gói đã nhận đúng.
NAK: Báo lỗi, yêu cầu gửi lại gói

check sum bằng CRC-32
timeout khoảng 2s

khi client nhận được data

trong file được đọc sẽ có 4 con trỏ file đọc file theo 1 phân vị khác nhau
dữ liệu sẽ được đọc và gửi tuần tự và liên tục không lưu trong bộ nhớ
=======
# Socket
>>>>>>> 4d4957f22bf2352b113dfc055e0ebd39b71bcf9e
