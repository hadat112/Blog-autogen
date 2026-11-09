import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.db import models


@pytest.fixture
def recovery_db(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'recovery.db'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(models.ContentDraft(id='draft', kind='article_v1', state='generating'))
        db.add(models.Job(id='first', draft_id='draft', workflow_type='article_v1', status='running'))
        db.commit()
    yield factory
    engine.dispose()


def test_checkpoints_survive_new_attempt_and_reject_stale_worker(recovery_db):
    from app.services.workflow_recovery_service import WorkflowRecoveryService
    with recovery_db() as db:
        first = WorkflowRecoveryService(db, 'draft', 'first')
        first.claim({'language': 'Italian'})
        first.save('source', {'title': 'Title', 'content': 'Original'})
        first.save('chunk:0', 'Tradotto')
        db.query(models.Job).filter_by(id='first').update({'status': 'failed'})
        db.add(models.Job(id='second', draft_id='draft', workflow_type='article_v1', status='running'))
        db.commit()
        second = WorkflowRecoveryService(db, 'draft', 'second')
        second.claim({'language': 'Italian'})
        assert second.get('source')['content'] == 'Original'
        assert second.get('chunk:0') == 'Tradotto'
        with pytest.raises(InterruptedError):
            first.save('chunk:0', 'CORRUPTED')
        assert second.get('chunk:0') == 'Tradotto'


def test_recovery_rejects_overlapping_attempts(recovery_db):
    from app.services.workflow_recovery_service import WorkflowRecoveryService
    with recovery_db() as db:
        first = WorkflowRecoveryService(db, 'draft', 'first')
        first.claim({'language': 'Italian'})
        db.add(models.Job(id='second', draft_id='draft', workflow_type='article_v1', status='queued'))
        db.commit()
        with pytest.raises(ValueError, match='active'):
            WorkflowRecoveryService(db, 'draft', 'second').claim({'language': 'Italian'})


def test_parallel_artifacts_do_not_overwrite_other_completed_chunks(recovery_db):
    from app.services.workflow_recovery_service import WorkflowRecoveryService
    from concurrent.futures import ThreadPoolExecutor
    with recovery_db() as db:
        recovery = WorkflowRecoveryService(db, 'draft', 'first')
        recovery.claim({'language': 'Italian'})
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i: recovery.save('chunk:' + str(i), 'part-' + str(i)), range(12)))
        assert [recovery.get('chunk:' + str(i)) for i in range(12)] == ['part-' + str(i) for i in range(12)]


