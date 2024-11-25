from pydantic import BaseModel
    
class Transaction(BaseModel):
    id: int             #transaction id
    user_id: int        #id of user who created the transaction NOT USED FOR LOGIN
    uname: str          #username, used for login
    tr_hash: str
    bc_hash_link: str   #link to block containing hash
    bc_file_link: str   #link to distributed file storage
    decrypt_key_first_last_5: str


class User(BaseModel):
    id: int         #same as user_id in Transaction class
    uname: str      #username
    pass_hash: str  #hashed password
    transactions: list[Transaction] = []