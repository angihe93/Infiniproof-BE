import os
import requests
from dotenv import load_dotenv

load_dotenv()

PINATA_API_KEY = os.getenv('PINATA_API_KEY')
PINATA_SECRET_KEY = os.getenv('PINATA_SECRET_KEY')

# Add debug prints
print(f"PINATA_API_KEY loaded: {'Yes' if PINATA_API_KEY else 'No'}")
print(f"PINATA_SECRET_KEY loaded: {'Yes' if PINATA_SECRET_KEY else 'No'}")


def upload_to_pinata(file_content: bytes) -> str:
    try:
        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"

        # Print the headers being sent
        headers = {
            'pinata_api_key': PINATA_API_KEY,
            'pinata_secret_api_key': PINATA_SECRET_KEY
        }
        print(f"Headers being sent: {headers}")

        files = {
            'file': file_content
        }

        response = requests.post(url, headers=headers, files=files)

        if response.status_code == 200:
            return response.json()['IpfsHash']
        else:
            print(f"Error uploading to Pinata: {response.text}")
            return None

    except Exception as e:
        print(f"Error in upload_to_pinata: {str(e)}")
        return None


def get_from_pinata(ipfs_hash: str) -> bytes:
    try:
        gateway_url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"
        response = requests.get(gateway_url)

        if response.status_code == 200:
            return response.content
        else:
            print(f"Error fetching from Pinata: {response.text}")
            return None

    except Exception as e:
        print(f"Error in get_from_pinata: {str(e)}")
        return None
