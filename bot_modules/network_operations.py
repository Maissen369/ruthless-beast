# bot_modules/network_operations.py

import socket
import requests
import telebot
import logging
import subprocess
import uuid
import netifaces
import psutil

logger = logging.getLogger(__name__)

def split_message(text, max_length=4096):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

class NetworkOperations:
    def __init__(self, bot: telebot.TeleBot, verify_telegram_id):
        self.bot = bot
        self.verify_telegram_id = verify_telegram_id

    def get_public_ip(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=10)
            public_ip = response.json()['ip']
            self.bot.reply_to(message, f"[+] Public IP Address: {public_ip}")
            logger.info(f"Public IP Address sent: {public_ip}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_local_ip(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            self.bot.reply_to(message, f"[+] Local IP Address: {local_ip}")
            logger.info(f"Local IP Address sent: {local_ip}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_hostname(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            hostname = socket.gethostname()
            self.bot.reply_to(message, f"[+] Hostname: {hostname}")
            logger.info(f"Hostname sent: {hostname}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_mac_address(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            mac_num = hex(uuid.getnode()).replace('0x', '').upper()
            mac = ':'.join(mac_num[i:i+2] for i in range(0, 11, 2))
            self.bot.reply_to(message, f"[+] MAC Address: {mac}")
            logger.info(f"MAC Address sent: {mac}")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_adapter_list(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            adapters = netifaces.interfaces()
            response = "\n".join(adapters)
            for chunk in split_message(response):
                self.bot.reply_to(message, chunk)
            logger.info("Network adapters list sent.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def scan_for_open_ports(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            target_ip = socket.gethostbyname(socket.gethostname())
            open_ports = []
            # Example scanning range 1-1024
            for port in range(1, 1025):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((target_ip, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            if open_ports:
                response = "Open Ports:\n" + "\n".join(map(str, open_ports))
            else:
                response = "No open ports found in the range 1-1024."
            for chunk in split_message(response):
                self.bot.reply_to(message, chunk)
            logger.info("Port scan completed and results sent.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_routing_table(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            routing_table = subprocess.check_output("netstat -r", shell=True).decode()
            for chunk in split_message(routing_table):
                self.bot.reply_to(message, chunk)
            logger.info("Routing table sent.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_arp_table(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            arp_table = subprocess.check_output("arp -a", shell=True).decode()
            for chunk in split_message(arp_table):
                self.bot.reply_to(message, chunk)
            logger.info("ARP table sent.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")

    def get_dns_address(self, message):
        if not self.verify_telegram_id(message.from_user.id):
            return
        try:
            dns_address = subprocess.check_output("nslookup", shell=True).decode()
            for chunk in split_message(dns_address):
                self.bot.reply_to(message, chunk)
            logger.info("DNS address information sent.")
        except Exception as e:
            self.bot.reply_to(message, f"[!] Error: {str(e)}")
