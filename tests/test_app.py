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


def test_search_endpoint_with_sellable_and_in_date(client):
    token = get_token(client)
    from datetime import date, timedelta
    today = date.today()
    # create medicines
    r = client.post('/api/medicines', json={'name': 'SearchOne'}, headers={'Authorization': 'Bearer ' + token})
    m1 = r.get_json()['id']
    r = client.post('/api/medicines', json={'name': 'SearchTwo'}, headers={'Authorization': 'Bearer ' + token})
    m2 = r.get_json()['id']
    r = client.post('/api/medicines', json={'name': 'SearchMixed'}, headers={'Authorization': 'Bearer ' + token})
    m3 = r.get_json()['id']
    # m1: expired-only
    client.post(f'/api/medicines/{m1}/batches', json={'batch_number': 'E1', 'quantity': 10, 'in_date': (today-timedelta(days=30)).isoformat(), 'expiry_date': (today-timedelta(days=1)).isoformat()}, headers={'Authorization': 'Bearer ' + token})
    # m2: in-date
    client.post(f'/api/medicines/{m2}/batches', json={'batch_number': 'I1', 'quantity': 25, 'in_date': (today-timedelta(days=5)).isoformat(), 'expiry_date': (today+timedelta(days=20)).isoformat()}, headers={'Authorization': 'Bearer ' + token})
    # m3: mixed
    client.post(f'/api/medicines/{m3}/batches', json={'batch_number': 'MX1', 'quantity': 0, 'in_date': (today-timedelta(days=5)).isoformat(), 'expiry_date': (today+timedelta(days=20)).isoformat()}, headers={'Authorization': 'Bearer ' + token})
    client.post(f'/api/medicines/{m3}/batches', json={'batch_number': 'MX2', 'quantity': 5, 'in_date': (today-timedelta(days=50)).isoformat(), 'expiry_date': (today+timedelta(days=2)).isoformat()}, headers={'Authorization': 'Bearer ' + token})

    # search for 'Search' should return all three
    r = client.get('/api/medicines/search?q=Search', headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    data = r.get_json()
    names = {it['name']: it for it in data['items']}
    assert 'SearchOne' in names and 'SearchTwo' in names and 'SearchMixed' in names
    # verify sellable and in_date
    assert names['SearchOne']['sellable_stock'] == 0
    assert names['SearchOne']['in_date'] is False
    assert names['SearchTwo']['sellable_stock'] == 25
    assert names['SearchTwo']['in_date'] is True
    # SearchMixed has one batch with 5 sellable
    assert names['SearchMixed']['sellable_stock'] == 5
    assert names['SearchMixed']['in_date'] is True


def test_reorder_outbox_created_on_threshold_breach(client):
    token = get_token(client)
    from datetime import date, timedelta
    today = date.today()
    # create medicine
    r = client.post('/api/medicines', json={'name': 'ReorderMed'}, headers={'Authorization': 'Bearer ' + token})
    mid = r.get_json()['id']
    # set reorder_threshold to 20 using app context
    app = client.application
    from models import db, Medicine, Outbox
    with app.app_context():
        m = Medicine.query.get(mid)
        m.reorder_threshold = 20
        db.session.commit()
    # add batches totalling 25
    client.post(f'/api/medicines/{mid}/batches', json={'batch_number': 'R1', 'quantity': 25, 'in_date': (today-timedelta(days=2)).isoformat(), 'expiry_date': (today+timedelta(days=30)).isoformat()}, headers={'Authorization': 'Bearer ' + token})
    # dispense 10 -> remaining 15 < threshold -> should create outbox
    r = client.post(f'/api/medicines/{mid}/dispense', json={'quantity': 10}, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    # check outbox entries via API
    r = client.get('/api/outbox', headers={'Authorization': 'Bearer ' + token})
    data = r.get_json()
    assert data['total'] == 1
    # dispense again while still below threshold -> no new outbox
    r = client.post(f'/api/medicines/{mid}/dispense', json={'quantity': 1}, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    r = client.get('/api/outbox', headers={'Authorization': 'Bearer ' + token})
    data = r.get_json()
    assert data['total'] == 1


def test_clock_idempotent_quarantine_and_counts(client):
    token = get_token(client)
    from datetime import date, timedelta
    today = date.today()
    # create medicine and batches
    r = client.post('/api/medicines', json={'name': 'ClockMed'}, headers={'Authorization': 'Bearer ' + token})
    mid = r.get_json()['id']
    # expired non-quarantined batch
    client.post(f'/api/medicines/{mid}/batches', json={'batch_number': 'EX', 'quantity': 5, 'in_date': (today-timedelta(days=30)).isoformat(), 'expiry_date': (today-timedelta(days=1)).isoformat()}, headers={'Authorization': 'Bearer ' + token})
    # expiring in 3 days
    client.post(f'/api/medicines/{mid}/batches', json={'batch_number': 'S3', 'quantity': 10, 'in_date': (today-timedelta(days=5)).isoformat(), 'expiry_date': (today+timedelta(days=3)).isoformat()}, headers={'Authorization': 'Bearer ' + token})
    # safe batch far out
    client.post(f'/api/medicines/{mid}/batches', json={'batch_number': 'OK', 'quantity': 20, 'in_date': (today-timedelta(days=5)).isoformat(), 'expiry_date': (today+timedelta(days=100)).isoformat()}, headers={'Authorization': 'Bearer ' + token})

    # first clock run
    r = client.post('/api/clock', headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    body = r.get_json()
    # at least the created expired batch should have been quarantined; expiring soon should be 1
    assert body['expiring_soon'] == 1
    # verify the expired batch is now quarantined by fetching medicine detail
    r = client.get(f'/api/medicines/{mid}', headers={'Authorization': 'Bearer ' + token})
    batches = r.get_json()['batches']
    ex_batch = [b for b in batches if b['batch_number']=='EX'][0]
    assert ex_batch['status'] == 'QUARANTINED' or ex_batch['status'] == 'EXPIRED' or getattr(ex_batch, 'status', None)

    # second clock run (idempotency)
    r = client.post('/api/clock', headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    body2 = r.get_json()
    # nothing new should be quarantined
    assert body2['expired_quarantined'] == 0
    assert body2['expiring_soon'] == 1


def test_messy_batch_import(client):
    token = get_token(client)
    # create medicine with no prior batches of these numbers
    r = client.post('/api/medicines', json={'name': 'ImportMed'}, headers={'Authorization': 'Bearer ' + token})
    mid = r.get_json()['id']
    payload = [
        {"batch_number": "B5-1", "quantity": "50", "in_date": "01/03/2026", "expiry_date": "2026-12-01"},
        {"batch_number": "B5-2", "quantity": "10 units", "in_date": None, "expiry_date": "15/01/2027"},
        {"batch_number": "B5-1", "quantity": 50, "in_date": "2026-03-01", "expiry_date": "2026-12-01"},
        {"batch_number": "B5-3", "quantity": "abc", "in_date": "2026-01-01", "expiry_date": "2026-06-01"},
        {"batch_number": "B5-4", "quantity": 20, "in_date": "2026-01-01", "expiry_date": "not-a-date"}
    ]
    r = client.post(f'/api/medicines/{mid}/batches/import', json=payload, headers={'Authorization': 'Bearer ' + token})
    assert r.status_code == 200
    body = r.get_json()
    assert body['imported'] == 2
    assert body['deduped'] == 1
    assert body['rejected'] == 2
    # errors should reference rows 3 and 4
    reasons = {e['row']: e['reason'] for e in body['errors']}
    assert 3 in reasons and reasons[3] == 'invalid quantity'
    assert 4 in reasons and reasons[4] == 'invalid expiry_date'
