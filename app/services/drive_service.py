from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os

SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')

def get_drive_service():
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError("File credentials.json tidak ditemukan.")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

import requests

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
