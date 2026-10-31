import asyncio
import json

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import create_app
from app.sponsors import SearchRequest, search_channel3, normalize_products
from .conftest import make_settings


def test_channel3_search_contract_and_secret_stays_server_side(tmp_path):
    def respond(request):
        assert request.url == 'https://api.trychannel3.com/v1/search'
        assert request.headers['x-api-key'] == 'private-key'
        assert json.loads(request.content) == {'query': 'Sony headphones', 'limit': 6}
        return httpx.Response(200, json={'products': [{'id': 'p1', 'title': 'Headphones',
            'images': [{'url': 'https://shop.example/image.jpg'}],
            'offers': [{'price': {'price': 99, 'currency': 'USD'}, 'url': 'https://shop.example/p', 'merchant': 'Shop'}]}]})
    result = asyncio.run(search_channel3(make_settings(tmp_path, channel3_api_key='private-key'),
        SearchRequest(query='Sony headphones'), transport=httpx.MockTransport(respond)))
    assert result['products'][0]['offers'][0]['price'] == 99
    assert result['provider'] == 'Channel3'
    assert 'private-key' not in json.dumps(result)
    assert result['retrieved_at']


def test_missing_key_and_upstream_errors_are_explicit(tmp_path):
    with pytest.raises(HTTPException) as err:
        asyncio.run(search_channel3(make_settings(tmp_path), SearchRequest(query='test')))
    assert err.value.status_code == 503
    for code in (401, 429, 500):
        with pytest.raises(HTTPException) as err:
            asyncio.run(search_channel3(make_settings(tmp_path, channel3_api_key='key'), SearchRequest(query='test'),
                transport=httpx.MockTransport(lambda r: httpx.Response(code, json={'secret': 'hidden'}))))
        assert err.value.status_code in (502, 503)
        assert 'hidden' not in str(err.value.detail)


def test_unsafe_links_and_invalid_prices_not_exposed():
    result = normalize_products([{'title': 'Item', 'images': ['javascript:alert(1)'], 'offers': [
        {'price': {'price': 10, 'currency': 'EUR'}, 'url': 'javascript:alert(1)'},
        {'price': {'price': 'NaN'}}, {'price': {'price': -1}}]}])
    assert result[0]['image_url'] is None
    assert len(result[0]['offers']) == 1
    assert result[0]['offers'][0]['url'] is None


def test_sponsor_routes_protected(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path, api_key='access')))
    for path in ('/api/analytics', '/api/sponsors/status'):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={'X-API-Key': 'access'}).status_code == 200
    assert client.post('/api/products/search', json={'query': 'camera'}).status_code == 401


def test_analytics_uses_persisted_assessments(client):
    listing = {'title': 'Camera', 'price': 100, 'currency': 'EUR', 'seller': {'name': 'Camera shop'}}
    response = client.post('/api/analyze', json=listing)
    assert response.status_code == 200
    result = client.get('/api/analytics').json()
    assert result['totals']['assessments'] == 1
    assert result['rows'][0]['id'] == response.json()['id']
    assert result['rows'][0]['currency'] == 'EUR'
    assert result['rows'][0]['payment_status'] == 'NOT_STARTED'
    assert result['totals']['completed'] == 0


def test_search_validation_and_missing_provider(client):
    assert client.post('/api/products/search', json={'query': 'x', 'limit': 100}).status_code == 422
    assert client.post('/api/products/search', json={'query': 'camera'}).status_code == 503


def test_developer_status_is_protected_and_does_not_return_secrets(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path, api_key='private-access', channel3_api_key='private-channel3')))
    assert client.get('/api/developer/status').status_code == 401
    result = client.get('/api/developer/status', headers={'X-API-Key': 'private-access'})
    assert result.status_code == 200
    assert result.json()['default_checkout_locale'] == 'en-US'
    assert result.json()['channel3_configured'] is True
    assert 'private-access' not in result.text
    assert 'private-channel3' not in result.text
    assert 'sk-test' not in result.text
