from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
from web3.exceptions import ContractLogicError
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from pinata_helper import upload_to_pinata, get_from_pinata
from database import SessionLocal, engine
import crud
import models
import schemas
import logging
from sqlalchemy.orm import Session
import hashlib
import datetime

load_dotenv()


app = FastAPI()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

infura_id = os.getenv('INFURA_ID')
if not infura_id:
    raise Exception("INFURA_ID is not set!")

w3 = Web3(Web3.HTTPProvider(f'https://sepolia.infura.io/v3/{infura_id}'))

if not w3.is_connected():
    raise Exception("Failed to connect to Ethereum network!")

contract_abi_path = os.path.join(
    'compiled_contract',
    'HashStorage_sol_HashStorage.abi')

with open(contract_abi_path, 'r') as file:
    contract_abi = json.load(file)

contract_address = Web3.to_checksum_address(
    '0xC2fba0A73D9843f109e235e985648207792Ce18f')
contract = w3.eth.contract(address=contract_address, abi=contract_abi)


ADMIN_KEY = os.getenv('ADMIN_KEY')


class HashData(BaseModel):
    hash_value: str


@app.delete("/reset-all-data/{admin_key}")
def reset_instructors_test_data(admin_key: str):
    if not admin_key == os.getenv('ADMIN_KEY'):
        raise HTTPException(status_code=404, detail="Invalid key")

    models.Base.metadata.drop_all(
        bind=engine,
        tables=[
            models.User.__table__,
            models.Transaction.__table__])
    models.Base.metadata.create_all(
        bind=engine,
        tables=[
            models.User.__table__,
            models.Transaction.__table__])
    return {"message": "All tables have been reset."}


