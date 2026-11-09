from types import SimpleNamespace
import requests

from app.services.account_service import fetch_ai_models
from app.services.ai_client_factory import create_ai_client


def test_blank_saved_base_url_uses_the_account_form_default(mocker):
    get = mocker.patch("app.services.account_service.requests.get")
    get.return_value.json.return_value = {"data": [{"id": "model-a"}]}
    get.return_value.raise_for_status.return_value = None
    config = {"base_url": "", "api_key": "secret"}

    assert fetch_ai_models(config)[0]["id"] == "model-a"
    assert get.call_args.args[0] == "http://localhost:20128/v1/models"

    account = SimpleNamespace(id="ai", config=config)
    client = create_ai_client(account, settings={})
    assert client.base_url == "http://localhost:20128/v1"


def test_model_discovery_retries_one_transient_connection_failure(mocker):
    get = mocker.patch("app.services.account_service.requests.get")
    response = mocker.Mock()
    response.json.return_value = {"data": [{"id": "model-a"}]}
    get.side_effect = [requests.Timeout("temporary"), response]

    assert fetch_ai_models({"base_url": "http://localhost:20128/v1"})[0]["id"] == "model-a"
    assert get.call_count == 2
