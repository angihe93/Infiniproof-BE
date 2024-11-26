import os
import requests
from dotenv import load_dotenv

load_dotenv()

PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY")

PINATA_BASE_URL = "https://api.pinata.cloud/"
PINATA_PIN_FILE_ENDPOINT = f"{PINATA_BASE_URL}pinning/pinFileToIPFS"
PINATA_GATEWAY = "https://gateway.pinata.cloud/ipfs/"

def upload_file_to_pinata(file_path):
    try:
        if not PINATA_API_KEY or not PINATA_SECRET_API_KEY:
            raise ValueError("Pinata API keys are not set")

        headers = {
            "pinata_api_key": PINATA_API_KEY,
            "pinata_secret_api_key": PINATA_SECRET_API_KEY,
        }

        with open(file_path, "rb") as file:
            files = {"file": file}
            response = requests.post(PINATA_PIN_FILE_ENDPOINT, headers=headers, files=files)

        if response.status_code == 200:
            return response.json().get("IpfsHash")
        else:
            raise Exception(f"Failed to upload to Pinata: {response.text}")
    except Exception as e:
        print(f"An error occurred while uploading to Pinata: {e}")
        return None

def fetch_from_ipfs_using_pinata(ipfs_hash):
    """
    Fetch a file from IPFS using Pinata's gateway.
    """
    try:
        # Use Pinata's gateway or public IPFS gateway
        gateway_url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"
        # Or use public gateway: f"https://ipfs.io/ipfs/{ipfs_hash}"
        
        headers = {
            "pinata_api_key": os.getenv("PINATA_API_KEY"),
            "pinata_secret_api_key": os.getenv("PINATA_API_SECRET")
        }
        
        response = requests.get(gateway_url, headers=headers)
        response.raise_for_status()
        
        return response.content
    except Exception as e:
        print(f"Error fetching from IPFS: {str(e)}")
        return None