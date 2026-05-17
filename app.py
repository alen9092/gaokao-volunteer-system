import os
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from models import db, User

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    basedir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gaokao-sim-secret-key-2026')
    app.config['DEEPSEEK_KEY'] = os.environ.get('DEEPSEEK_KEY', 'sk-507b6946a4604db8b2e5dffd659685a7')
    app.config['DEEPSEEK_URL'] = 'https://api.deepseek.com/v1/chat/completions'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "gaokao.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录后再使用此功能。'
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from auth import auth_bp
    from simulation import sim_bp
    from export import export_bp
    from ai_qa import ai_bp
    from admin import admin_bp
    from recharge import recharge_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(sim_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(ai_bp)
    csrf.exempt(ai_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(recharge_bp)
    csrf.exempt(recharge_bp)

    # Home page
    from flask import render_template
    @app.route('/')
    def index():
        return render_template('index.html')

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)
