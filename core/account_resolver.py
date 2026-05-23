from sqlalchemy.orm import Session
from .models import Account

def resolve_accounts_for_pipeline(db: Session, step_accounts: dict):
    resolved = {}
    for step, acc_id in step_accounts.items():
        if not acc_id:
            continue
        acc = db.query(Account).filter(Account.id == acc_id).first()
        if acc:
            resolved[step] = acc.config
    return resolved
