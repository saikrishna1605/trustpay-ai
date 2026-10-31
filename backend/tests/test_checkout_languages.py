import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from .conftest import make_settings

LISTING = {'title': 'Test headphones', 'description': 'Full headphones product specification and condition details.',
           'price': 100, 'seller': {'name': 'Shop'}}

@pytest.mark.parametrize('locale', ['en-US', 'ar-AE', 'fr-FR'])
def test_locale_reaches_paypal_and_is_preserved(client, fake_paypal, locale):
    a = client.post('/api/analyze', json=LISTING).json()
    aid = a['id']
    assert client.post(f'/api/assessments/{aid}/decision', json={'approve': True, 'acknowledge_risk': True, 'note': 'Sandbox testing only'}).status_code == 200
    result = client.post(f'/api/assessments/{aid}/orders', json={'locale': locale})
    assert result.status_code == 200
    sent = [r for r in fake_paypal.requests if r.url.path == '/v2/checkout/orders']
    assert json.loads(sent[0].content)['payment_source']['paypal']['experience_context']['locale'] == locale
    assert client.get(f'/api/assessments/{aid}').json()['checkout_locale'] == locale
    reused = client.post(f'/api/assessments/{aid}/orders', json={'locale': locale}).json()
    assert reused['reused'] is True
    assert reused['locale'] == locale
    assert reused['order_id'] == result.json()['order_id']
    assert len([r for r in fake_paypal.requests if r.url.path == '/v2/checkout/orders']) == 1


def test_invalid_locale_rejected(client):
    assert client.post('/api/assessments/anything/orders', json={'locale': 'invalid'}).status_code == 422


def test_default_locale_config(tmp_path):
    assert make_settings(tmp_path).paypal_locale == 'en-US'
    make_settings(tmp_path, paypal_locale='fr-FR').validate()
    with pytest.raises(RuntimeError):
        make_settings(tmp_path, paypal_locale='invalid').validate()


def test_locale_change_does_not_reuse_wrong_language_or_create_duplicate(client, fake_paypal):
    aid = client.post('/api/analyze', json=LISTING).json()['id']
    client.post(f'/api/assessments/{aid}/decision', json={'approve': True, 'acknowledge_risk': True, 'note': 'Sandbox testing only'})
    first = client.post(f'/api/assessments/{aid}/orders', json={'locale': 'ar-AE'}).json()
    assert 'locale.x=ar_AE' in first['approve_url']
    conflict = client.post(f'/api/assessments/{aid}/orders', json={'locale': 'en-US'})
    assert conflict.status_code == 409
    assert 'fresh assessment' in conflict.json()['detail']
    assert len(fake_paypal.orders) == 1


def test_approval_link_preserves_token_and_replaces_language():
    from app.paypal import localized_approval_url
    from urllib.parse import urlsplit, parse_qs
    url = localized_approval_url('https://www.sandbox.paypal.com/checkoutnow?token=ORDER1&locale.x=ar_AE#pay', 'en-US')
    assert parse_qs(urlsplit(url).query) == {'token': ['ORDER1'], 'locale.x': ['en_US']}
    assert urlsplit(url).fragment == 'pay'
