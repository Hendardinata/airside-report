AIRPORTS = {
    'DPS': {'name': 'Bali', 'id': 'DPS', 'code': '1. Kantor Cabang DPS'},
    'LOP': {'name': 'Lombok', 'id': 'LOP', 'code': '2. Kantor Cabang LOP'},
    'KOE': {'name': 'Kupang', 'id': 'KOE', 'code': '3. Kantor Cabang KOE'},
    'BWX': {'name': 'Banyuwangi', 'id': 'BWX', 'code': '4. Kantor Cabang BWX'}
}

from app.models.user_store import (
    load_users,
    get_user,
    get_all_users,
    add_user,
    update_user_status,
    update_user,
    delete_user,
    verify_user_password
)

class _UserStoreProxy(dict):
    """
    Proxy dictionary agar seluruh kode yang memanggil USERS[key], USERS.get(key),
    atau 'key' in USERS selalu mendapatkan data akun terbaru dari database SQLite secara dinamis.
    """
    def __getitem__(self, key):
        return load_users()[str(key).lower()]

    def get(self, key, default=None):
        if not key:
            return default
        return load_users().get(str(key).lower(), default)

    def __contains__(self, key):
        if not key:
            return False
        return str(key).lower() in load_users()

    def keys(self):
        return load_users().keys()

    def values(self):
        return load_users().values()

    def items(self):
        return load_users().items()

    def __iter__(self):
        return iter(load_users())

    def __len__(self):
        return len(load_users())

USERS = _UserStoreProxy()

