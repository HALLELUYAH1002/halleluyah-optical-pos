from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from datetime import datetime
import os


db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///hol_pos.db').replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User, Branch
    from .routes import register_routes

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    register_routes(app)

    with app.app_context():
        db.create_all()
        if not Branch.query.first():
            main_branch = Branch(name='Main Branch', code='MAIN', location='Ilorin')
            db.session.add(main_branch)
            db.session.commit()
        if not User.query.filter_by(username='manager').first():
            manager = User(
                full_name='HOL Manager',
                username='manager',
                role='manager',
                branch_id=Branch.query.first().id,
                password_hash=generate_password_hash(os.getenv('DEFAULT_MANAGER_PASSWORD', 'admin1234')),
                created_at=datetime.utcnow(),
            )
            db.session.add(manager)
            db.session.commit()

    return app
