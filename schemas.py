from pydantic import BaseModel


class TransactionBase(BaseModel):
    file_hash: str
    tr_hash: str


class TransactionCreate(TransactionBase):
    user_id: int  # id of user who created the transaction NOT USED FOR LOGIN
    bc_hash_link: str  # link to block containing hash
    bc_file_link: str  # link to distributed file storage
    decrypt_key_first_last_5: str


class Transaction(TransactionCreate):
    id: int  # transaction id

    class Config:
        orm_mode = True
        from_attributes = True


class UserBase(BaseModel):
    uname: str  # username


class UserCreate(UserBase):
    pass_hash: str


class User(UserCreate):
    id: int  # same as user_id in Transaction class
    transactions: list[Transaction] = []

    class Config:
        orm_mode = True
        from_attributes = True


class UploadResponse(BaseModel):
    file_hash: str
    tx_hash: str
    etherscan_url: str
    timestamp: str
    ipfs_hash: str
    ipfs_link: str

    class Config:
        orm_mode = True
        from_attributes = True


class VerifyResponse(BaseModel):
    file_hash: str
    timestamp: str
    bc_file_link: str

    class Config:
        orm_mode = True
        from_attributes = True
