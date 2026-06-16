from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api import schemas
from application.account_service import (
    AccountService,
    fetch_ai_models,
    fetch_wp_categories,
    perform_connection_test,
)
from infrastructure.db.session import get_db


router = APIRouter()


@router.post("/accounts/test")
def test_account(test_data: dict, db: Session = Depends(get_db)):
    service = AccountService(db)
    account_type, config, error = service.resolve_test_payload(test_data)
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Account not found")
    if error == "missing":
        raise HTTPException(status_code=400, detail="Missing account type or configuration")

    success, message = perform_connection_test(account_type, config)
    if not success:
        raise HTTPException(status_code=400, detail=f"Verification failed: {message}")
    return {"status": "ok", "message": message}


@router.get("/accounts", response_model=List[schemas.AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    return AccountService(db).list_accounts()


@router.get("/accounts/{id}", response_model=schemas.AccountResponse)
def get_account(id: str, db: Session = Depends(get_db)):
    account = AccountService(db).get_account(id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/accounts", response_model=schemas.AccountResponse)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    return AccountService(db).create_account(account)


@router.put("/accounts/{id}", response_model=schemas.AccountResponse)
def update_account(id: str, account: schemas.AccountCreate, db: Session = Depends(get_db)):
    updated = AccountService(db).update_account(id, account)
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found")
    return updated


@router.delete("/accounts/{id}")
def delete_account(id: str, db: Session = Depends(get_db)):
    deleted = AccountService(db).delete_account(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "ok"}


@router.post("/accounts/wp-categories")
def get_wp_categories(config: dict):
    try:
        return fetch_wp_categories(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch categories: {str(e)}")


@router.post("/accounts/ai-models")
def get_ai_models(config: dict):
    try:
        return fetch_ai_models(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch AI models: {str(e)}")
