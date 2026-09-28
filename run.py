import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Debug mode hanya aktif jika secara eksplisit diaktifkan via environment variable
    # untuk mencegah risiko Remote Code Execution (RCE) melalui Werkzeug debugger
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')
    
    print("Menjalankan aplikasi Flask Airside Report...")
    print(f"Debug Mode: {'AKTIF (Development)' if debug_mode else 'NONAKTIF (Aman / Production)'}")
    print("Buka browser di http://127.0.0.1:5000")
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)
