from fastapi import FastAPI, HTTPException
from web3 import Web3
import json
import os

app = FastAPI()

w3 = Web3(Web3.HTTPProvider('https://<network>.infura.io/v3/YOUR_PROJECT_ID'))
if not w3.isConnected():
    raise Exception("Failed to connect to Ethereum network!")


with open('HashStorage.json', 'r') as file:     # compiled contract JSON
    contract_json = json.load(file)
    contract_abi = contract_json['abi']

contract_address = '0xContractAddress'  # address of where the contract was deployed
contract = w3.eth.contract(address=contract_address, abi=contract_abi)


@app.post("/upload-hash/")
async def upload_hash(hash_value: str):
    try:
        estimated_gas = contract.functions.storeHash(hash_value).estimateGas({
            'from': w3.eth.accounts[0]
        })

        tx_hash = contract.functions.storeHash(hash_value).transact({
            'from': w3.eth.accounts[0],
            'gas': estimated_gas
        })

        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        record = contract.functions.getRecord(contract.functions.records().call() - 1).call()

        return {"hash": record[0], "timestamp": record[1], "transaction_hash": tx_receipt.transactionHash.hex()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
