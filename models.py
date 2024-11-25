from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id                          = Column(Integer, primary_key=True)
    user_id                     = Column(Integer, ForeignKey("users.id"), index=True)
    uname                       = Column(String, ForeignKey("users.uname"), index=True)
    tr_hash                     = Column(String, unique=True, index=True)
    bc_hash_link                = Column(String, unique=True, index=True)
    bc_file_link                = Column(String, unique=True, index=True)
    decrypt_key_first_last_5    = Column(String, unique=True, index=True)


class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True)
    uname           = Column(String, unique=True, index=True)
    pass_hash       = (String)
    transactions    = relationship("Transaction", back_populates="user_id") #not sure about this one.