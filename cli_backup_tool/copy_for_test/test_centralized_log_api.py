import pytest
import json
from centralized_log_api import app, init_db


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client


def test_add_system(client):
    data = {'name': 'TestSystem', 'ip_address': '127.0.0.1'}
    response = client.post('/systems', json=data)

    assert response.status_code == 201
    assert 'System added successfully' in response.get_data(as_text=True)


def test_add_log_entry(client):
    system_data = {'name': 'TestSystem', 'ip_address': '127.0.0.1'}
    client.post('/systems', json=system_data)

    log_data = {
        'system_name': 'TestSystem',
        'log_date': '2022-01-19',
        'log_level': 'INFO',
        'message': 'Test log message',
        'directory': '/var/log/test.log'
    }
    response = client.post('/logs', json=log_data)

    assert response.status_code == 201
    assert 'Log entry added successfully' in response.get_data(as_text=True)


def test_get_all_logs(client):
    response = client.get('/logs')

    assert response.status_code == 200
    assert isinstance(json.loads(response.get_data(as_text=True)), list)


def test_get_logs_by_system(client):
    system_data = {'name': 'TestSystem', 'ip_address': '127.0.0.1'}
    client.post('/systems', json=system_data)

    response = client.get('/logs/system/TestSystem')

    assert response.status_code == 200
    assert isinstance(json.loads(response.get_data(as_text=True)), list)


def test_get_logs_by_date(client):
    response = client.get('/logs/date/2022-01-19')

    assert response.status_code == 200
    assert isinstance(json.loads(response.get_data(as_text=True)), list)


def test_delete_logs_before_date(client):
    client.post('/logs', json={
        'system_name': 'TestSystem',
        'log_date': '2022-01-18',
        'log_level': 'INFO',
        'message': 'Log to be deleted',
        'directory': '/var/log/test.log'
    })

    response = client.delete('/logs/delete-before/2022-01-19')

    assert response.status_code == 200
    assert 'Logs deleted successfully' in response.get_data(as_text=True)


def test_update_log(client):
    system_data = {'name': 'TestSystem', 'ip_address': '127.0.0.1'}
    client.post('/systems', json=system_data)

    log_data = {
        'system_name': 'TestSystem',
        'log_date': '2022-01-19',
        'log_level': 'INFO',
        'message': 'Original log message',
        'directory': '/var/log/test.log'
    }
    response = client.post('/logs', json=log_data)
    log_id = json.loads(response.get_data(as_text=True)).get('log_id')

    update_data = {'system': 1, 'log_level': 'ERROR', 'message': 'Updated log message', 'directory': '/var/log/updated.log'}
    response = client.put(f'/logs/update/9', json=update_data)

    assert response.status_code == 200
    assert 'Log entry updated successfully' in response.get_data(as_text=True)
