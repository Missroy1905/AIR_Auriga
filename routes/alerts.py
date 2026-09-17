from flask import Blueprint, request, jsonify
from models import Batch, Medicine, db
from datetime import date, timedelta
from flask_jwt_extended import jwt_required

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('/alerts/expiry', methods=['GET'])
@jwt_required()
def expiry_alerts():
    days = int(request.args.get('days', 30))
    today = date.today()
    end = today + timedelta(days=days)
    batches = Batch.query.filter(Batch.expiry_date >= today, Batch.expiry_date <= end).order_by(Batch.expiry_date.asc()).all()
    result = []
    for b in batches:
        med = Medicine.query.get(b.medicine_id)
        days_remaining = (b.expiry_date - today).days
        status = 'Expired' if b.expiry_date < today else 'Active'
        result.append({'id': b.id, 'medicine': med.name if med else None, 'batch_number': b.batch_number, 'quantity': b.quantity, 'expiry_date': b.expiry_date.isoformat(), 'days_remaining': days_remaining, 'status': status})
    return jsonify(result)



@alerts_bp.route('/clock', methods=['POST'])
@jwt_required()
def run_clock():
    """Simulate daily job: quarantine expired batches and count expiring soon."""
    from models import Batch
    from datetime import date, timedelta
    today = date.today()
    # quarantine expired
    expired = Batch.query.filter(Batch.expiry_date < today, Batch.quarantined == False).all()
    expired_count = 0
    for b in expired:
        b.quarantined = True
        expired_count += 1
        db.session.add(b)
    # expiring soon count (non-expired, not quarantined)
    end = today + timedelta(days=7)
    expiring_soon = Batch.query.filter(Batch.expiry_date >= today, Batch.expiry_date <= end, Batch.quarantined == False).count()
    db.session.commit()
    return jsonify({'expired_quarantined': expired_count, 'expiring_soon': expiring_soon})
