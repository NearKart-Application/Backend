import pytest


@pytest.mark.django_db
def test_health_check(anon_client):
    response = anon_client.get('/api/v1/health/')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
