def append_to_file(file_path: str, content: str):
    """
    Thêm dữ liệu vào cuối file.

    :param file_path: Đường dẫn đến file.
    :param content: Chuỗi nội dung cần thêm.
    """
    try:
        with open(file_path, 'a') as file:  # Mở file ở chế độ append
            file.write('\n' + content)  # Thêm nội dung mới và xuống dòng
        print(f"Đã thêm {content} dung vào {file_path}")
    except Exception as e:
        print(f"Lỗi khi thêm dữ liệu vào file: {e}")


lst_file = ['File8.zip']
for file in lst_file:
    append_to_file("input.txt", file)
