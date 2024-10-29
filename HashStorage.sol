// example solidity smart contract
pragma solidity ^0.8.0;

contract HashStorage {
    struct HashRecord {
        string hash;
        uint256 timestamp;
    }

    HashRecord[] public records;

    function storeHash(string memory hashValue) public {
        records.push(HashRecord({
            hash: hashValue,
            timestamp: block.timestamp
        }));
    }

    function getRecord(uint index) public view returns (string memory, uint256) {
        HashRecord storage record = records[index];
        return (record.hash, record.timestamp);
    }
}
