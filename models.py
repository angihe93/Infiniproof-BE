from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    file_name = Column(String, unique=True, index=True)
    file_hash = Column(String)
    tr_hash = Column(String, unique=True, index=True)
    bc_hash_link = Column(String, unique=True)
    bc_file_link = Column(String, unique=True)
    decrypt_key_first_last_5 = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="transactions")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    uname = Column(String, unique=True, index=True)
    pass_hash = Column(String)

    transactions = relationship("Transaction", back_populates="user")
