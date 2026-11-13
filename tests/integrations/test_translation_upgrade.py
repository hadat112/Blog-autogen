import pytest
from app.integrations.ai.openai_compatible import OpenAICompatibleAIClient, _split_text_chunks
from app.domain.settings_manager import normalize_translation_chunk_size


def test_translation_reuses_prefix_before_target_language(monkeypatch):
    client = OpenAICompatibleAIClient('key', 'model', None)
    captured = []
    monkeypatch.setattr(client, '_chat_text', lambda prompt, system_prompt=None: captured.append((system_prompt, prompt)) or 'Translated')
    client._translate_text('A mother said yes.\n\nHer son smiled.', 'Italian', article_title='Title')
    client._translate_text('A mother said yes.\n\nHer son smiled.', 'Polish', article_title='Other title')
    left, right = captured
    assert left[0] == right[0]
    assert left[1].split('</source_text>')[0] == right[1].split('</source_text>')[0]
    assert left[1].index('<source_text>') < left[1].index('TARGET LANGUAGE (authoritative')
    assert 'quoted' in left[1] and 'paragraph' in left[1]
    assert 'Italian' in left[1] and 'Polish' in right[1]


def test_chunk_limit_accepts_fifty_thousand_without_losing_text():
    assert normalize_translation_chunk_size(50000) == 50000
    text = 'a' * 40000
    client = OpenAICompatibleAIClient('key', 'model', None, translation_chunk_size=50000)
    assert _split_text_chunks(text, client.translation_chunk_size) == [text]


def test_sequential_clients_share_account_capacity_without_forcing_one_slot():
    a = OpenAICompatibleAIClient('same-key', 'm', None, base_url='https://api.test/v1/', account_key='saved-a', translation_mode='sequential', max_concurrency=4)
    b = OpenAICompatibleAIClient('same-key', 'm', None, base_url='https://api.test/v1', account_key='saved-b', max_concurrency=2)
    assert a.account_key == b.account_key
    assert a.request_limit == 4
    assert a.scheduler.capacity(a.account_key, 4) == 2


def test_different_credentials_have_independent_quotas():
    a = OpenAICompatibleAIClient('first', 'm', None, max_concurrency=4)
    b = OpenAICompatibleAIClient('second', 'm', None, max_concurrency=1)
    assert a.account_key != b.account_key
    assert a.scheduler.capacity(a.account_key, 4) == 4


def test_translation_retry_reuses_title_and_completed_chunks(monkeypatch):
    class Checkpoints:
        values = {}
        def get(self, key, default=None):
            return self.values.get(key, default)
        def save(self, key, value):
            self.values[key] = value
    client = OpenAICompatibleAIClient('test-checkpoint', 'm', None, translation_chunk_size=1000)
    client.recovery = Checkpoints()
    source = ('a' * 900) + '\n\n' + ('b' * 900)
    seen = []
    fail = [True]
    def translate(text, language, **kwargs):
        seen.append(text)
        if text.startswith('b') and fail[0]:
            fail[0] = False
            raise ValueError('Temporary failure')
        return 'Translated ' + text
    monkeypatch.setattr(client, '_translate_text', translate)
    with pytest.raises(ValueError):
        client.translate_article_fields('Title', source, language='Italian')
    result = client.translate_article_fields('Title', source, language='Italian')
    assert seen.count('Title') == 1
    assert seen.count('a' * 900) == 1
    assert seen.count('b' * 900) == 2
    assert result['content'].endswith('b' * 900)


def test_chat_rate_limit_cools_account_and_retries_when_enabled(monkeypatch):
    import responses
    client = OpenAICompatibleAIClient('retry-enabled', 'm', None, base_url='https://quota.test/v1')
    client.retry_transient = True
    monkeypatch.setattr(client, '_retry_delay', lambda response, attempt: 0)
    with responses.RequestsMock() as mocked:
        mocked.add(responses.POST, 'https://quota.test/v1/chat/completions', json={'error':'limit'},status=429)
        mocked.add(responses.POST, 'https://quota.test/v1/chat/completions', json={'choices':[{'message':{'content':'Success'}}]},status=200)
        assert client.chat([{'role':'user','content':'hello'}])['content'] == 'Success'
        assert len(mocked.calls) == 2


def test_long_translation_reserves_enough_completion_tokens():
    import responses, json
    client = OpenAICompatibleAIClient('large-story', 'deepseek-flash', None, base_url='https://large.test/v1')
    with responses.RequestsMock() as mocked:
        mocked.add(responses.POST, 'https://large.test/v1/chat/completions', json={'choices':[{'finish_reason':'stop','message':{'content':'Translated'}}]},status=200)
        client._translate_text('a' * 40000, 'Italian')
        payload = json.loads(mocked.calls[0].request.body)
        assert payload['max_tokens'] >= 30000


def test_cancelled_http_failure_is_not_retried(monkeypatch):
    import threading
    import requests
    from app.integrations.ai.scheduler import AIRequestScheduler
    cancelled = threading.Event()
    client = OpenAICompatibleAIClient('cancel-test', 'm', None, scheduler=AIRequestScheduler(), cancelled=cancelled.is_set)
    calls = []
    def post(*args, **kwargs):
        calls.append(1)
        cancelled.set()
        raise requests.Timeout('slow provider')
    monkeypatch.setattr(requests, 'post', post)
    monkeypatch.setattr(client, '_retry_delay', lambda *args: 0)
    with pytest.raises(InterruptedError):
        client._post_json('https://fake.test', {}, {}, attempts=1)
    assert len(calls) == 1
    assert client.scheduler.snapshot(client.account_key)['active'] == 0


def test_retry_after_is_capped_and_ignores_nonfinite_values():
    import requests
    client = OpenAICompatibleAIClient('delay-test', 'm', None)
    response = requests.Response()
    for value in ('86400', 'inf', 'nan'):
        response.headers['Retry-After'] = value
        delay = client._retry_delay(response, 0)
        assert 0 <= delay <= 30


def test_translation_reports_title_before_network_request(monkeypatch):
    client = OpenAICompatibleAIClient('title-progress', 'm', None)
    events = []
    def translate(text, *args, **kwargs):
        assert events, 'UI must leave queued state before the first network call'
        return 'Translated ' + text
    monkeypatch.setattr(client, '_translate_text', translate)
    client.translate_article_fields('Title', 'Body', language='Italian', progress_callback=events.append)
    assert 'title' in events[0].lower()


def test_request_timeout_does_not_restart_full_budget_for_each_retry(monkeypatch):
    import requests
    from types import SimpleNamespace
    import app.integrations.ai.openai_compatible as module
    from app.integrations.ai.scheduler import AIRequestScheduler
    clock = [0.0]
    calls = []
    client = OpenAICompatibleAIClient('budget-test', 'm', None, scheduler=AIRequestScheduler())
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda value: None))
    monkeypatch.setattr(module, '_get_ai_request_timeout', lambda value: 30)
    monkeypatch.setattr(client, '_retry_delay', lambda *args: 0)
    def post(*args, **kwargs):
        calls.append(kwargs['timeout'])
        clock[0] += 31
        raise requests.Timeout('provider stalled')
    monkeypatch.setattr(requests, 'post', post)
    with pytest.raises(requests.Timeout, match='budget exhausted'):
        client._post_json('https://fake.test', {}, {})
    assert calls == [30]
