from models import db, Batch, Medicine
from datetime import date


def dispense_from_medicine(med_id, quantity):
    if quantity <= 0:
        raise ValueError('quantity must be positive')
    med = Medicine.query.get(med_id)
    if not med:
        raise ValueError('medicine not found')
    today = date.today()
    eligible = Batch.query.filter(
        Batch.medicine_id == med_id,
        Batch.expiry_date >= today,
        Batch.quantity > 0,
        Batch.quarantined == False,
    ).order_by(Batch.expiry_date.asc(), Batch.id.asc()).with_for_update().all()
    total = sum(b.quantity for b in eligible)
    if quantity > total:
        raise ValueError('not enough sellable stock')

    remaining = quantity
    used = []
    # use a transaction
    session = db.session
    try:
        # use nested transaction (savepoint) to be safe inside request-managed transactions
        with session.begin_nested():
            for b in eligible:
                if remaining <= 0:
                    break
                take = min(b.quantity, remaining)
                b.quantity -= take
                remaining -= take
                used.append({'batch_id': b.id, 'batch_number': b.batch_number, 'taken': take, 'expiry_date': b.expiry_date.isoformat()})
                session.add(b)
        # commit outer transaction
        session.commit()
    except Exception:
        session.rollback()
        raise

    sellable_after = med.sellable_stock()
    return {'quantity_dispensed': quantity, 'medicine': {'id': med.id, 'name': med.name}, 'batches_used': used, 'sellable_stock_remaining': sellable_after}
