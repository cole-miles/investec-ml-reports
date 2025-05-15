from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .database import SessionLocal, engine
from .investec_api import get_access_token, get_account_id, get_transactions
from datetime import datetime
from .ml import forecast_spending

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API endpoint to fetch and save transactions
@app.post("/users/{user_id}/transactions/")
async def fetch_and_save_transactions(user_id: int, db: Session = Depends(get_db)):
    # Get user
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch transactions from Investec API
    access_token = get_access_token()
    account_id = get_account_id(access_token)
    transactions = get_transactions(account_id, access_token)

    # Process and save transactions
    for transaction_data in transactions:
        transaction = schemas.TransactionCreate(
            date=datetime.strptime(transaction_data["transactionDate"], "%Y-%m-%d"),
            amount=float(transaction_data["amount"]),
            description=transaction_data["description"]
        )
        crud.create_transaction(db=db, transaction=transaction, user_id=user_id)

    return {"message": "Transactions fetched and saved successfully"}

# API endpoint to run the report
@app.get("/users/{user_id}/report")
async def generate_report(user_id: int, db: Session = Depends(get_db)):
    # Get user
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all transactions for the user
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).order_by(models.Transaction.date.asc()).all()

    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions found for user")

    # Convert transactions to a list of dictionaries
    transactions_list = [
        {
            "date": transaction.date,
            "amount": transaction.amount,
            "description": transaction.description
        }
        for transaction in transactions
    ]

    try:
        # Run ML forecasting
        forecast_result = forecast_spending(transactions_list)

        return {
            "next_month_forecast": {
                "amount": round(forecast_result['predicted_spending'], 2),
                "confidence_interval": {
                    "lower": round(forecast_result['confidence_interval']['lower'], 2),
                    "upper": round(forecast_result['confidence_interval']['upper'], 2)
                }
            },
            "trend": {
                "percentage": round(forecast_result['trend_percentage'], 1),
                "direction": "up" if forecast_result['trend_percentage'] > 0 else "down"
            },
            "historical": {
                "average_monthly": round(forecast_result['average_monthly_spending'], 2)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating forecast: {str(e)}")

# Example endpoint to create a user
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

# Example endpoint to get a user
@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Example endpoint to get transactions
@app.get("/transactions/", response_model=list[schemas.Transaction])
def read_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    transactions = crud.get_transactions(db, skip=skip, limit=limit)
    return transactions

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Delete all transactions for this user
    db.query(models.Transaction).filter(models.Transaction.user_id == user_id).delete()
    # Delete the user
    db.delete(user)
    db.commit()
    return {"message": f"User {user_id} and all their transactions have been deleted."}