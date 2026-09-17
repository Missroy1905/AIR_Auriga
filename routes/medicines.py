from flask import Blueprint, request, jsonify
from models import db, Medicine, Batch
from flask_jwt_extended import jwt_required
from datetime import datetime

meds_bp = Blueprint('medicines', __name__)


@meds_bp.route('/medicines', methods=['GET'])
@jwt_required()
def list_medicines():
    # base query (search applied)
    search = request.args.get('search')
    base_q = Medicine.query
    if search:
        base_q = base_q.filter((Medicine.name.ilike(f'%{search}%')) | (Medicine.generic_name.ilike(f'%{search}%')))

    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

    # handle sort by sellable_stock in Python (computed property)
    items = []
    if sort == 'sellable_stock':
        all_items = base_q.all()
        with_stock = [(m, m.sellable_stock()) for m in all_items]
        reverse = (order != 'asc')
        with_stock.sort(key=lambda x: x[1], reverse=reverse)
        total = len(with_stock)
        start = (page - 1) * limit
        page_slice = with_stock[start:start + limit]
        for m, stock in page_slice:
            items.append({'id': m.id, 'name': m.name, 'generic_name': m.generic_name, 'manufacturer': m.manufacturer, 'sellable_stock': stock})
    else:
        # safe sortable fields
        allowed_med_sorts = {'name', 'generic_name', 'manufacturer', 'created_at', 'id'}
        q = base_q
        if sort in allowed_med_sorts and hasattr(Medicine, sort):
            col = getattr(Medicine, sort)
            q = q.order_by(col.asc() if order == 'asc' else col.desc())
        total = q.count()
        meds = q.offset((page - 1) * limit).limit(limit).all()
        for m in meds:
            items.append({'id': m.id, 'name': m.name, 'generic_name': m.generic_name, 'manufacturer': m.manufacturer, 'sellable_stock': m.sellable_stock()})

    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    return jsonify({'items': items, 'page': page, 'limit': limit, 'total': total, 'total_pages': total_pages})


@meds_bp.route('/dashboard/summary', methods=['GET'])
@jwt_required()
def dashboard_summary():
    from datetime import date, timedelta
    today = date.today()
    total_medicines = Medicine.query.count()
    total_sellable_stock = 0
    for m in Medicine.query.all():
        total_sellable_stock += m.sellable_stock()
    # count batches expiring in next 7 days (inclusive) and not quarantined
    expiring_cutoff = today + timedelta(days=7)
    expiring_soon = Batch.query.filter(Batch.expiry_date >= today, Batch.expiry_date <= expiring_cutoff, getattr(Batch, 'quarantined') == False).count()
    return jsonify({'total_medicines': total_medicines, 'total_sellable_stock': total_sellable_stock, 'expiring_soon_count': expiring_soon})


@meds_bp.route('/medicines', methods=['POST'])
@jwt_required()
def create_medicine():
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'msg': 'name required'}), 400
    m = Medicine(name=name, generic_name=data.get('generic_name'), manufacturer=data.get('manufacturer'))
    db.session.add(m)
    db.session.commit()
    return jsonify({'id': m.id}), 201


@meds_bp.route('/medicines/<int:med_id>', methods=['GET'])
@jwt_required()
def get_medicine(med_id):
    m = Medicine.query.get(med_id)
    if not m:
        return jsonify({'msg': 'not found'}), 404
    batches = []
    for b in sorted(m.batches, key=lambda x: x.expiry_date):
        batches.append({
            'id': b.id,
            'batch_number': b.batch_number,
            'quantity': b.quantity,
            'in_date': getattr(b, 'in_date', None).isoformat() if getattr(b, 'in_date', None) else None,
            'expiry_date': b.expiry_date.isoformat(),
            'status': b.status
        })
    return jsonify({'id': m.id, 'name': m.name, 'generic_name': m.generic_name, 'manufacturer': m.manufacturer, 'sellable_stock': m.sellable_stock(), 'batches': batches})


@meds_bp.route('/medicines/<int:med_id>', methods=['PUT'])
@jwt_required()
def update_medicine(med_id):
    m = Medicine.query.get(med_id)
    if not m:
        return jsonify({'msg': 'not found'}), 404
    data = request.get_json() or {}
    m.name = data.get('name', m.name)
    m.generic_name = data.get('generic_name', m.generic_name)
    m.manufacturer = data.get('manufacturer', m.manufacturer)
    db.session.commit()
    return jsonify({'msg': 'updated'})


@meds_bp.route('/medicines/<int:med_id>', methods=['DELETE'])
@jwt_required()
def delete_medicine(med_id):
    m = Medicine.query.get(med_id)
    if not m:
        return jsonify({'msg': 'not found'}), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify({'msg': 'deleted'})


@meds_bp.route('/medicines/<int:med_id>/batches', methods=['GET'])
@jwt_required()
def list_batches(med_id):
    m = Medicine.query.get(med_id)
    if not m:
        return jsonify({'msg': 'not found'}), 404
    sort = request.args.get('sort', 'expiry_date')
    order = request.args.get('order', 'asc')
    bs = Batch.query.filter_by(medicine_id=med_id)
    allowed_batch_sorts = {'expiry_date', 'batch_number', 'quantity', 'created_at', 'id'}
    if sort in allowed_batch_sorts and hasattr(Batch, sort):
        col = getattr(Batch, sort)
        bs = bs.order_by(col.asc() if order == 'asc' else col.desc())
    items = bs.all()
    result = []
    from datetime import date
    today = date.today()
    for b in items:
        status = 'Expired' if b.expiry_date < today else 'Active'
        if getattr(b, 'quarantined', False):
            status = 'Quarantined'
        result.append({'id': b.id, 'batch_number': b.batch_number, 'quantity': b.quantity, 'in_date': getattr(b, 'in_date', None).isoformat() if getattr(b, 'in_date', None) else None, 'expiry_date': b.expiry_date.isoformat(), 'status': status})
    return jsonify(result)


@meds_bp.route('/medicines/<int:med_id>/batches', methods=['POST'])
@jwt_required()
def create_batch(med_id):
    m = Medicine.query.get(med_id)
    if not m:
        return jsonify({'msg': 'medicine not found'}), 404
    data = request.get_json() or {}
    batch_number = data.get('batch_number')
    quantity = data.get('quantity')
    expiry = data.get('expiry_date')
    in_date_raw = data.get('in_date')
    if not batch_number or quantity is None or not expiry or in_date_raw is None:
        return jsonify({'msg': 'batch_number, quantity, in_date and expiry_date required'}), 400
    try:
        expiry_date = datetime.fromisoformat(expiry).date()
        in_date = datetime.fromisoformat(in_date_raw).date()
    except Exception:
        return jsonify({'msg': 'invalid in_date or expiry_date; use ISO format YYYY-MM-DD'}), 400
    if in_date > expiry_date:
        return jsonify({'msg': 'in_date cannot be after expiry_date'}), 422
    try:
        q = int(quantity)
        if q <= 0:
            return jsonify({'msg': 'quantity must be a positive integer'}), 422
    except Exception:
        return jsonify({'msg': 'invalid quantity'}), 422

    b = Batch(medicine_id=med_id, batch_number=batch_number, quantity=q, in_date=in_date, expiry_date=expiry_date)
    db.session.add(b)
    db.session.commit()
    resp = {'id': b.id}
    # warn if already expired
    from datetime import date as _d
    if expiry_date < _d.today():
        resp['warning'] = 'This batch is already expired and will not be sellable or dispensable.'
    return jsonify(resp), 201
