import hashlib
from io import BytesIO


def calculate_file_hash(file: BytesIO) -> str:
    file_hash = hashlib.md5()
    file.seek(0)  # Ensure we start from the beginning of the file
    while chunk := file.read(8192):
        file_hash.update(chunk)
    file.seek(0)  # Reset file pointer to the beginning
    return file_hash.hexdigest()
