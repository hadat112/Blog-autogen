from io import BytesIO
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.db import models
from app.db.session import Base, get_db


@pytest.fixture
def manual_api(tmp_path, monkeypatch):
    from app.api.routes import article_workflows as routes
    monkeypatch.chdir(tmp_path)
    engine = create_engine(f'sqlite:///{tmp_path / "manual.db"}', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add_all([
            models.Account(id='ai', name='AI', type='ai', config={'text_model': 'test', 'translation_chunk_size': 12000}),
            models.Account(id='wp', name='WP', type='wp', config={}),
            models.Pipeline(id='pipe', name='Pipe', language='Italian', type='crawl', step_accounts={'ai': 'ai', 'wp': 'wp'}),
        ])
        db.commit()
    def override():
        with factory() as db: yield db
    app.dependency_overrides[get_db] = override
    start = Mock()
    monkeypatch.setattr(routes.workflow_runner, 'start', start)
    yield TestClient(app), factory, start
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def payload(**changes):
    return {'pipeline_id': 'pipe', 'mode': 'v1', 'title': 'Source title',
            'content': 'First paragraph.\n\nSecond paragraph.', **changes}


@pytest.mark.parametrize('mode', ['v1', 'v2'])
def test_manual_intake_is_durable_before_dispatch(manual_api, mode):
    client, factory, start = manual_api
    def check(job_id, operation):
        with factory() as db:
            job = db.get(models.Job, job_id)
            recovery = db.get(models.WorkflowRecovery, job.draft_id)
            assert recovery.manifest['source_kind'] == 'manual'
            assert recovery.manifest['chunk_size'] == 12000
            assert recovery.artifacts['source']['content'] == payload()['content']
            assert recovery.artifacts['source']['title'] == 'Source title'
            draft = db.get(models.ContentDraft, job.draft_id)
            assert not draft.source_url
            assert draft.wp_status == 'publish'
            assert draft.content == ''
            assert job.workflow_type == f'article_{mode}'
    start.side_effect = check
    response = client.post('/article-workflows/run-text', data=payload(mode=mode))
    assert response.status_code == 200, response.text
    start.assert_called_once()


@pytest.mark.parametrize('newline', ['\n', '\r\n', '\r'])
def test_manual_multipart_keeps_paragraphs_like_url_source(manual_api, newline):
    from app.domain.translation_prompts import build_translation_messages
    from app.integrations.ai.openai_compatible import _split_text_chunks
    import hashlib
    client, factory, start = manual_api
    source = (
        "The first person through the door was a tall man in a sheriff's uniform.\n\n"
        'Behind him came a woman carrying a sleeping toddler.\n\n'
        'Eleven people altogether.'
    )
    fields = payload(content=source.replace('\n', newline))
    # Browser FormData serializes textarea newlines as CRLF. The previous
    # urlencoded API tests did not exercise that boundary.
    response = client.post('/article-workflows/run-text', files={
        key: (None, value) for key, value in fields.items()
    })
    assert response.status_code == 200, response.text
    with factory() as db:
        recovery = db.get(models.WorkflowRecovery, response.json()['draft_id'])
        saved = recovery.artifacts['source']['content']
        assert saved == source
        assert recovery.artifacts['source_hash'] == hashlib.sha256(source.encode()).hexdigest()
        chunks = _split_text_chunks(saved, 50000)
        assert chunks == [source]
        _, prompt = build_translation_messages(chunks[0], 'Italian')
        assert 'Source paragraph count: 3' in prompt
    start.assert_called_once()


@pytest.mark.parametrize('changes', [
    {'title': '   '}, {'content': '\n  '}, {'mode': 'v3'},
    {'pipeline_id': 'missing'}, {'image_url': 'file:///private/image'},
])
def test_manual_invalid_input_does_not_create_job(manual_api, changes):
    client, factory, start = manual_api
    response = client.post('/article-workflows/run-text', data=payload(**changes))
    assert response.status_code in {400, 404, 422}
    start.assert_not_called()
    with factory() as db:
        assert db.query(models.Job).count() == 0
        assert db.query(models.ContentDraft).count() == 0
        assert db.query(models.WorkflowRecovery).count() == 0


@pytest.mark.parametrize('invalid', ['inactive', 'no_ai', 'no_wp', 'wrong_ai', 'wrong_wp'])
def test_manual_invalid_pipeline(manual_api, invalid):
    client, factory, start = manual_api
    with factory() as db:
        pipe = db.get(models.Pipeline, 'pipe')
        if invalid == 'inactive': pipe.is_active = False
        else:
            accounts = dict(pipe.step_accounts)
            role = 'ai' if invalid.endswith('ai') else 'wp'
            accounts[role] = ('wp' if role == 'ai' else 'ai') if invalid.startswith('wrong') else None
            pipe.step_accounts = accounts
        db.commit()
    response = client.post('/article-workflows/run-text', data=payload())
    assert response.status_code in {400, 404}
    start.assert_not_called()


@pytest.mark.parametrize('image_mode', ['url', 'upload', 'both', 'invalid_file'])
def test_manual_image_intake(manual_api, tmp_path, image_mode):
    client, factory, start = manual_api
    data = payload()
    if image_mode in {'url', 'both'}: data['image_url'] = 'https://images.test/a.jpg?x=1&y=2'
    files = None
    if image_mode in {'upload', 'both', 'invalid_file'}:
        files = {'image': ('a.jpg', BytesIO(b'bad' if image_mode == 'invalid_file' else b'\xff\xd8\xffimage'), 'image/jpeg')}
    response = client.post('/article-workflows/run-text', data=data, files=files)
    if image_mode in {'both', 'invalid_file'}:
        assert response.status_code in {400, 422}
        start.assert_not_called()
        assert list(tmp_path.rglob('*.jpg')) == []
        return
    assert response.status_code == 200, response.text
    with factory() as db:
        draft = db.get(models.ContentDraft, response.json()['draft_id'])
        assert draft.image_kind == image_mode
        if image_mode == 'url': assert draft.image_source == data['image_url']
        else:
            from pathlib import Path
            assert Path(draft.image_source).read_bytes() == b'\xff\xd8\xffimage'


def test_dispatch_failure_retains_retryable_source(manual_api):
    client, factory, start = manual_api
    start.side_effect = RuntimeError('dispatch unavailable')
    response = client.post('/article-workflows/run-text', data=payload())
    assert response.status_code == 503
    with factory() as db:
        job = db.query(models.Job).one()
        assert job.status == 'failed'
        assert db.get(models.WorkflowRecovery, job.draft_id).artifacts['source']['content'] == payload()['content']


@pytest.mark.parametrize('status', ['failed', 'cancelled'])
def test_manual_retry_reuses_snapshot_without_input_url(manual_api, status):
    client, factory, start = manual_api
    response = client.post('/article-workflows/run-text', data=payload())
    assert response.status_code == 200
    old = response.json()
    with factory() as db:
        job = db.get(models.Job, old['job_id'])
        job.status, job.input_text = status, None
        db.commit()
    response = client.post(f'/article-workflows/{old["job_id"]}/retry')
    assert response.status_code == 200, response.text
    new = response.json()
    assert old['draft_id'] == new['draft_id']
    assert old['job_id'] != new['job_id']
    with factory() as db:
        assert db.query(models.ContentDraft).count() == 1
        assert db.get(models.WorkflowRecovery, old['draft_id']).artifacts['source']['content'] == payload()['content']
    repeated = client.post(f'/article-workflows/{old["job_id"]}/retry')
    assert repeated.status_code in {400, 409}
    with factory() as db: assert db.query(models.Job).count() == 2


def test_intake_rollback_cleans_uploaded_file(manual_api, tmp_path, monkeypatch):
    client, factory, start = manual_api
    with factory() as db:
        db.get(models.Pipeline, 'pipe').is_active = False
        db.commit()
    # Validation happens after a new upload has been written; it must be removed.
    response = client.post('/article-workflows/run-text', data=payload(),
                           files={'image': ('a.jpg', b'\xff\xd8\xffimage', 'image/jpeg')})
    assert response.status_code == 404
    assert list(tmp_path.rglob('*.jpg')) == []
    start.assert_not_called()


def test_intake_transaction_failure_removes_all_partial_data(manual_api, tmp_path, monkeypatch):
    import app.services.article_workflow_intake as intake
    client, factory, start = manual_api
    def fail(*a, **kw): raise RuntimeError('injected failure after draft and job flush')
    monkeypatch.setattr(intake, 'build_article_manifest', fail)
    with pytest.raises(RuntimeError, match='injected'):
        client.post('/article-workflows/run-text', data=payload(),
                    files={'image': ('a.jpg', b'\xff\xd8\xffimage', 'image/jpeg')})
    assert list(tmp_path.rglob('*.jpg')) == []
    with factory() as db:
        assert db.query(models.Job).count() == db.query(models.ContentDraft).count() == 0
    start.assert_not_called()


def test_manual_retry_rejects_another_active_attempt(manual_api):
    client, factory, start = manual_api
    old = client.post('/article-workflows/run-text', data=payload()).json()
    with factory() as db:
        db.get(models.Job, old['job_id']).status = 'failed'
        db.add(models.Job(id='other', draft_id=old['draft_id'], workflow_type='article_v1', status='running'))
        db.commit()
    response = client.post(f'/article-workflows/{old["job_id"]}/retry')
    assert response.status_code == 409
    with factory() as db:
        assert db.query(models.Job).count() == 2
        assert db.get(models.Job, old['job_id']).rerun_job_id is None
