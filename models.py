from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    tr_hash = Column(String, unique=True, index=True)
    bc_hash_link = Column(String)
    ipfs_cid = Column(String)
    user_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