@app.post("/register", response_model=schemas.User)
async def register(
        username: str,
        password: str,
        db: Session = Depends(get_db)
):
    try:
        user = crud.get_user(db, username)
        if user:
            raise HTTPException(status_code=400, detail="User already exists")

        pass_hash = get_password_hash(password)

        db_user = schemas.UserCreate(uname=username, pass_hash=pass_hash)
        user = crud.create_user(db, db_user)
        user_schema = schemas.User.from_orm(user)
        return user_schema
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transactions/{username}", response_model=list[schemas.Transaction])
async def transactions(username: str, password: str,
                       db: Session = Depends(get_db)):
    try:
        user = crud.get_user(db, username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.pass_hash == get_password_hash(password):
            raise HTTPException(status_code=401, detail="Invalid password")

        user_transactions = crud.get_user_transactions(db, user.id)
        user_transactions = [schemas.Transaction.from_orm(
            transaction) for transaction in user_transactions]
        return user_transactions

    except Exception as e:
        logger.error(f"Error in transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=schemas.UploadResponse)
async def upload(
        email: str,
        password: str,
        decrypt_key_first_last_5: str,
        encrypted_file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    try:
        user = crud.get_user(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.pass_hash == get_password_hash(password):
            raise HTTPException(status_code=401, detail="Invalid password")
        
        file_name = encrypted_file.filename
        file_content = await encrypted_file.read()

        ipfs_hash = upload_to_pinata(file_content)
        ipfs_link = get_ipfs_link(ipfs_hash)

        if not ipfs_hash:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload to IPFS")

        file_hash = get_file_hash(file_content)

        store_hash_info = await store_hash(HashData(hash_value=file_hash))

        response_data = schemas.UploadResponse(
            file_name=file_name,
            file_hash=file_hash,
            tx_hash=store_hash_info['tx_hash'],
            etherscan_url=store_hash_info['etherscan_url'],
            timestamp=convert_unix_to_datetime(store_hash_info['timestamp']),
            ipfs_hash=ipfs_hash,
            ipfs_link=ipfs_link
        )

        db_transaction = schemas.TransactionCreate(
            user_id=user.id,
            file_name=file_name,
            file_hash=file_hash,
            tr_hash=store_hash_info['tx_hash'],
            bc_hash_link=store_hash_info['etherscan_url'],
            bc_file_link=ipfs_link,
            decrypt_key_first_last_5=decrypt_key_first_last_5
        )

        crud.create_transaction(db, db_transaction)
        return response_data

    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/store-hash/")
async def store_hash(data: HashData):
    try:
        hash_value = data.hash_value
        if not hash_value:
            raise HTTPException(status_code=400, detail="Invalid hash")

        account_address = Web3.to_checksum_address(
            '0xc3561A59F3E69C54DAFC1ed26E9d32f6DE293d42')
        private_key = os.getenv('PRIVATE_KEY')

        nonce = w3.eth.get_transaction_count(account_address)
        print(f"Nonce: {nonce}")

        gas_estimate = contract.functions.storeHash(
            hash_value).estimate_gas({'from': account_address})
        print(f"Gas estimate: {gas_estimate}")

        transaction = contract.functions.storeHash(hash_value).build_transaction({
            'from': account_address,
            'nonce': nonce,
            'gas': gas_estimate,
            'maxFeePerGas': w3.eth.max_priority_fee + (2 * w3.eth.get_block('latest')['baseFeePerGas']),
            'maxPriorityFeePerGas': w3.eth.max_priority_fee,
        })
        print(f"Transaction built: {transaction}")

        signed_txn = w3.eth.account.sign_transaction(
            transaction, private_key=private_key)
        print(f"Transaction signed: {signed_txn}")

        # Use 'raw_transaction' instead of 'rawTransaction'
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"Transaction sent, hash: {tx_hash.hex()}")

        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction receipt: {tx_receipt}")

        block = w3.eth.get_block(tx_receipt['blockHash'])
        timestamp = block['timestamp']

        # Create Etherscan URL for Sepolia network
        etherscan_url = f"https://sepolia.etherscan.io/tx/0x{
            tx_receipt['transactionHash'].hex()}"
        print(f"Etherscan URL: {etherscan_url}")

        return {
            "tx_hash": tx_receipt['transactionHash'].hex(),
            "timestamp": timestamp,
            "status": "Hash stored",
            "etherscan_url": etherscan_url
        }
    except ContractLogicError as e:
        print(f"Contract error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Contract error: {
                str(e)}")
    except Exception as e:
        print(f"Error in store_hash: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


async def get_file_hash_from_tx_hash(tx_hash: str):
    try:
        tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
        print(f"Transaction receipt: {tx_receipt}")

        if not tx_receipt:
            raise HTTPException(
                status_code=404,
                detail="Transaction not found")

        logs = tx_receipt['logs']
        print(f"Transaction logs: {logs}")

        event_signature_hash = Web3.keccak(
            text="HashStored(string,uint256,uint256)").hex()
        event_log = next(
            (log for log in logs if log['topics'][0].hex() == event_signature_hash), None)

        if not event_log:
            raise HTTPException(
                status_code=404,
                detail="No HashStored event found in the transaction")

        event_data = contract.events.HashStored().process_log(event_log)
        print(f"Decoded event data: {event_data}")

        event_args = event_data['args']
        print(f"Event args: {event_args}")

        return {"hash": event_args['hash'], "timestamp": convert_unix_to_datetime(
            event_args['timestamp']), "index": event_args['index']}
    except Exception as e:
        print(f"Error in verify_hash: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/verify/{tx_hash}", response_model=schemas.VerifyResponse)
async def verify(tx_hash: str, db: Session = Depends(get_db)):
    try:
        result = await get_file_hash_from_tx_hash(tx_hash)
        file_hash = result['hash']
        timestamp = result['timestamp']

        transaction = crud.get_transaction(db, tx_hash)
        if not transaction:
            raise HTTPException(status_code=404, detail="IPFS link not found")

        ipfs_link = transaction.bc_file_link
        ipfs_hash = ipfs_link.split('/')[-1]
        encrypted_file = get_from_pinata(ipfs_hash)

        if not encrypted_file:
            raise HTTPException(
                status_code=404,
                detail="Failed to fetch from IPFS")

        ipfs_file_hash = get_file_hash(encrypted_file)
        if not ipfs_file_hash == file_hash:
            raise HTTPException(status_code=404, detail="File hash mismatch")

        response = schemas.VerifyResponse(
            file_hash=file_hash,
            timestamp=timestamp,
            bc_file_link=ipfs_link
        )

        return response

    except Exception as e:
        print(f"Error in verify: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# === HELPERS ===
def get_password_hash(key: str) -> str:
    hash_object = hashlib.sha256()
    hash_object.update(key.encode('utf-8'))

    return hash_object.hexdigest()


def get_file_hash(data):
    hasher = hashlib.sha256()
    hasher.update(data)
    hash_256 = hasher.digest()
    return hash_256.hex()


def convert_unix_to_datetime(unix_timestamp):
    return datetime.datetime.fromtimestamp(
        unix_timestamp).strftime('%Y-%m-%d-%H-%M-%S')


def get_ipfs_link(ipfs_hash):
    return f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
