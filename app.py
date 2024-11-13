from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
from web3.exceptions import ContractLogicError
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

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

contract_abi_path = os.path.join('compiled_contract', 'HashStorage_sol_HashStorage.abi')

with open(contract_abi_path, 'r') as file:
    contract_abi = json.load(file)

contract_address = Web3.to_checksum_address('0xC2fba0A73D9843f109e235e985648207792Ce18f')
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

class HashData(BaseModel):
    hash_value: str

@app.post("/store-hash/")
async def store_hash(data: HashData):
    try:
        hash_value = data.hash_value
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

        # Use 'raw_transaction' instead of 'rawTransaction'
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"Transaction sent, hash: {tx_hash.hex()}")

        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction receipt: {tx_receipt}")

        block = w3.eth.get_block(tx_receipt['blockHash'])
        timestamp = block['timestamp']

        return {"tx_hash": tx_receipt['transactionHash'].hex(), "timestamp": timestamp, "status": "Hash stored"}
    except ContractLogicError as e:
        print(f"Contract error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Contract error: {str(e)}")
    except Exception as e:
        print(f"Error in store_hash: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/verify-hash/")
async def verify_hash(tx_hash: str):
    try:
        tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
        print(f"Transaction receipt: {tx_receipt}")

        if not tx_receipt:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        logs = tx_receipt['logs']
        print(f"Transaction logs: {logs}")

        event_signature_hash = Web3.keccak(text="HashStored(string,uint256,uint256)").hex()
        event_log = next((log for log in logs if log['topics'][0].hex() == event_signature_hash), None)
        
        if not event_log:
            raise HTTPException(status_code=404, detail="No HashStored event found in the transaction")

        event_data = contract.events.HashStored().process_log(event_log)
        print(f"Decoded event data: {event_data}")

        event_args = event_data['args']
        print(f"Event args: {event_args}")
        
        return {"hash": event_args['hash'], "timestamp": event_args['timestamp'], "index": event_args['index']}
    except Exception as e:
        print(f"Error in verify_hash: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)