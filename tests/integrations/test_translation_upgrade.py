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