@pytest.mark.parametrize("fail_stage", ["fetch", "translation", "wordpress", "unknown", "account_changed", "model_changed"])
def test_publish_retry_keeps_source_and_translation(recovery_db, monkeypatch, fail_stage):
    from app.services.article_workflow_service import ArticleWorkflowService
    import app.services.article_workflow_service as module
    from app.integrations.wordpress.source import SourceArticle
    from types import SimpleNamespace
    calls = {'fetch': 0, 'translate': 0, 'publish': 0}
    with recovery_db() as db:
        db.add_all([models.Account(id='ai', name='AI', type='ai', config={'text_model':'test','translation_chunk_size':12000}), models.Account(id='wp', name='WP', type='wp', config={}), models.Pipeline(id='pipe', name='Pipe', type='crawl', language='Italian', step_accounts={'ai':'ai','wp':'wp'})])
        db.get(models.ContentDraft, 'draft').pipeline_id = 'pipe'
        db.get(models.ContentDraft, 'draft').source_url = 'https://source.test/story'
        db.commit()
    class Source:
        def fetch(self, url):
            calls['fetch'] += 1
            if fail_stage == 'fetch' and calls['fetch'] == 1:
                raise RuntimeError('Source unavailable')
            return SourceArticle('Original', 'Original story', '', url)
    class AI:
        translation_chunk_size = 50000
        def translate_article_fields(self, **kwargs):
            calls['translate'] += 1
            if fail_stage in {'translation', 'account_changed', 'model_changed'} and calls['translate'] == 1:
                raise RuntimeError('Translation unavailable')
            return {'title':'Titolo', 'content':'Storia tradotta', 'caption':''}
    class Publisher:
        def __init__(self, db):
            self.db = db
        def publish(self, draft_id, **kwargs):
            calls['publish'] += 1
            if fail_stage == 'unknown':
                self.db.get(models.ContentDraft, draft_id).state = 'publish_unknown'
                self.db.commit()
                raise RuntimeError('WP result uncertain')
            if fail_stage == 'wordpress' and calls['publish'] == 1:
                raise RuntimeError('WP unavailable')
            return SimpleNamespace(wp_post_id='77',wp_url='https://wp.test/77',wp_status='publish',error=None)
    monkeypatch.setattr(module, 'SessionLocal', recovery_db)
    monkeypatch.setattr(module, 'create_ai_client', lambda account: AI())
    monkeypatch.setattr(module, 'WordPressPublishingService', Publisher)
    monkeypatch.setattr(module, 'SettingsManager', lambda: SimpleNamespace(config={'auto_collect_patterns':False}))
    ArticleWorkflowService.execute('first','draft',mode='v1',source_gateway=Source())
    with recovery_db() as db:
        assert db.get(models.Job,'first').status == 'failed'
        assert db.get(models.WorkflowRecovery,'draft').manifest['chunk_size'] == 12000
        db.get(models.Account,'ai').config = {**db.get(models.Account,'ai').config, 'translation_chunk_size':1000}
        if fail_stage in {'wordpress', 'unknown'}:
            assert db.get(models.ContentDraft,'draft').content == 'Storia tradotta'
        if fail_stage in {'account_changed', 'model_changed'}:
            db.add(models.Account(id='other-ai',type='ai',name='Other',config={'text_model':'test' if fail_stage == 'model_changed' else 'other'}))
            db.get(models.Pipeline,'pipe').step_accounts = {'ai':'other-ai','wp':'wp'}
            if fail_stage == 'model_changed':
                db.get(models.Account,'ai').config = {'text_model':'changed'}
        db.add(models.Job(id='second', draft_id='draft', status='queued', workflow_type='article_v1'))
        db.commit()
    ArticleWorkflowService.execute('second','draft',mode='v1',source_gateway=Source())
    assert calls == {'fetch':2 if fail_stage == 'fetch' else 1, 'translate':2 if fail_stage in {'translation','account_changed'} else 1, 'publish':0 if fail_stage == 'model_changed' else 2 if fail_stage == 'wordpress' else 1}
    with recovery_db() as db:
        assert db.get(models.WorkflowRecovery,'draft').manifest['chunk_size'] == 12000
        assert db.get(models.Job,'second').status == ('failed' if fail_stage in {'unknown','model_changed'} else 'success')
        if fail_stage == 'unknown':
            assert db.get(models.ContentDraft,'draft').state == 'publish_unknown'


def test_progress_cannot_resurrect_a_cancelled_job(recovery_db):
    from app.services.workflow_job_service import WorkflowJobService
    with recovery_db() as stale:
        job = stale.get(models.Job, 'first')
        assert job.status == 'running'
        with recovery_db() as other:
            other.query(models.Job).filter_by(id='first').update({'status':'cancelled'})
            other.commit()
        service = WorkflowJobService(stale)
        service.progress('first', 'publish_facebook', 96)
        service.complete('first')
    with recovery_db() as db:
        assert db.get(models.Job,'first').status == 'cancelled'


def test_account_limit_edit_updates_existing_request_admission(recovery_db):
    from app.services.account_service import AccountService
    from app.services.ai_client_factory import create_ai_client
    from types import SimpleNamespace
    with recovery_db() as db:
        account = models.Account(id='edited-account',type='ai',name='AI',config={'base_url':'https://edit-quota.test/v1','api_key':'unique-edit-key','max_concurrency':4})
        db.add(account);db.commit()
        client = create_ai_client(account)
        assert client.scheduler.capacity(client.account_key) == 4
        AccountService(db).update_account(account.id, SimpleNamespace(name='AI',type='ai',config={'base_url':'https://edit-quota.test/v1','api_key':'unique-edit-key','max_concurrency':1}))
        assert client.scheduler.capacity(client.account_key) == 1


