from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register Blueprints
    from app.routes.auth_routes import bp as auth_bp
    from app.routes.staff_routes import bp as staff_bp
    from app.routes.admin_routes import bp as admin_bp

    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
