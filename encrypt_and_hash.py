from fastapi import FastAPI, HTTPException
from web3 import Web3, HTTPProvider
import os
import json

app = FastAPI()

# Setup Web3 connection
w3 = Web3(Web3.HTTPProvider('https://<network>.infura.io/v3/YOUR_PROJECT_ID'))

# Assuming the compiled contract ABI and the contract address are available
with open('HashStorage.json', 'r') as file:
    contract_json = json.load(file)
    contract_abi = contract_json['abi']
    contract_address = '0xContractAddress'
contract = w3.eth.contract(address=contract_address, abi=contract_abi)


# store the hash
@app.post("/store-hash/")
async def store_hash(hash_value: str):
    account_address = '0xYourAccountAddress'
    private_key = os.getenv('PRIVATE_KEY')

    # Create the transaction
    nonce = w3.eth.getTransactionCount(account_address)
    transaction = contract.functions.storeHash(hash_value).buildTransaction({
        'from': account_address,
        'nonce': nonce,
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return {"tx_hash": tx_receipt.transactionHash.hex(), "status": "Hash stored"}

# Endpoint to verify hash
@app.get("/verify-hash/")
async def verify_hash(tx_hash: str):
    tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
    if not tx_receipt:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Assuming we have the event ABI correctly set up here
    event = contract.events.HashStored()
    event_data = event.processReceipt(tx_receipt)
    if not event_data:
        raise HTTPException(status_code=404, detail="No event found in the transaction")

    event_args = event_data[0]['args']
    return {"hash": event_args['hash'], "timestamp": event_args['timestamp'], "index": event_args['index']}
