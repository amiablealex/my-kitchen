from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import db, migrate, csrf, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Behave correctly behind a reverse proxy / sub-path (HA ingress).
    # Honours X-Forwarded-* so url_for() and relative assets resolve right.
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    db.init_app(app)

    # App-wide CSRF protection (see base.html meta tag + form hidden fields).
    csrf.init_app(app)

    # Flask-Login: simple session auth. login_view drives @login_required
    # redirects; the app-wide "must be logged in" gate is a before_app_request
    # in the auth blueprint.
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "error"

    # Import models so SQLAlchemy knows about them for create_all().
    from . import models  # noqa: F401

    # Migrations. render_as_batch is required for SQLite: it rebuilds tables
    # to emulate the ALTER TABLE operations SQLite can't do natively. compare_type
    # lets autogenerate notice column-type changes too.
    migrate.init_app(app, db, render_as_batch=True, compare_type=True)

    # CLI: flask init-db / flask seed / flask shell context
    from .cli import register_cli
    register_cli(app)

    # Auth first so its before_app_request gate registers up front.
    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from .main.routes import main_bp
    app.register_blueprint(main_bp)

    from .stock.routes import stock_bp
    app.register_blueprint(stock_bp)

    from .wizard.routes import wizard_bp
    app.register_blueprint(wizard_bp)

    from .history.routes import history_bp
    app.register_blueprint(history_bp)

    from .manage.routes import manage_bp
    app.register_blueprint(manage_bp)

    return app
