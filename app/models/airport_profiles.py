AIRPORTS = {
    'LOP': {'name': 'Lombok', 'id': 'LOP', 'code': '1. Kantor Cabang LOP'},
    'DPS': {'name': 'Bali', 'id': 'DPS', 'code': '2. Kantor Cabang DPS'},
    'BWX': {'name': 'Banyuwangi', 'id': 'BWX', 'code': '3. Kantor Cabang BWX'},
    'KOE': {'name': 'Kupang', 'id': 'KOE', 'code': '4. Kantor Cabang KOE'}
}

# Mock database untuk user (Dalam produksi bisa memakai database sebenarnya)
USERS = {
    'admin': {'password': '123', 'role': 'admin', 'name': 'Admin Regional'},
    'lop': {'password': '123', 'role': 'staff', 'airport': 'LOP', 'name': 'Petugas LOP'},
    'dps': {'password': '123', 'role': 'staff', 'airport': 'DPS', 'name': 'Petugas DPS'},
    'bwx': {'password': '123', 'role': 'staff', 'airport': 'BWX', 'name': 'Petugas BWX'},
    'koe': {'password': '123', 'role': 'staff', 'airport': 'KOE', 'name': 'Petugas KOE'},
}
