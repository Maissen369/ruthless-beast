# bot_modules/files_operations.py

import os
import shutil
import zipfile
import hashlib
import stat
import time
import msvcrt
from cryptography.fernet import Fernet
import telebot

# Utility function to chunk large texts for Telegram
def split_message(text, max_length=4096):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

class FilesOperations:
    def __init__(self, bot: telebot.TeleBot, verify_telegram_id, upload_directory="./uploads"):
        self.bot = bot
        self.verify_telegram_id = verify_telegram_id
        self.upload_directory = upload_directory
        if not os.path.exists(self.upload_directory):
            os.makedirs(self.upload_directory)

    def list_files(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        directory = message.text.split(' ')[1]
        try:
            files = os.listdir(directory)
            response = "\n".join(files)
            for chunk in split_message(response):
                self.bot.reply_to(message, chunk)
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def hash_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            file_path = args[1]
            hash_type = args[2].lower()

            if not os.path.exists(file_path):
                self.bot.reply_to(message, "[!] File not found.")
                return

            hash_func = None
            if hash_type == 'md5':
                hash_func = hashlib.md5()
            elif hash_type == 'sha1':
                hash_func = hashlib.sha1()
            elif hash_type == 'sha256':
                hash_func = hashlib.sha256()
            else:
                self.bot.reply_to(message, "[!] Invalid hash type. Use 'md5', 'sha1', or 'sha256'.")
                return

            with open(file_path, 'rb') as f:
                for chunk_data in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk_data)

            self.bot.reply_to(message, f"[+] {hash_type.upper()} hash of {file_path}: {hash_func.hexdigest()}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_file_attributes(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        file_path = message.text.split(' ')[1]
        try:
            file_stats = os.stat(file_path)
            is_read_only = not (file_stats.st_mode & stat.S_IWUSR)
            response = f"""
[+] File Attributes for {file_path}:
- Size: {file_stats.st_size} bytes
- Last Accessed: {time.ctime(file_stats.st_atime)}
- Last Modified: {time.ctime(file_stats.st_mtime)}
- Created: {time.ctime(file_stats.st_ctime)}
- Read-Only: {'Yes' if is_read_only else 'No'}
"""
            self.bot.reply_to(message, response)
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def set_file_attributes(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            file_path = args[1]
            read_only = args[2].lower() == 'true'
            if read_only:
                os.chmod(file_path, stat.S_IREAD)
                self.bot.reply_to(message, f"[+] {file_path} is now read-only.")
            else:
                os.chmod(file_path, stat.S_IWRITE)
                self.bot.reply_to(message, f"[+] {file_path} is now writable.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def encrypt_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            file_path = args[1]
            key = Fernet.generate_key()
            cipher_suite = Fernet(key)

            with open(file_path, 'rb') as f:
                file_data = f.read()

            encrypted_data = cipher_suite.encrypt(file_data)

            with open(file_path, 'wb') as f:
                f.write(encrypted_data)

            self.bot.reply_to(message, f"[+] File {file_path} encrypted. Keep this key to decrypt: {key.decode()}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def decrypt_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            file_path = args[1]
            key = args[2].encode()

            cipher_suite = Fernet(key)

            with open(file_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = cipher_suite.decrypt(encrypted_data)

            with open(file_path, 'wb') as f:
                f.write(decrypted_data)

            self.bot.reply_to(message, f"[+] File {file_path} decrypted.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def lock_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            file_path = message.text.split(' ')[1]
            with open(file_path, 'a') as file:
                msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, os.path.getsize(file_path))
            self.bot.reply_to(message, f"[+] File {file_path} locked.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def unlock_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            file_path = message.text.split(' ')[1]
            with open(file_path, 'a') as file:
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, os.path.getsize(file_path))
            self.bot.reply_to(message, f"[+] File {file_path} unlocked.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def rename_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            old_name = message.text.split(' ')[1]
            new_name = message.text.split(' ')[2]
            os.rename(old_name, new_name)
            self.bot.reply_to(message, f"[+] File renamed from {old_name} to {new_name}.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def list_directories(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        directory = message.text.split(' ')[1]
        try:
            directories = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
            response = "\n".join(directories)
            for chunk in split_message(response):
                self.bot.reply_to(message, chunk)
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_directory_size(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        directory = message.text.split(' ')[1]
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            self.bot.reply_to(message, f"[+] Total size of {directory}: {total_size} bytes.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def check_file_exists(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        file_path = message.text.split(' ')[1]
        if os.path.exists(file_path):
            self.bot.reply_to(message, f"[+] File {file_path} exists.")
        else:
            self.bot.reply_to(message, f"[!] File {file_path} does not exist.")

    def delete_directory(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            directory = message.text.split(' ')[1]
            shutil.rmtree(directory)
            self.bot.reply_to(message, f"[+] Directory {directory} deleted successfully.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def check_if_file_or_directory(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        path = message.text.split(' ')[1]
        if os.path.isdir(path):
            self.bot.reply_to(message, f"[+] {path} is a directory.")
        elif os.path.isfile(path):
            self.bot.reply_to(message, f"[+] {path} is a file.")
        else:
            self.bot.reply_to(message, f"[!] {path} does not exist.")

    def read_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        file_path = message.text.split(' ')[1]
        try:
            with open(file_path, 'r') as file:
                content = file.read()
            for chunk in split_message(content):
                self.bot.reply_to(message, chunk)
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def delete_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        file_path = message.text.split(' ')[1]
        try:
            os.remove(file_path)
            self.bot.reply_to(message, f"[+] File {file_path} deleted.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def zip_files(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            output_zip = args[-1]
            files_to_zip = args[1:-1]
            with zipfile.ZipFile(output_zip, 'w') as zipf:
                for file in files_to_zip:
                    zipf.write(file)
            self.bot.reply_to(message, f"[+] Files zipped successfully into {output_zip}.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def unzip_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            zip_file = args[1]
            extract_to = args[2]
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                zipf.extractall(extract_to)
            self.bot.reply_to(message, f"[+] Files extracted to {extract_to}.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def copy_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            source = args[1]
            destination = args[2]
            shutil.copy(source, destination)
            self.bot.reply_to(message, f"[+] File copied from {source} to {destination}.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def move_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            source = args[1]
            destination = args[2]
            shutil.move(source, destination)
            self.bot.reply_to(message, f"[+] File moved from {source} to {destination}.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def file_info(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        file_path = message.text.split(' ')[1]
        try:
            file_stats = os.stat(file_path)
            response = f"""
[+] File Info for {file_path}:
- Size: {file_stats.st_size} bytes
- Last Accessed: {time.ctime(file_stats.st_atime)}
- Last Modified: {time.ctime(file_stats.st_mtime)}
- Created: {time.ctime(file_stats.st_ctime)}
"""
            self.bot.reply_to(message, response)
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def file_permissions(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        file_path = message.text.split(' ')[1]
        try:
            file_permissions = oct(os.stat(file_path).st_mode)[-3:]
            self.bot.reply_to(message, f"[+] File permissions for {file_path}: {file_permissions}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def change_file_extension(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            old_file = args[1]
            new_extension = args[2]
            base = os.path.splitext(old_file)[0]
            new_file = f"{base}.{new_extension}"
            os.rename(old_file, new_file)
            self.bot.reply_to(message, f"[+] File extension changed from {old_file} to {new_file}.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def ads_write(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            file_path = args[1]
            ads_name = args[2]
            ads_data = ' '.join(args[3:])
            ads_path = f"{file_path}:{ads_name}"
            with open(ads_path, 'w') as ads_file:
                ads_file.write(ads_data)
            self.bot.reply_to(message, f"[+] ADS {ads_name} written successfully to {file_path}.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def ads_read(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split()
            file_path = args[1]
            ads_name = args[2]
            ads_path = f"{file_path}:{ads_name}"
            with open(ads_path, 'r') as ads_file:
                ads_content = ads_file.read()
            self.bot.reply_to(message, f"[+] ADS {ads_name} content: {ads_content}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def upload_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            file_info = self.bot.get_file(message.document.file_id)
            downloaded_file = self.bot.download_file(file_info.file_path)
            save_path = os.path.join(self.upload_directory, message.document.file_name)
            with open(save_path, "wb") as new_file:
                new_file.write(downloaded_file)
            self.bot.reply_to(message, f"[+] File uploaded successfully: {save_path}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def download_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        file_path = message.text.split(' ')[1]
        try:
            with open(file_path, "rb") as file:
                self.bot.send_document(message.from_user.id, file)
            self.bot.reply_to(message, f"[+] File {file_path} sent successfully.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def search_file(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            args = message.text.split(' ')
            filename = args[1]
            directory = args[2]

            result_paths = []
            for root, dirs, files in os.walk(directory):
                if filename in files:
                    result_paths.append(os.path.join(root, filename))

            if result_paths:
                response = "\n".join(result_paths)
                for chunk in split_message(response):
                    self.bot.reply_to(message, chunk)
            else:
                self.bot.reply_to(message, f"[!] File {filename} not found.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")
