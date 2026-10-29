import os
import re
import requests
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')


class _DriveRequest:
    def __init__(self, session, method, url, params=None):
        self._session = session
        self._method = method
        self._url = url
        self._params = params or {}

    def execute(self):
        resp = self._session.request(self._method, self._url, params=self._params, timeout=20)
        if resp.status_code >= 400:
            raise Exception(f"Google Drive API Error ({resp.status_code}): {resp.text}")
        if not resp.text or not resp.text.strip():
            return {}
        return resp.json()


class _DriveFilesResource:
    BASE_URL = "https://www.googleapis.com/drive/v3/files"

    def __init__(self, session):
        self._session = session

    def list(self, **kwargs):
        params = {k: v for k, v in kwargs.items() if v is not None}
        return _DriveRequest(self._session, "GET", self.BASE_URL, params=params)

    def emptyTrash(self):
        return _DriveRequest(self._session, "DELETE", f"{self.BASE_URL}/trash")


class _DriveService:
    def __init__(self, creds):
        self._session = AuthorizedSession(creds)

    def files(self):
        return _DriveFilesResource(self._session)


def get_drive_service():
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError("File credentials.json tidak ditemukan.")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return _DriveService(creds)

def create_monthly_sheet(new_file_name, target_folder_id, template_file_id):
    """
    Fungsi ini menyalin file template Spreadsheet menggunakan Google Apps Script proxy.
    Ini mem-bypass limitasi kuota Service Account (0 bytes).
    """
    APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw9pKLrbZEIlZfLC-sHg0DlKtYbYfMFpwuBxwjNTYSOnMGjkc0ccPmF9ABaRdPPdnWp/exec"
    
    payload = {
        "name": new_file_name,
        "folderId": target_folder_id,
        "templateId": template_file_id
    }
    
    # Follow redirects is True by default in requests.post
    response = requests.post(APPS_SCRIPT_URL, json=payload)
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get("success"):
                return data.get("url")
            else:
                raise Exception(data.get("error", "Apps Script error"))
        except ValueError:
            raise Exception(f"Respons tidak valid dari Apps Script: {response.text}")
    else:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")

def find_monthly_sheet(airport_code, target_folder_id, month_abbr, year):
    """
    Mencari file Google Spreadsheet di Google Drive untuk bandara, bulan, dan tahun tertentu.
    Contoh: mencari LOP_NOV_2026 di folder LOP.
    """
    if not target_folder_id:
        return None
    try:
        drive_svc = get_drive_service()
        clean_folder = target_folder_id.strip()
        # Ekstrak ID folder jika berupa URL
        m_id = re.search(r'[-\w]{25,}', clean_folder)
        if m_id:
            clean_folder = m_id.group(0)

        query = f"'{clean_folder}' in parents and trashed=false and mimeType='application/vnd.google-apps.spreadsheet'"
        res = drive_svc.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, webViewLink, modifiedTime)',
            orderBy='modifiedTime desc'
        ).execute()
        files = res.get('files', [])

        code_upper = str(airport_code).upper().strip()
        month_abbr_upper = str(month_abbr).upper().strip()
        year_str = str(year).strip()

        # 1. Exact pattern: misal LOP_NOV_2026
        exact_pattern = f"{code_upper}_{month_abbr_upper}_{year_str}"
        for f in files:
            fname = f.get('name', '').upper()
            if exact_pattern in fname:
                return f

        # 2. Match bandara + bulan + tahun
        for f in files:
            fname = f.get('name', '').upper()
            if code_upper in fname and month_abbr_upper in fname and year_str in fname:
                return f

        # 3. Match bulan + tahun
        for f in files:
            fname = f.get('name', '').upper()
            if month_abbr_upper in fname and year_str in fname:
                return f

        return None
    except Exception as e:
        print(f"Warning find_monthly_sheet ({airport_code}, {month_abbr}, {year}): {e}")
        return None
