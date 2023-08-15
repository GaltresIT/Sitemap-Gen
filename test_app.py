import app
import pytest

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client

def test_index_page(client):
    response = client.get('/')
    assert b'Sitemap Generator' in response.data

def test_sitemap_generation(client):
    response = client.post('/generate_sitemap', data={'url': 'https://www.example.com'})
    assert b'urlset' in response.data

def test_invalid_url(client):
    response = client.post('/generate_sitemap', data={'url': 'invalid_url'})
    assert b'Invalid URL' in response.data
