from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.services.article_workflow_intake import create_manual_article_attempt


@pytest.fixture
def manual_run(tmp_path, monkeypatch):
    import app.services.article_workflow_service as module
    from app.services.article_workflow_service import ArticleWorkflowService
    monkeypatch.chdir(tmp_path)
    engine = create_engine(f'sqlite:///{tmp_path / "workflow.db"}', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add_all([
            models.Account(id='ai', name='AI', type='ai', config={'text_model': 'test', 'translation_chunk_size': 12000}),
            models.Account(id='wp', name='WP', type='wp', config={}),
            models.Account(id='fb', name='FB', type='fb', config={'page_id': 'page', 'access_token': 'fake'}),
            models.Account(id='tg', name='TG', type='tg', config={'bot_token': 'fake', 'chat_id': 'chat'}),
            models.Pipeline(id='pipe', name='Pipe', type='crawl', language='Italian',
                            step_accounts={'ai': 'ai', 'wp': 'wp', 'fb': 'fb', 'tg': 'tg'}),
        ])
        db.commit()
    calls = dict.fromkeys(['fetch', 'collect', 'enrich', 'v1', 'v2', 'wordpress', 'facebook', 'facebook_file', 'telegram'], 0)
    inputs = {}
    state = {'fail_wp': False, 'fail_fb': False, 'fail_tg': False}
    def forbidden(name):
        def call(*a, **kw):
            calls[name] += 1
            raise AssertionError(f'{name} must not run for manual input')
        return call
    class AI:
        def translate_article_fields(self, **kw):
            calls['v1'] += 1
            inputs.update(kw)
            assert self.translation_chunk_size == 12000
            return {'title': 'Titolo', 'content': 'Storia tradotta.', 'caption': 'Storia tradotta.'}
    class Rewrite:
        def __init__(self, ai, chunk_size): assert chunk_size == 12000
        def rewrite(self, title, content, language, progress):
            calls['v2'] += 1
            inputs.update(title=title, content=content, language=language)
            return {'title': 'Titolo', 'content': 'Storia tradotta.', 'caption': 'Storia tradotta.'}
    class Publisher:
        def __init__(self, db): self.db = db
        def publish(self, draft_id, **kw):
            calls['wordpress'] += 1
            kw['guard']()
            if state['fail_wp']:
                state['fail_wp'] = False
                raise RuntimeError('WP unavailable')
            draft = self.db.get(models.ContentDraft, draft_id)
            draft.wp_post_id, draft.wp_url, draft.state = '77', 'https://wp.test/77', 'wordpress_created'
            self.db.commit()
            return draft
    class Facebook:
        def __init__(self, **kw): pass
        def publish_photo_file(self, caption, path):
            calls['facebook_file'] += 1
            assert Path(path).read_bytes() == b'\xff\xd8\xffimage'
            return self.publish_text(caption)
        def publish_photo_caption(self, caption, url):
            assert url == 'https://image.test/a.jpg'
            return self.publish_text(caption)
        def publish_text(self, caption):
            calls['facebook'] += 1
            if state['fail_fb']:
                state['fail_fb'] = False
                import requests
                response = requests.Response()
                response.status_code = 429
                raise requests.HTTPError(response=response)
            return 'fb-1'
    def telegram(*args):
        calls['telegram'] += 1
        if state['fail_tg']:
            state['fail_tg'] = False
            import requests
            response = requests.Response()
            response.status_code = 429
            raise requests.HTTPError(response=response)
    monkeypatch.setattr(module, 'SessionLocal', factory)
    monkeypatch.setattr(module, 'create_ai_client', lambda account: AI())
    monkeypatch.setattr(module, 'RewriteEngine', Rewrite)
    monkeypatch.setattr(module.WordPressSourceGateway, 'fetch', forbidden('fetch'))
    monkeypatch.setattr(module, 'normalize_source_url', forbidden('fetch'))
    monkeypatch.setattr(module.PatternCollectionService, 'collect', forbidden('collect'))
    monkeypatch.setattr(module.ArticleEnrichmentService, 'enqueue', forbidden('enrich'))
    monkeypatch.setattr(module, 'WordPressPublishingService', Publisher)
    monkeypatch.setattr(module, 'FacebookPagePublisher', Facebook)
    monkeypatch.setattr(module, 'send_telegram_msg', telegram)
    monkeypatch.setattr(module, 'SettingsManager', lambda: SimpleNamespace(config={'auto_collect_patterns': True}))
    def create(mode='v1', image_kind=None):
        path = tmp_path / 'input.jpg'
        path.write_bytes(b'\xff\xd8\xffimage')
        with factory() as db:
            job, draft = create_manual_article_attempt(db, pipeline_id='pipe', mode=mode,
                title='Source title', content='First paragraph.\n\nSecond paragraph.', image_kind=image_kind,
                image_source=str(path) if image_kind == 'upload' else 'https://image.test/a.jpg' if image_kind == 'url' else None)
            job_id, draft_id = job.id, draft.id
        return SimpleNamespace(factory=factory, job_id=job_id, draft_id=draft_id, calls=calls, inputs=inputs, state=state,
                               execute=lambda: ArticleWorkflowService.execute(job_id, draft_id, mode=mode))
    yield create
    engine.dispose()


@pytest.mark.parametrize('mode', ['v1', 'v2'])
@pytest.mark.parametrize('image_kind', [None, 'url', 'upload'])
def test_manual_input_uses_shared_processing(manual_run, mode, image_kind):
    run = manual_run(mode, image_kind)
    run.execute()
    with run.factory() as db:
        job = db.get(models.Job, run.job_id)
        assert job.status == 'success', job.logs
    assert run.calls['fetch'] == run.calls['collect'] == run.calls['enrich'] == 0
    assert run.calls['v1'] == (1 if mode == 'v1' else 0)
    assert run.calls['v2'] == (1 if mode == 'v2' else 0)
    assert run.inputs['title'] == 'Source title'
    assert run.inputs['content'] == 'First paragraph.\n\nSecond paragraph.'
    assert run.inputs['language'] == 'Italian'
    assert run.calls['wordpress'] == run.calls['facebook'] == run.calls['telegram'] == 1
    assert run.calls['facebook_file'] == (1 if image_kind == 'upload' else 0)


def test_missing_manual_source_fails_without_fetch(manual_run):
    run = manual_run()
    with run.factory() as db:
        db.get(models.WorkflowRecovery, run.draft_id).artifacts = {}
        db.commit()
    run.execute()
    with run.factory() as db:
        job = db.get(models.Job, run.job_id)
        assert job.status == 'failed'
        assert 'manual source' in job.logs[-1]['detail'].lower()
    assert run.calls['fetch'] == run.calls['v1'] == run.calls['wordpress'] == 0


@pytest.mark.parametrize('failed_channel', ['wp', 'fb', 'tg'])
def test_manual_retry_after_restart_skips_completed_stages(manual_run, failed_channel):
    from app.services.article_workflow_intake import create_article_retry
    from app.services.article_workflow_service import ArticleWorkflowService
    run = manual_run(image_kind='upload')
    run.state['fail_' + failed_channel] = True
    run.execute()
    with run.factory() as db:
        old = db.get(models.Job, run.job_id)
        assert old.status == 'failed', old.logs
        recovery = db.get(models.WorkflowRecovery, run.draft_id)
        source = dict(recovery.artifacts['source'])
        job = create_article_retry(db, old, db.get(models.ContentDraft, run.draft_id), mode='v1')
        new_id = job.id
    # A fresh executor/session has no in-memory source or translation from attempt one.
    ArticleWorkflowService.execute(new_id, run.draft_id, mode='v1')
    with run.factory() as db:
        job = db.get(models.Job, new_id)
        assert job.status == 'success', job.logs
        assert db.get(models.WorkflowRecovery, run.draft_id).artifacts['source'] == source
    assert run.calls['v1'] == 1
    assert run.calls['wordpress'] == (2 if failed_channel == 'wp' else 1)
    assert run.calls['facebook'] == (2 if failed_channel == 'fb' else 1)
    assert run.calls['telegram'] == (2 if failed_channel == 'tg' else 1)


def test_url_and_manual_workflows_share_real_account_quota(manual_run, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import app.services.article_workflow_service as module
    import app.integrations.ai.openai_compatible as ai_module
    from app.services.ai_client_factory import create_ai_client
    from app.services.article_service import normalize_source_url
    from app.integrations.wordpress.source import SourceArticle
    run = manual_run()
    with run.factory() as db:
        account = db.get(models.Account, 'ai')
        account.config = {**account.config, 'api_key': 'mixed-source-unique',
                          'base_url': 'https://mixed-source.test/v1', 'max_concurrency': 1}
        db.add(models.ContentDraft(id='url-draft', kind='article_v1', pipeline_id='pipe',
                                   source_url='https://source.test/story', state='generating', wp_status='publish'))
        db.add(models.Job(id='url-job', draft_id='url-draft', pipeline_id='pipe', workflow_type='article_v1', status='queued'))
        db.commit()
    lock = threading.Lock()
    entered, both_clients, release, second_http = [threading.Event() for _ in range(4)]
    state = {'clients': 0, 'requests': 0, 'active': 0, 'peak': 0}
    def real_client(account):
        client = create_ai_client(account, settings={'translation_chunk_size': 12000})
        with lock:
            state['clients'] += 1
            if state['clients'] == 2: both_clients.set()
        return client
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {'choices': [{'message': {'content': 'Tradotto.'}, 'finish_reason': 'stop'}]}
    def post(*a, **kw):
        with lock:
            state['requests'] += 1
            state['active'] += 1
            state['peak'] = max(state['peak'], state['active'])
            first = state['requests'] == 1
            if not first: second_http.set()
        try:
            entered.set()
            if first: assert release.wait(timeout=5)
            return Response()
        finally:
            with lock: state['active'] -= 1
    class Source:
        def fetch(self, url): return SourceArticle('URL title', 'URL body.', '', url)
    monkeypatch.setattr(module, 'create_ai_client', real_client)
    monkeypatch.setattr(module, 'normalize_source_url', normalize_source_url)
    monkeypatch.setattr(module, 'SettingsManager', lambda: SimpleNamespace(config={'auto_collect_patterns': False}))
    monkeypatch.setattr(ai_module.requests, 'post', post)
    with ThreadPoolExecutor(max_workers=2) as pool:
        manual = pool.submit(run.execute)
        url = pool.submit(module.ArticleWorkflowService.execute, 'url-job', 'url-draft', mode='v1', source_gateway=Source())
        try:
            assert entered.wait(timeout=5)
            assert both_clients.wait(timeout=5)
            assert not second_http.wait(timeout=.1)
        finally: release.set()
        manual.result(timeout=5)
        url.result(timeout=5)
    assert state['peak'] == 1
    with run.factory() as db:
        for job_id in (run.job_id, 'url-job'):
            job = db.get(models.Job, job_id)
            assert job.status == 'success', job.logs


def test_real_wordpress_publisher_retains_image_until_facebook_retry_finishes(manual_run, tmp_path, monkeypatch):
    import app.services.article_workflow_service as module
    from app.services.wordpress_publishing_service import WordPressPublishingService
    from app.services.article_workflow_intake import create_article_retry
    run = manual_run(image_kind='upload')
    image = tmp_path / 'var/uploads/input.jpg'
    image.parent.mkdir(parents=True)
    image.write_bytes(b'\xff\xd8\xffimage')
    with run.factory() as db:
        draft = db.get(models.ContentDraft, run.draft_id)
        draft.image_source = str(image)
        recovery = db.get(models.WorkflowRecovery, run.draft_id)
        source = {**recovery.artifacts['source'], 'image_source': str(image)}
        recovery.artifacts = {**recovery.artifacts, 'source': source}
        db.commit()
    posts = []
    class Gateway:
        def __init__(self, config): pass
        def upload_file(self, path):
            assert Path(path).is_file()
            return 'media-1'
        def create_post(self, *a, **kw):
            posts.append(kw)
            return {'id': '77', 'link': 'https://wp.test/77', 'status': 'publish'}
    monkeypatch.setattr(module, 'WordPressPublishingService', lambda db: WordPressPublishingService(db, Gateway))
    run.state['fail_fb'] = True
    run.execute()
    assert image.is_file(), 'WordPress must retain the upload for remaining channels and retries'
    with run.factory() as db:
        old = db.get(models.Job, run.job_id)
        assert old.status == 'failed'
        assert db.get(models.WorkflowRecovery, run.draft_id).artifacts.get('facebook_pending') is False
        job = create_article_retry(db, old, db.get(models.ContentDraft, run.draft_id), mode='v1')
        new_id = job.id
    module.ArticleWorkflowService.execute(new_id, run.draft_id, mode='v1')
    with run.factory() as db:
        job = db.get(models.Job, new_id)
        assert job.status == 'success', job.logs
    assert len(posts) == 1
    assert run.calls['v1'] == 1
    assert run.calls['facebook_file'] == 2
    assert not image.exists(), 'Finished workflows clean the temporary upload'


def test_manual_unknown_wordpress_requires_resolution_before_retry(manual_run, monkeypatch):
    import app.services.article_workflow_service as module
    from app.integrations.wordpress.destination import AmbiguousWordPressResult
    from app.services.wordpress_publishing_service import WordPressPublishingService
    from app.services.article_workflow_intake import create_article_retry
    from app.services.delivery_recovery_service import resolve_delivery
    run = manual_run()
    posts = []
    class Gateway:
        def __init__(self, config): pass
        def create_post(self, *a, **kw):
            posts.append(kw)
            if len(posts) == 1: raise AmbiguousWordPressResult('Unknown response')
            return {'id': '77', 'link': 'https://wp.test/77', 'status': 'publish'}
    monkeypatch.setattr(module, 'WordPressPublishingService', lambda db: WordPressPublishingService(db, Gateway))
    run.execute()
    with run.factory() as db:
        draft = db.get(models.ContentDraft, run.draft_id)
        assert draft.state == 'publish_unknown'
        second = create_article_retry(db, db.get(models.Job, run.job_id), draft, mode='v1').id
    module.ArticleWorkflowService.execute(second, run.draft_id, mode='v1')
    assert len(posts) == 1
    with run.factory() as db:
        assert db.get(models.Job, second).status == 'failed'
        resolve_delivery(db, run.draft_id, 'wordpress', 'not_sent', confirmed=True)
        third = create_article_retry(db, db.get(models.Job, second), db.get(models.ContentDraft, run.draft_id), mode='v1').id
    module.ArticleWorkflowService.execute(third, run.draft_id, mode='v1')
    with run.factory() as db:
        job = db.get(models.Job, third)
        assert job.status == 'success', job.logs
    assert len(posts) == 2
    assert run.calls['v1'] == 1
