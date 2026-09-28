from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.airport_profiles import USERS

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET'])
def index():
    if 'user_id' in session:
        user = USERS.get(session['user_id'])
        if user and user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user:
            return redirect(url_for('staff.dashboard'))
    return render_template('login.html')

@bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    # Simple authentication
    if username in USERS and USERS[username]['password'] == password:
        session['user_id'] = username
        if USERS[username]['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('staff.dashboard'))
    
    return redirect(url_for('auth.index'))

@bp.route('/api/auth/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('auth.index'))
