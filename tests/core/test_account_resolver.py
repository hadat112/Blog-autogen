import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infrastructure.db.session import Base
from infrastructure.db.models import Account
from core.account_resolver import resolve_accounts_for_pipeline

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_resolve_accounts_for_pipeline(db):
    # Setup: Create some accounts
    wp_acc = Account(name="My WP", type="wp", config={"url": "https://wp.com", "user": "admin"})
    ai_acc = Account(name="My AI", type="ai", config={"api_key": "secret"})
    db.add(wp_acc)
    db.add(ai_acc)
    db.commit()
    db.refresh(wp_acc)
    db.refresh(ai_acc)

    # Resolve accounts
    step_accounts = {
        "wp": wp_acc.id,
        "ai": ai_acc.id,
        "fb": None # Should be ignored
    }
    
    resolved = resolve_accounts_for_pipeline(db, step_accounts)
    
    assert len(resolved) == 2
    assert resolved["wp"] == {"url": "https://wp.com", "user": "admin"}
    assert resolved["ai"] == {"api_key": "secret"}
    assert "fb" not in resolved

def test_resolve_accounts_with_missing_account(db):
    # Resolve accounts with a non-existent ID
    step_accounts = {
        "wp": "non-existent-uuid"
    }
    
    resolved = resolve_accounts_for_pipeline(db, step_accounts)
    
    assert len(resolved) == 0
