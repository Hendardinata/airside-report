import os
from flask import Flask, session, request, abort, jsonify, send_from_directory, redirect
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
            # Endpoint otentikasi publik (/login & /api/auth/logout) dikecualikan dari CSRF abort
            # agar pengguna tidak terblokir saat sesi kedaluwarsa atau cache peramban desinkron
            req_path = (request.path or '').rstrip('/')
            if req_path in ('/login', '/api/auth/logout') or request.endpoint in ('auth.login', 'auth.logout'):
                return

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
                if request.is_json or request.path.startswith(('/admin/', '/staff/', '/gm/')):
                    return jsonify({
                        "status": "error",
                        "success": False,
                        "error": "Permintaan ditolak: Token CSRF tidak valid atau telah kedaluwarsa. Silakan muat ulang halaman."
                    }), 403
                abort(403, description="Token CSRF tidak valid atau telah kedaluwarsa. Silakan muat ulang halaman.")

    # Graceful 403 Forbidden handler
    @app.errorhandler(403)
    def handle_forbidden(e):
        if request.is_json or request.path.startswith(('/admin/', '/staff/', '/gm/')):
            return jsonify({
                "status": "error",
                "success": False,
                "error": str(getattr(e, 'description', 'Permintaan ditolak: Token CSRF tidak valid.'))
            }), 403
        from flask import flash, redirect, url_for
        flash("Sesi Anda telah kedaluwarsa atau token tidak valid. Silakan masuk kembali.", "warning")
        return redirect(url_for('auth.index'))

    # 3. HTTP Security Headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

        # Mencegah peramban menyimpan cache halaman HTML (portal, dashboard, login)
        # agar setelah logout peramban selalu meminta halaman segar tanpa perlu refresh manual
        if 'text/html' in response.headers.get('Content-Type', ''):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, post-check=0, pre-check=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

        return response

    # Register Blueprints
    from app.routes.auth_routes import bp as auth_bp
    from app.routes.staff_routes import bp as staff_bp
    from app.routes.admin_routes import bp as admin_bp
    from app.routes.gm_routes import bp as gm_bp

    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(gm_bp, url_prefix='/gm')

    # Alias URL /dh ke /gm untuk fleksibilitas navigasi Department Head
    @app.route('/dh')
    @app.route('/dh/<path:subpath>')
    def redirect_dh(subpath=""):
        suffix = f"/{subpath}" if subpath else "/dashboard"
        return redirect(f"/gm{suffix}")


    # Direct route for /favicon.ico requests
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static', 'img'),
            'logo-kawung.png',
            mimetype='image/png'
        )

    # Inisialisasi Database SQLite lokal
    from app.models.db import init_db
    try:
        init_db()
    except Exception as db_err:
        print(f"Warning inisialisasi SQLite database: {db_err}")

    return app
