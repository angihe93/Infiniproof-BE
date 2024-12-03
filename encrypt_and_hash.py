import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import hashlib
import sys


def encrypt_file(file_path, key):
    nonce = secrets.token_bytes(12)

    with open(file_path, 'rb') as f:
        filename = os.path.basename(file_path)
        file_data = f.read()

    data_to_encrypt = filename.encode() + b'\x00' + file_data

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data_to_encrypt, None)

    return nonce + ciphertext


def create_hash(data):
    hasher = hashlib.sha256()
    hasher.update(data)
    hash_256 = hasher.digest()
    return hash_256.hex()


def decrypt_file(encrypted_data, key):
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]

    aesgcm = AESGCM(key)
    try:
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        print("Failed to decrypt. The ciphertext may have been tampered with or the wrong key was used.")
        return None

    filename, file_data = decrypted_data.split(b'\x00', 1)
    return filename.decode(), file_data


def main():
    file_path = sys.argv[1]
    key = sys.argv[2]
    key = bytes.fromhex(key)
    
    with open(file_path, "rb") as f:
        encrypted_data = f.read()
        print("############### encrypted file ###############")
        print(encrypted_data)

    # encrypted_data = encrypt_file(file_path, key)
    # print("Encryption successful")
    # file_hash = create_hash(encrypted_data)
    # print(f"File hash: {file_hash}")

    result = decrypt_file(encrypted_data, key)
    if result:
        filename, file_data = result
        print(f"Decrypted file: {filename}")
        with open(f"decrypted_{filename}", 'wb') as f:
            f.write(file_data)
            print("############### decrypted file ###############")
            print(file_data)
        print("File restored successfully")


if __name__ == "__main__":
    main()


#3acf844af2098e50e8e017ea9e1f187b21fa254943966a1b1007a34358c41da1