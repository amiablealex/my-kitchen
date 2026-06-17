from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Behave correctly behind a reverse proxy / sub-path (HA ingress).
    # Honours X-Forwarded-* so url_for() and relative assets resolve right.
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    db.init_app(app)

    from .main.routes import main_bp
    app.register_blueprint(main_bp)

    return app
