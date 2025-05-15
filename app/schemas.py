from pydantic import BaseModel
from datetime import datetime

class TransactionBase(BaseModel):
    date: datetime
    amount: float
    description: str

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: str
    investec_account_id: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    transactions: list[Transaction] = []

    class Config:
        from_attributes = True