from datetime import date, timedelta

def seed_data(db):
    from models import Medicine, Batch, User
    # create demo user
    if not User.query.filter_by(username='admin').first():
        from werkzeug.security import generate_password_hash

        u = User(username='admin', password_hash=generate_password_hash('password'))
        db.session.add(u)

    meds = [
        {'name': 'Paracetamol', 'generic_name': 'Acetaminophen', 'manufacturer': 'Acme Pharma'},
        {'name': 'Amoxicillin', 'generic_name': 'Amoxicillin', 'manufacturer': 'HealthCorp'},
        {'name': 'Ibuprofen', 'generic_name': 'Ibuprofen', 'manufacturer': 'MediLife'},
        {'name': 'Cetirizine', 'generic_name': 'Cetirizine', 'manufacturer': 'AllergyFree'},
        {'name': 'Metformin', 'generic_name': 'Metformin', 'manufacturer': 'GlucoCare'},
    ]
    created = []
    for m in meds:
        if not Medicine.query.filter_by(name=m['name']).first():
            med = Medicine(name=m['name'], generic_name=m['generic_name'], manufacturer=m['manufacturer'])
            db.session.add(med)
            created.append(med)
    db.session.commit()

    # add batches
    today = date.today()
    for med in Medicine.query.all():
        # add 3 batches
        Batch = globals().get('Batch')
        if not Batch:
            from models import Batch as B
            Batch = B
        db.session.add(Batch(medicine_id=med.id, batch_number='B1-'+str(med.id), quantity=100, in_date=today - timedelta(days=180), expiry_date=today + timedelta(days=90)))
        db.session.add(Batch(medicine_id=med.id, batch_number='B2-'+str(med.id), quantity=50, in_date=today - timedelta(days=60), expiry_date=today + timedelta(days=20)))
        # expired batch
        db.session.add(Batch(medicine_id=med.id, batch_number='OLD-'+str(med.id), quantity=10, in_date=today - timedelta(days=365), expiry_date=today - timedelta(days=10)))
        # for first medicine, add a batch expiring within 7 days
        if med.name == 'Paracetamol':
            db.session.add(Batch(medicine_id=med.id, batch_number='SOON-'+str(med.id), quantity=25, in_date=today - timedelta(days=30), expiry_date=today + timedelta(days=5)))
    db.session.commit()
