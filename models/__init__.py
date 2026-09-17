from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    generic_name = db.Column(db.String(200), nullable=True)
    manufacturer = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reorder_threshold = db.Column(db.Integer, default=10, nullable=False)

    batches = db.relationship('Batch', backref='medicine', cascade='all, delete-orphan')

    def sellable_stock(self):
        today = date.today()
        total = 0
        for b in self.batches:
            # sellable only if not expired, not quarantined and quantity > 0
            if b.expiry_date >= today and getattr(b, 'quarantined', False) is False and (b.quantity or 0) > 0:
                total += b.quantity
        return total


class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    batch_number = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    in_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    quarantined = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status(self):
        today = date.today()
        # Expired takes precedence
        if self.expiry_date < today:
            return 'EXPIRED'
        # Quarantined (but not expired)
        if getattr(self, 'quarantined', False):
            return 'QUARANTINED'
        # Expiring soon within 7 days
        if today <= self.expiry_date <= (today + timedelta(days=7)):
            return 'EXPIRING SOON'
        return 'ACTIVE'


class Outbox(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False, nullable=False)
    medicine = db.relationship('Medicine', backref='outbox')