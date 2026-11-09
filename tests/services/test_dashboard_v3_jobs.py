import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import models
from app.db.session import Base
from app.services.job_service import JobService


@pytest.fixture
def jobs_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        for name, workflow, source, status in [
            ('manual-v1', 'article_v1', 'manual', 'queued'),
            ('manual-v2', 'article_v2', 'manual', 'success'),
            ('url-v1', 'article_v1', 'url', 'success'),
            ('url-v2', 'article_v2', 'url', 'running'),
        ]:
            db.add(models.ContentDraft(id=name, kind=workflow))
            db.add(models.Job(id=name, draft_id=name, workflow_type=workflow, status=status))
            db.add(models.WorkflowRecovery(draft_id=name, active_job_id=name,
                                          manifest={'source_kind': source}, artifacts={}))
        db.add(models.Job(id='old', workflow_type='legacy', status='success'))
        db.commit()
        yield db
    engine.dispose()


@pytest.mark.parametrize('workflow,expected', [
    ('article_v3', {'manual-v1', 'manual-v2'}),
    ('legacy', {'old', 'url-v1'}),
    ('rewrite', {'url-v2'}),
])
def test_dashboard_filters_manual_jobs_as_v3(jobs_db, workflow, expected):
    result = JobService(jobs_db).list_jobs(workflow_type=workflow)
    assert {job.id for job in result['items']} == expected
    assert result['total'] == len(expected)


def test_dashboard_v3_uses_shared_active_and_history(jobs_db):
    service = JobService(jobs_db)
    active = service.list_jobs(workflow_type='article_v3', status_group='active')
    recent = service.list_jobs(workflow_type='article_v3', status_group='history')
    assert [job.id for job in active['items']] == ['manual-v1']
    assert [job.id for job in recent['items']] == ['manual-v2']
    assert service.get_job('manual-v2').outputs['source_kind'] == 'manual'
    assert service.get_job('url-v1').outputs['source_kind'] == 'url'
