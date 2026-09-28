from flask import Flask, session, request, abort, jsonify
from config import Config
import secrets
import hmac

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 1. CSRF Token Generator & Context Processor
    def generate_csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        return session['_csrf_token']

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf_token)

    # 2. CSRF Protection Middleware
    @app.before_request
    def validate_csrf():
        # Validasi hanya metode HTTP yang memutasi state
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            token = (
                request.headers.get('X-CSRFToken') or
                request.headers.get('X-CSRF-Token') or
                request.form.get('csrf_token')
            )
            if not token and request.is_json:
                try:
                    data = request.get_json(silent=True)
                    if isinstance(data, dict):
                        token = data.get('csrf_token')
                except Exception:
                    pass

            expected_token = session.get('_csrf_token')

            if not token or not expected_token or not hmac.compare_digest(str(token), str(expected_token)):
                if request.is_json or request.path.startswith(('/admin/api/', '/staff/api/')):
                    return jsonify({
                        "success": False,
                        "error": "Permintaan ditolak: Token CSRF tidak valid atau telah kedaluwarsa. Silakan muat ulang halaman."
                    }), 403
                abort(403, description="Token CSRF tidak valid atau telah kedaluwarsa. Silakan muat ulang halaman.")

    # 3. HTTP Security Headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response

    # Register Blueprints
    from app.routes.auth_routes import bp as auth_bp
    from app.routes.staff_routes import bp as staff_bp
    from app.routes.admin_routes import bp as admin_bp

    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