def test_confirmed_secondary_receipt_survives_cancel_without_reviving_job(recovery_db):
    from app.services.workflow_recovery_service import WorkflowRecoveryService
    with recovery_db() as db:
        recovery = WorkflowRecoveryService(db,'draft','first')
        recovery.claim({'language':'Italian'})
        recovery.save('facebook_pending',True)
        db.query(models.Job).filter_by(id='first').update({'status':'cancelled'})
        db.commit()
        recovery.save_receipt('facebook','confirmed-fb-id')
        assert recovery.get('facebook') == 'confirmed-fb-id'
        assert recovery.get('facebook_pending') is False
        with pytest.raises(InterruptedError):
            recovery.save('assembled', {'content':'stale'})
        db.expire_all()
        assert db.get(models.Job,'first').status == 'cancelled'


def test_retry_waiting_for_secondary_delivery_reuses_receipt(recovery_db, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    import app.services.article_workflow_service as module
    from app.integrations.wordpress.source import SourceArticle
    started, release, waiting = threading.Event(), threading.Event(), threading.Event()
    calls = []
    class DeliveryLock:
        def __init__(self): self.lock = threading.Lock()
        def __enter__(self):
            if self.lock.locked(): waiting.set()
            self.lock.acquire()
        def __exit__(self, *args): self.lock.release()
    class Source:
        def fetch(self, url): return SourceArticle('Title','Original','','https://source.test/story')
    class AI:
        def translate_article_fields(self, **kwargs): return {'title':'Titolo','content':'Tradotto','caption':''}
    class Publisher:
        def __init__(self, db): pass
        def publish(self, *args, **kwargs): return SimpleNamespace(wp_post_id='1',wp_url='https://wp.test/1',wp_status='publish',error=None)
    class Facebook:
        def __init__(self, **kwargs): pass
        def publish_text(self, text):
            calls.append(text)
            started.set()
            assert release.wait(timeout=3)
            return 'confirmed-facebook'
    with recovery_db() as db:
        db.add_all([models.Account(id='ai',name='AI',type='ai',config={'text_model':'m'}),models.Account(id='wp',name='WP',type='wp',config={}),models.Account(id='fb',name='FB',type='fb',config={'page_id':'page','access_token':'fake'}),models.Pipeline(id='pipe',name='Pipe',type='crawl',language='Italian',step_accounts={'ai':'ai','wp':'wp','fb':'fb'})])
        db.get(models.ContentDraft,'draft').pipeline_id='pipe'
        db.get(models.ContentDraft,'draft').source_url='https://source.test/story'
        db.commit()
    monkeypatch.setattr(module,'SessionLocal',recovery_db)
    monkeypatch.setattr(module,'SettingsManager',lambda: SimpleNamespace(config={'auto_collect_patterns':False}))
    monkeypatch.setattr(module,'create_ai_client',lambda account: AI())
    monkeypatch.setattr(module,'WordPressPublishingService',Publisher)
    monkeypatch.setattr(module,'FacebookPagePublisher',Facebook)
    monkeypatch.setattr(module,'_draft_locks',{'draft':DeliveryLock()})
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(module.ArticleWorkflowService.execute,'first','draft',mode='v1',source_gateway=Source())
        assert started.wait(timeout=3)
        with recovery_db() as db:
            db.query(models.Job).filter_by(id='first').update({'status':'cancelled'})
            db.add(models.Job(id='second',draft_id='draft',pipeline_id='pipe',workflow_type='article_v1',status='queued'))
            db.commit()
        second = pool.submit(module.ArticleWorkflowService.execute,'second','draft',mode='v1',source_gateway=Source())
        try:
            assert waiting.wait(timeout=3)
        finally:
            release.set()
        first.result(timeout=3)
        second.result(timeout=3)
    assert len(calls) == 1
