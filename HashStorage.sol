// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract HashStorage {
    struct HashRecord {
        string hash;
        uint256 timestamp;
    }

    HashRecord[] public records;

    // event to later find the hash
    event HashStored(string hash, uint256 timestamp, uint index);

    function storeHash(string memory hashValue) public {
        records.push(HashRecord({
            hash: hashValue,
            timestamp: block.timestamp
        }));
        emit HashStored(hashValue, block.timestamp, records.length - 1);
    }

    function getRecord(uint index) public view returns (string memory, uint256) {
        HashRecord storage record = records[index];
        return (record.hash, record.timestamp);
    }
}
