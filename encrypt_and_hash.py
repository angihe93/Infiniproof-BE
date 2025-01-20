import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import hashlib
import sys
import requests
import logging

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

    if isinstance(key, str):
        try:
            key = bytes.fromhex(key) # convert key to bytes if it is a string
        except Exception as e:
            logging.error(f"Error converting key to bytes: {e}")
            return None
    try:
        aesgcm = AESGCM(key)
    except Exception as e:
        logging.error(f"Error with AESGCM(key): {e}")
        return None
    
    try:
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        logging.error("except InvalidTag")
        print("Failed to decrypt. The ciphertext may have been tampered with or the wrong key was used.")
        return None

    filename, file_data = decrypted_data.split(b'\x00', 1)
    return filename.decode(), file_data

def decrypt_file_from_link(encrypted_file_link, encryption_key):
    response = requests.get(encrypted_file_link)
    response.raise_for_status()  # check if request successful
    return decrypt_file(response.content, encryption_key)


# main to test decrypt_file_from_link
# example: 
# python3 encrypt_and_hash.py https://gateway.pinata.cloud/ipfs/QmeFkK2V9PKD37i6cLiPxBXSAqkds4e5e8vs2vWtCHgmjX 89accf71c6c12863f0f9471ff41a85349dc1ed8d27e532bd37e2cfafc697f570
def main():
    #demo file key:
    "8304ce05712e15215d2e41ea2df9f681ec20ffd298316c6b851456d25e5ae8f2"
    encrypted_file_link = sys.argv[1]
    key = sys.argv[2]
    key = bytes.fromhex(key)
    
    result = decrypt_file_from_link(encrypted_file_link, key)
    if result:
        filename, file_data = result
        print("############### decrypted file ###############\n")
        print(f"Decrypted file: {filename}")
        with open(f"decrypted_{filename}", 'wb') as f:
            f.write(file_data)
            print(file_data)
            print("\n")
            print("File restored successfully")
        f.close()

if __name__ == "__main__":
    main()
    
    # MysteryFile is the encrypted text of DemoFile
    # To demonstrate, in decryptionDemo/ run:
    # python encrypt_and_hash.py MysteryFile 8304ce05712e15215d2e41ea2df9f681ec20ffd298316c6b851456d25e5ae8f2