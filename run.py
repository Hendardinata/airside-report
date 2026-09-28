from app import create_app

app = create_app()

if __name__ == '__main__':
    print("Menjalankan aplikasi Flask Airside Report...")
    print("Buka browser di http://localhost:5000")
    app.run(debug=True, port=5000)
