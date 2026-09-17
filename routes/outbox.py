from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, Outbox

outbox_bp = Blueprint('outbox', __name__)


@outbox_bp.route('/outbox', methods=['GET'])
@jwt_required()
def list_outbox():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    q = Outbox.query.filter_by(resolved=False).order_by(Outbox.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    result = []
    for o in items:
        result.append({'id': o.id, 'medicine_id': o.medicine_id, 'message': o.message, 'created_at': o.created_at.isoformat(), 'resolved': o.resolved})
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    return jsonify({'items': result, 'page': page, 'limit': limit, 'total': total, 'total_pages': total_pages})


@outbox_bp.route('/outbox/<int:oid>/resolve', methods=['POST'])
@jwt_required()
def resolve_outbox(oid):
    o = Outbox.query.get(oid)
    if not o:
        return jsonify({'msg': 'not found'}), 404
    o.resolved = True
    db.session.commit()
    return jsonify({'msg': 'resolved'})
