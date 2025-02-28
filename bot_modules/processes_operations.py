# bot_modules/processes_operations.py

import psutil
import subprocess
import telebot

def split_message(text, max_length=4096):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

class ProcessesOperations:
    def __init__(self, bot: telebot.TeleBot, verify_telegram_id):
        self.bot = bot
        self.verify_telegram_id = verify_telegram_id

    def list_processes(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            processes = psutil.process_iter(['pid', 'name'])
            response = "\n".join([f"PID: {p.info['pid']}, Name: {p.info['name']}" for p in processes])
            for chunk in split_message(response):
                self.bot.reply_to(message, chunk)
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def suspend_process(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        pid = int(message.text.split(' ')[1])
        try:
            process = psutil.Process(pid)
            process.suspend()
            self.bot.reply_to(message, f"[+] Process {pid} suspended.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def resume_process(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        pid = int(message.text.split(' ')[1])
        try:
            process = psutil.Process(pid)
            process.resume()
            self.bot.reply_to(message, f"[+] Process {pid} resumed.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def kill_process(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        pid = int(message.text.split(' ')[1])
        try:
            process = psutil.Process(pid)
            process.terminate()
            self.bot.reply_to(message, f"[+] Process {pid} terminated.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def start_process(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        process = message.text.split(' ')[1]
        try:
            subprocess.Popen(process)
            self.bot.reply_to(message, f"[+] Process {process} started.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")
