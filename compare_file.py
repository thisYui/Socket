import os


def read_file(file_input) -> list[str]:
    lines = []
    try:
        with open(file_input, "r", encoding="utf-8") as file:
            lines = file.readlines()
        # Loại bỏ ký tự xuống dòng nếu cần
        lines = [line.strip() for line in lines]
    except FileNotFoundError:
        print(f"File '{file_input}' Not found!")
    except Exception as e:
        print(f"Error: {e}")
    return lines


def compare_files(file1, file2):
    """
    So sánh nội dung của hai file.

    Parameters:
        file1 (str): Tên file thứ nhất.
        file2 (str): Tên file thứ hai.

    Returns:
        bool: True nếu hai file giống nhau, False nếu khác nhau.
    """
    try:
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            return f1.read() == f2.read()
    except FileNotFoundError as e:
        print(f"Lỗi: {e}")
        return False
    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
        return False


""" 
Nếu test chương trình trên loopback thì run chương trình
Nếu test trên 2 máy thì chạy trên máy client
có thể gửi file 2 lần rồi kiểm tra 2 file này
hoặc có thể sử dụng một ứng dụng khác để gửi file qua cho client và client sẽ kiểm tra
"""

'''Chọn loại giao thức'''
type_protocol = "TCP"
lst_files = read_file(f"{type_protocol}/client/input.txt")
for i in lst_files:
    print(f"File name: {i}")
    des = f"{type_protocol}/server/{i}"  # File nhận
    src = f"{type_protocol}/client/{i}"  # Suorce file

    result = compare_files(des, src)
    if result:
        print("The same file.")
        print(f"File size: {os.path.getsize(des)/(1024*1024)} MB")
    else:
        print("The differance file.")
        print(f"File des size: {os.path.getsize(des)/(1024*1024)} MB")
        print(f"File source size: {os.path.getsize(src)/(1024*1024)} MB")
