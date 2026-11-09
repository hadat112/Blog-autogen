from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.services.ai_client_factory import create_ai_client
from app.services.account_service import AccountService


@pytest.mark.parametrize('override,expected', [(12000,12000),(50000,50000),(None,9000),('',9000)])
def test_account_character_limit_overrides_or_inherits_global_setting(override, expected):
    account=SimpleNamespace(id='chunk-account',config={'translation_chunk_size':override})
    client=create_ai_client(account,settings={'translation_chunk_size':9000})
    assert client.translation_chunk_size == expected


@pytest.mark.parametrize('value',[999,50001,'invalid',1200.5])
def test_account_rejects_invalid_character_limits(value):
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        with pytest.raises(ValueError,match='1,000.*50,000'):
            AccountService(db).create_account(SimpleNamespace(name='AI',type='ai',config={'translation_chunk_size':value}))
    engine.dispose()


def test_clearing_account_override_restores_inheritance():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        service=AccountService(db)
        account=service.create_account(SimpleNamespace(name='AI',type='ai',config={'translation_chunk_size':12000}))
        updated=service.update_account(account.id,SimpleNamespace(name='AI',type='ai',config={**account.config,'translation_chunk_size':''}))
        assert 'translation_chunk_size' not in updated.config
        assert create_ai_client(updated,settings={'translation_chunk_size':7000}).translation_chunk_size == 7000
    engine.dispose()
