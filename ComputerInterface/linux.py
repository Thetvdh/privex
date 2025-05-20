import socket

import paramiko
import gssapi
import yaml
import subprocess
import logging

from paramiko.ssh_exception import NoValidConnectionsError

def load_config():
    with open("domain_config.yaml", "r") as config_file:
        ad_config = yaml.safe_load(config_file)
    return ad_config

logging.basicConfig(
    level=logging.INFO,
    filename="linux_utils.log",
    encoding="utf-8",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S",
)

# sudo /usr/bin/gpasswd -a user group
# sudo /usr/bin/gpasswd --delete user group
# domain has to be capitalised
class LinuxWorker:

    def __init__(self):
        self.AD_CONFIG = load_config()
        self.user_name = self.AD_CONFIG['WorkerUsername']
        self.password = self.AD_CONFIG["WorkerPassword"]
        self.net_bios = self.AD_CONFIG["DomainNetBIOSName"]

    def get_kerberos_ticket(self):
        try:
            klist_cmd = "klist"
            output = subprocess.run(klist_cmd, shell=True, check=True, executable="/bin/bash", stdout=subprocess.DEVNULL)
            if output.returncode == 0:
                logging.info("Kerberos ticket already valid")
                return True
        except subprocess.CalledProcessError as e:
            logging.error("Failed to check status of Kerberos Ticket")
        try:
            kinit_cmd = f"echo '{self.password}' | kinit {self.user_name}@{self.AD_CONFIG['DomainDNSName']}"
            subprocess.run(kinit_cmd, shell=True, check=True, executable="/bin/bash", stdout=subprocess.DEVNULL)
            logging.info("Successfully got Kerberos Ticket")
        except subprocess.CalledProcessError as e:
            logging.error("Failed to obtain Kerberos Ticket")
            return False
        return True

    def establish_connection(self, computer_name):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        username = f"{self.user_name}@{self.AD_CONFIG['DomainDNSName']}"
        computer = computer_name.lower()
        # print(username, computer, self.password)
        try:
            client.connect(
                hostname=computer,
                username=username,
                password=self.password
            )
        except NoValidConnectionsError as err:
            logging.error(err)
            print("Failed to establish connection to computer", err)
            return False
        except socket.gaierror as err:
            logging.error(err)
            print("Failed to establish connection to computer", err)
            return False
        return client
    def close_connection(self, client):
        client.close()

    # user_name in format username@domain
    def add_to_sudo(self, client, user_name):
        print(f"[DEBUG] Attempting to add {user_name} to sudo")
        stdin, stdout, stderr = client.exec_command(f'sudo /usr/bin/gpasswd -a {user_name} sudo')
        print(stdout.read())
        print(stderr.read())
        stdin.close()
        stdout.close()
        stderr.close()
        return True

    def remove_from_sudo(self, client, user_name):
        stdin, stdout, stderr = client.exec_command(f'sudo /usr/bin/gpasswd --delete {user_name} sudo')
        print(stdout.read())
        stdin.close()
        stdout.close()
        stderr.close()

    def check_added_to_sudo(self, client, user_name):
        stdin, stdout, stderr = client.exec_command(f'getent group sudo')
        result = stdout.read()
        print(f"[DEBUG] {result}")
        if user_name in result.decode():
            stdin.close()
            stdout.close()
            stderr.close()
            return True
        else:
            stdin.close()
            stdout.close()
            stderr.close()
            return False
    def check_removed_from_sudo(self, client, user_name):
        stdin, stdout, stderr = client.exec_command(f'getent group sudo')
        result = stdout.read()
        print(f"[DEBUG] {result}")
        if user_name not in result.decode():
            stdin.close()
            stdout.close()
            stderr.close()
            return True
        else:
            stdin.close()
            stdout.close()
            stderr.close()
            return False
    def get_all_admins(self, client) -> list:
        stdin, stdout, stderr = client.exec_command(f'getent group sudo')
        sudoers = stdout.read().decode().split(":")[-1].split(",")
        sanitised_sudoers = [i.strip() for i in sudoers]
        return sanitised_sudoers

    def terminate_linux_session(self, client, username):
        command = "ps -ef | grep sshd | grep -E %s | grep -v priv | awk '{print $2}'" % username
        print(f"[DEBUG] {command}")
        stdin, stdout, stderr = client.exec_command(command)
        result = stdout.read() # should be PID
        clean_result = result.decode().strip()
        print("[DEBUG]", clean_result)
        kill_command = f"sudo kill {clean_result}"
        stdin, stdout, stderr = client.exec_command(kill_command)
        result = stdout.read()
        print("[DEBUG]", result)
        return True

