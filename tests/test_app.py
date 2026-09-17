import sys
import os
import pytest
# ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from config import TestConfig
from models import db, Medicine, Batch, User
from werkzeug.security import generate_password_hash
from datetime import date, timedelta


@pytest.fixture
def app():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.app_context():
        db.create_all()
        # seed minimal data
        u = User(username='tester', password_hash=generate_password_hash('pass'))
        db.session.add(u)
        m = Medicine(name='Paracetamol', generic_name='Acetaminophen')
        db.session.add(m)
        db.session.commit()
        today = date.today()
        # one batch
        b1 = Batch(medicine_id=m.id, batch_number='B1', quantity=100, in_date=today - timedelta(days=30), expiry_date=today + timedelta(days=10))
        # second batch
        b2 = Batch(medicine_id=m.id, batch_number='B2', quantity=50, in_date=today - timedelta(days=60), expiry_date=today + timedelta(days=30))
        # expired
        b3 = Batch(medicine_id=m.id, batch_number='OLD', quantity=20, in_date=today - timedelta(days=400), expiry_date=today - timedelta(days=5))
        db.session.add_all([b1, b2, b3])
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def get_token(client):
    r = client.post('/api/auth/login', json={'username': 'tester', 'password': 'pass'})
    assert r.status_code == 200
    return r.get_json()['access_token']


def test_register_login(client):
    r = client.post('/api/auth/register', json={'username': 'newu', 'password': 'pw'})
    assert r.status_code == 201
    r = client.post('/api/auth/login', json={'username': 'newu', 'password': 'pw'})
    assert r.status_code == 200


def test_medicine_creation(client):
    token = get_token(client)
    r = client.post('/api/medicines', json={'name': 'Ibuprofen'}, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 201


def test_batch_creation(client):
    token = get_token(client)
    # create medicine
    r = client.post('/api/medicines', json={'name': 'Cetirizine'}, headers={'Authorization': 'Bearer ' + token})
    mid = r.get_json()['id']
    r = client.post(f'/api/medicines/{mid}/batches', json={'batch_number': 'X1', 'quantity': 10, 'in_date': date.today().isoformat(), 'expiry_date': (date.today()+timedelta(days=40)).isoformat()}, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 201


def test_sellable_excludes_expired(client):
    token = get_token(client)
    r = client.get('/api/medicines', headers={'Authorization': 'Bearer ' + token})
    data = r.get_json()
    # paracetamol had 100+50 sellable (expired excluded)
    assert any(m['name'] == 'Paracetamol' and m['sellable_stock'] == 150 for m in data['items'])


def test_fefo_single_batch(client):
    token = get_token(client)
    # dispense 20 from paracetamol
    # find med id
    r = client.get('/api/medicines', headers={'Authorization': 'Bearer ' + token})
    mids = [m for m in r.get_json()['items'] if m['name']=='Paracetamol']
    mid = mids[0]['id']
    r = client.post(f'/api/medicines/{mid}/dispense', json={'quantity': 20}, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    body = r.get_json()
    assert body['quantity_dispensed'] == 20
    # check remaining sellable
    r = client.get(f'/api/medicines/{mid}', headers={'Authorization': 'Bearer ' + token})
    assert r.get_json()['sellable_stock'] == 130


def test_fefo_across_batches(client):
    token = get_token(client)
    # dispense 140 (will consume first 100 then 40 from second)
    r = client.get('/api/medicines', headers={'Authorization': 'Bearer ' + token})
    mid = [m for m in r.get_json()['items'] if m['name']=='Paracetamol'][0]['id']
    r = client.post(f'/api/medicines/{mid}/dispense', json={'quantity': 140}, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    body = r.get_json()
    assert body['quantity_dispensed'] == 140
    # remaining should be 10 (original sellable 150 - 140)
    r = client.get(f'/api/medicines/{mid}', headers={'Authorization': 'Bearer ' + token})
    assert r.get_json()['sellable_stock'] == 10


def test_cannot_dispense_expired(client):
    token = get_token(client)
    # expired batch exists but cannot be used; try to dispense more than sellable
    r = client.get('/api/medicines', headers={'Authorization': 'Bearer ' + token})
    mid = [m for m in r.get_json()['items'] if m['name']=='Paracetamol'][0]['id']
    # try to over-dispense
    r = client.post(f'/api/medicines/{mid}/dispense', json={'quantity': 1000}, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 400


def test_expiry_alerts(client):
    token = get_token(client)
    r = client.get('/api/alerts/expiry?days=30', headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)


def test_search(client):
    token = get_token(client)
    r = client.get('/api/medicines?search=para', headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    data = r.get_json()
    assert any('Paracetamol' in m['name'] for m in data['items'])


def test_batch_in_date_validation(client):
    token = get_token(client)
    r = client.post('/api/medicines', json={'name': 'TestMed'}, headers={'Authorization': 'Bearer ' + token})
    mid = r.get_json()['id']
    # in_date after expiry should be rejected
    r = client.post(f'/api/medicines/{mid}/batches', json={'batch_number': 'BAD', 'quantity': 5, 'in_date': '2026-12-31', 'expiry_date': '2026-01-01'}, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 422


def test_clock_quarantines_and_counts(client):
    token = get_token(client)
    # call clock to quarantine expired batches
    r = client.post('/api/clock', headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    body = r.get_json()
    assert 'expired_quarantined' in body and 'expiring_soon' in body
