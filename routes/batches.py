from flask import Blueprint, request, jsonify
from models import db, Batch, Medicine
from flask_jwt_extended import jwt_required
from services.dispense import dispense_from_medicine

batches_bp = Blueprint('batches', __name__)


@batches_bp.route('/batches/<int:batch_id>', methods=['PUT'])
@jwt_required()
def update_batch(batch_id):
    b = Batch.query.get(batch_id)
    if not b:
        return jsonify({'msg': 'not found'}), 404
    data = request.get_json() or {}
    if 'quantity' in data:
        b.quantity = int(data['quantity'])
    if 'expiry_date' in data:
        try:
            from datetime import datetime

            b.expiry_date = datetime.fromisoformat(data['expiry_date']).date()
        except Exception:
            return jsonify({'msg': 'invalid expiry_date'}), 400
    db.session.commit()
    return jsonify({'msg': 'updated'})


@batches_bp.route('/medicines/<int:med_id>/dispense', methods=['POST'])
@jwt_required()
def dispense(med_id):
    data = request.get_json() or {}
    qty = data.get('quantity')
    if qty is None:
        return jsonify({'msg': 'quantity required'}), 400
    try:
        qty = int(qty)
    except Exception:
        return jsonify({'msg': 'invalid quantity'}), 400
    med = Medicine.query.get(med_id)
    if not med:
        return jsonify({'msg': 'medicine not found'}), 404
    try:
        res = dispense_from_medicine(med_id, qty)
        return jsonify(res)
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
