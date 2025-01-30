# MyProject - zstd 
Dự án này thuộc vào học phần Mạng máy tính của trường Đại học Khoa học Tự nhiên,  ĐHQG-TPHCM.

## Description
- Đây là một dự án sử dụng socket để giao tiếp giữa client và server.
- Có thể thực hiện trao đổi dữ liệu giữa client và server bằng 2 giao thức TCP/UDP.
- Dụ án này là dự án cá nhân được thực hiện bởi Nguyễn Quang Duy, sinh viên khóa 2023 thuộc Trường Đại học Khoa học Tự nhiên, ĐHQG-TPHCM.

## Features
- Feature 1: Có thể giao tiếp giữa clinet và server.
- Feature 2: Giao diện dòng lệnh.

## Requirements
- Operating System: Linux / macOS / Windows
- Programming Language: Python 3.12 hoặc bất kì phiên bản tương thích nào khác.
- Dependencies: Được code bằng Pycharm.

## Attention
- Server và client phải ở chung 1 mạng LAN. Mỗi khi chạy phải cập nhật lại địa chỉ IP của server ở cả server và client.
- UDP chỉ hỗ trợ kết nối 1-1, đối với TCP hỗ trợ đa kết nối.
- Khi các file đang được gửi nếu chương trình bị ngắt kết nối đột ngột một số file được chương trình tạo ra sẽ không bị xóa và gây lỗi cho lần chạy tiếp theo người chyaj cần xóa các file này đi.
- Nếu sử dụng VSCode cần chú ý về đường dẫn đọc và ghi file nếu gặp lỗi.
- Khi clone về server không có dữ liệu người dùng có thể tạo dữ liệu random từ file .py tương ứng hoặc bất kì dữ liệu nào khác. Lưu ý khi đó phải chỉnh sữa file JSON để hiển thị chính xác.

## Operating
- Bước 1: Clone dự án về máy của bạn.
- Bước 2: Kiểm tra địa chỉ IP của server và cập nhật ở cả client và server.
- Bước 3: Chạy dự án bằng Pycharm hoặc các IDE/Text Editor khác hoặc Command Prompt/PowerShell/Terminal . Chú ý rằng một số kí tự thoát không hoạt động trong môi trường IDE ưu tiên sử dụng các giao diện dòng lệnh hay Text Edittor.
- Bước 4: Giao tiếp giữa clinet server người dùng sẽ đọc danh sách file của server và có thể yêu cầu server gửi các file đó, chú ý khi chọn file để gửi có thể thêm trực tiếp vào input.txt hoặc dùng file .py để thêm vào ưu tiên dùng .py vì một số chương trình không nhận dạng được ngay lập tức khi thêm thủ công.
