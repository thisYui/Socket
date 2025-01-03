import os
import zipfile
import json


def generate_exact_size_zip(target_size_mb, output_zip="output_data.zip"):
    """
    Tạo file zip có kích thước chính xác theo yêu cầu (đơn vị MB).

    Args:
        target_size_mb (int): Kích thước file zip (đơn vị MB).
        output_zip (str): Tên file zip đầu ra.
    """
    target_size_bytes = target_size_mb * 1024 * 1024
    padding_file = "padding_file.tmp"

    # Bước 1: Tạo file zip ban đầu
    with zipfile.ZipFile(output_zip, "w") as zipf:
        # Tạo file tạm có nội dung nhỏ nhất
        zipf.writestr("placeholder.txt", "This is placeholder content.")

    # Kiểm tra kích thước file zip
    current_size = os.path.getsize(output_zip)

    # Bước 2: Thêm padding nếu thiếu
    if current_size < target_size_bytes:
        padding_needed = target_size_bytes - current_size
        with open(padding_file, "wb") as f:
            f.write(b"\0" * padding_needed)

        with zipfile.ZipFile(output_zip, "a") as zipf:
            zipf.write(padding_file, arcname="padding.bin")

        os.remove(padding_file)

    # Bước 3: Kiểm tra và cắt bỏ phần dư (nếu cần)
    current_size = os.path.getsize(output_zip)
    if current_size > target_size_bytes:
        with open(output_zip, "rb+") as f:
            f.truncate(target_size_bytes)  # Cắt bớt file ZIP để đạt kích thước chính xác

    # Xác nhận kích thước cuối cùng
    final_size = os.path.getsize(output_zip)
    if final_size != target_size_bytes:
        raise ValueError(f"Không thể tạo file ZIP kích thước chính xác. Kích thước hiện tại: {final_size} bytes.")

    print(f"File created successfully {target_size_mb}MB: {output_zip}")


def extract_names_and_sizes(json_file):
    """
    Đọc file JSON và trích xuất danh sách tên file và kích thước.

    Args:
        json_file (str): Đường dẫn tới file JSON.

    Returns:
        tuple: (name_list, size_list)
    """
    with open(json_file, "r") as file:
        data = json.load(file)  # Đọc nội dung JSON từ file

    name_list = []
    size_list = []

    for file_entry in data["files"]:
        name, size = file_entry.rsplit(" ", 1)  # Tách theo khoảng trắng từ phải
        name_list.append(name)
        size_list.append(size)

    return name_list, size_list


def convert_to_mb(size_list):
    """
    Chuyển danh sách kích thước từ dạng 'MB' hoặc 'GB' sang số MB (dưới dạng int).

    Args:
        size_list (list): Danh sách kích thước dạng chuỗi (vd. ['5MB', '1GB']).

    Returns:
        list: Danh sách số nguyên kích thước chuyển thành MB.
    """
    result = []
    for size in size_list:
        if size.endswith("MB"):
            result.append(int(size[:-2]))  # Loại bỏ "MB" và chuyển sang số nguyên
        elif size.endswith("GB"):
            result.append(int(size[:-2]) * 1024)  # Chuyển từ GB sang MB
    return result


"""  
Chọn loại giao thức 
Thay đổi biến type_protocol để tạo dữ liệu
Tạo các file có tên và kích thước tương ứng trong file JSON
"""
type_protocol = "UDP"  # Chọn loại giao thức (TCP hoặc UDP)

json_file_path = f"{type_protocol}/server/data_name.JSON"  # Đường dẫn tới file JSON
name_list, size_list = extract_names_and_sizes(json_file_path)
size_list = convert_to_mb(size_list)  # Chuyển kích thước sang MB

print("\nMake file zip:")
for file, size in zip(name_list, size_list):
    link_directory = f"{type_protocol}/server/{file}"
    generate_exact_size_zip(int(size), link_directory)  # Tạo file zip với kích thước từ file JSON
