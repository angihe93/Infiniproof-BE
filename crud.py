from sqlalchemy.orm import Session
import models
import schemas


def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    db_transaction = models.Transaction(
        user_id=transaction.user_id,
        file_name=transaction.file_name,
        file_hash=transaction.file_hash,
        tr_hash=transaction.tr_hash,
        bc_hash_link=transaction.bc_hash_link,
        bc_file_link=transaction.bc_file_link,
        decrypt_key_first_last_5=transaction.decrypt_key_first_last_5
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def get_transaction(db: Session, tr_hash: str):
    return db.query(models.Transaction).filter(
        models.Transaction.tr_hash == tr_hash).first()


def get_user_transactions(db: Session, user_id: int):
    return db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id).all()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        uname=user.uname,
        pass_hash=user.pass_hash
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, uname: str):
    return db.query(models.User).filter(models.User.uname == uname).first()
