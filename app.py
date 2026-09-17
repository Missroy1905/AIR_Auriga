from flask import Flask, render_template
from flask_jwt_extended import JWTManager
from models import db
from routes.auth import auth_bp
from routes.medicines import meds_bp
from routes.batches import batches_bp
from routes.alerts import alerts_bp
import os
from config import Config


def create_app(test_config=None):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    JWTManager(app)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(meds_bp, url_prefix='/api')
    app.register_blueprint(batches_bp, url_prefix='/api')
    app.register_blueprint(alerts_bp, url_prefix='/api')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/register')
    def register_page():
        return render_template('register.html')

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/alerts')
    def alerts_page():
        return render_template('alerts.html')

    @app.route('/medicines/<int:med_id>')
    def medicine_detail(med_id):
        return render_template('medicine_detail.html', med_id=med_id)

    # ensure DB exists and seed
    with app.app_context():
        db_path = os.path.join(os.getcwd(), 'pharmadost.db')
        if not os.path.exists(db_path):
            db.create_all()
            # seed
            from seed import seed_data

            seed_data(db)
        else:
            # ensure schema updates for development: add quarantined column if missing
            from sqlalchemy import text
            # Only attempt schema changes if the table exists in this engine
            if db.engine.has_table('batch'):
                conn = db.engine.connect()
                try:
                    res = conn.execute(text("PRAGMA table_info('batch')")).fetchall()
                    cols = [r[1] for r in res]
                    if 'quarantined' not in cols:
                        conn.execute(text("ALTER TABLE batch ADD COLUMN quarantined BOOLEAN DEFAULT 0"))
                finally:
                    conn.close()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)