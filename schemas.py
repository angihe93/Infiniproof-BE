from pydantic import BaseModel


class TransactionBase(BaseModel):
    tr_hash: str


class TransactionCreate(TransactionBase):
    user_id: int        #id of user who created the transaction NOT USED FOR LOGIN
    bc_hash_link: str   #link to block containing hash
    bc_file_link: str   #link to distributed file storage
    decrypt_key_first_last_5: str


class Transaction(TransactionCreate):
    id: int             #transaction id

    class Config:
        orm_mode = True
        from_attributes = True


class UserBase(BaseModel):
    uname: str      #username


class UserCreate(UserBase):
    pass_hash: str


class User(UserCreate):
    id: int         #same as user_id in Transaction class
    transactions: list[Transaction] = []

    class Config:
        orm_mode = True
        from_attributes = True

