from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from web3 import Web3
from web3.exceptions import ContractLogicError
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from pinata_helper import upload_file_to_pinata, fetch_from_ipfs_using_pinata  # Import the IPFS helper function
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
from database import SessionLocal, engine

# Load environment variables
load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Setup web3 connection
infura_id = os.getenv('INFURA_ID')
if not infura_id:
    raise Exception("INFURA_ID is not set!")

w3 = Web3(Web3.HTTPProvider(f'https://sepolia.infura.io/v3/{infura_id}'))

if not w3.is_connected():
    raise Exception("Failed to connect to Ethereum network!")

# Load contract ABI
contract_abi_path = os.path.join('compiled_contract', 'HashStorage_sol_HashStorage.abi')

with open(contract_abi_path, 'r') as file:
    contract_abi = json.load(file)

contract_address = Web3.to_checksum_address('0xC2fba0A73D9843f109e235e985648207792Ce18f')
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

class HashData(BaseModel):
    hash_value: str
    ipfs_hash: str

# Create tables
models.Base.metadata.create_all(bind=engine)

# Add this database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/upload-to-ipfs/")
async def upload_to_ipfs(file: UploadFile = File(...)):
    """
    Upload a file to IPFS using Pinata.
    """
    try:
        # Ensure the temp directory exists
        os.makedirs("temp", exist_ok=True)
        
        # Save the uploaded file temporarily in the temp directory
        file_location = f"temp/{file.filename}"
        with open(file_location, "wb") as buffer:
            buffer.write(await file.read())
        
        # Upload the file to IPFS via Pinata
        print("Uploading file to Pinata...")
        ipfs_hash = upload_file_to_pinata(file_location)

        if not ipfs_hash:
            raise HTTPException(status_code=500, detail="Failed to upload file to IPFS via Pinata")
        
        print(f"File uploaded to Pinata successfully, IPFS Hash (CID): {ipfs_hash}")

        return {"ipfs_hash": ipfs_hash}
    except Exception as e:
        print(f"Error in upload_to_ipfs: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/store-hash/")
async def store_hash(data: HashData, db: Session = Depends(get_db)):
    """
    Store a hash value on the Ethereum blockchain.
    """
    try:
        print("=== Starting store_hash endpoint ===")
        print(f"Received data: {data}")
        
        hash_value = data.hash_value
        ipfs_hash = data.ipfs_hash
        print(f"Received hash_value: {hash_value}")
        print(f"Received IPFS hash: {ipfs_hash}")
        
        if not hash_value:
            raise HTTPException(status_code=400, detail="Invalid hash")
        
        account_address = Web3.to_checksum_address('0xc3561A59F3E69C54DAFC1ed26E9d32f6DE293d42')
        private_key = os.getenv('PRIVATE_KEY')

        nonce = w3.eth.get_transaction_count(account_address)
        print(f"Nonce: {nonce}")
        
        gas_estimate = contract.functions.storeHash(hash_value).estimate_gas({'from': account_address})
        print(f"Gas estimate: {gas_estimate}")
        
        transaction = contract.functions.storeHash(hash_value).build_transaction({
            'from': account_address,
            'nonce': nonce,
            'gas': gas_estimate,
            'maxFeePerGas': w3.eth.max_priority_fee + (2 * w3.eth.get_block('latest')['baseFeePerGas']),
            'maxPriorityFeePerGas': w3.eth.max_priority_fee,
        })
        print(f"Transaction built: {transaction}")

        signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
        print(f"Transaction signed: {signed_txn}")

        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"Transaction sent, hash: {tx_hash.hex()}")

        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction receipt: {tx_receipt}")

        block = w3.eth.get_block(tx_receipt['blockHash'])
        timestamp = block['timestamp']

        # Store in database with IPFS hash
        db_transaction = models.Transaction(
            tr_hash=tx_receipt['transactionHash'].hex(),
            bc_hash_link=hash_value,
            ipfs_cid=data.ipfs_hash,  # Make sure this is being stored
            user_id=1
        )
        db.add(db_transaction)
        db.commit()
        
        print(f"Stored transaction with IPFS hash: {data.ipfs_hash}")  # Debug log

        return {
            "tx_hash": tx_receipt['transactionHash'].hex(),
            "timestamp": timestamp,
            "status": "Hash stored",
            "ipfs_hash": data.ipfs_hash
        }
    except ContractLogicError as e:
        print(f"Contract error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Contract error: {str(e)}")
    except Exception as e:
        print(f"Error in store_hash: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/verify-hash/")
async def verify_hash(tx_hash: str, db: Session = Depends(get_db)):
    """
    Verify the hash stored on the Ethereum blockchain.
    """
    try:
        # Get blockchain data
        tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
        if not tx_receipt:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Get database record
        db_transaction = db.query(models.Transaction).filter(
            models.Transaction.tr_hash.ilike(f"%{tx_hash}")
        ).first()
        
        print(f"Found transaction in DB: {db_transaction}")  # Debug log
        if db_transaction:
            print(f"IPFS CID from DB: {db_transaction.ipfs_cid}")  # Debug log

        # Get blockchain event data
        event_signature_hash = Web3.keccak(text="HashStored(string,uint256,uint256)").hex()
        event_log = next((log for log in tx_receipt['logs'] if log['topics'][0].hex() == event_signature_hash), None)
        
        if not event_log:
            raise HTTPException(status_code=404, detail="No HashStored event found")

        event_data = contract.events.HashStored().process_log(event_log)
        event_args = event_data['args']
        
        return {
            "hash": event_args['hash'],
            "timestamp": event_args['timestamp'],
            "index": event_args['index'],
            "ipfs_hash": db_transaction.ipfs_cid if db_transaction else None
        }
        
    except Exception as e:
        print(f"Error in verify_hash: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
