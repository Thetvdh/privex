import winrm
import yaml
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    filename="windows_utils.log",
    encoding="utf-8",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S",
)

def load_config():
    with open("domain_config.yaml", "r") as config_file:
        ad_config = yaml.safe_load(config_file)
    return ad_config

# TODO Fix, research SPNs
class WindowsWorker:
    def __init__(self):
        self.AD_CONFIG = load_config()
        self.user_name = self.AD_CONFIG['WorkerUsername']
        self.password = self.AD_CONFIG["WorkerPassword"]
    def get_kerberos_ticket(self):
        try:
            kinit_cmd = f"echo '{self.password}' | kinit {self.user_name}@FYP.LOC"
            subprocess.run(kinit_cmd, shell=True, check=True, executable="/bin/bash")
            logging.info("Successfully got Kerberos Ticket")
        except subprocess.CalledProcessError as e:
            logging.error(e)
            return False
        return True
    def debug(self):
        result = subprocess.run("klist", shell=True, check=True, executable="/bin/bash")

    def establish_winrm_session(self, computer_fqdn):
        self.get_kerberos_ticket()
        self.debug()
        user_with_principal = f"{self.user_name}@FYP.LOC"
        return winrm.Session(computer_fqdn, auth=(user_with_principal, self.password), transport="kerberos", server_cert_validation="ignore")

    def get_computer_administrators(self, session):
        ps_script_get_administrators = """
        Get-LocalGroupMember -Name "Administrators" | Where-Object { $_.ObjectClass -eq 'User' } | Select-Object -ExpandProperty Name
        """
        response = session.run_ps(ps_script_get_administrators)
        admins = response.std_out.decode()
        admin_list = admins.split("\r\n")
        clean_admin_list = []
        for admin in admin_list:
            admin = admin.strip()
            if admin:
                clean_admin_list.append(admin)
        return clean_admin_list