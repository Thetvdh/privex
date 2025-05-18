import requests
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

class WindowsWorker:
    def __init__(self):
        self.AD_CONFIG = load_config()
        self.user_name = self.AD_CONFIG['WorkerUsername']
        self.password = self.AD_CONFIG["WorkerPassword"]
        self.net_bios = self.AD_CONFIG["DomainNetBIOSName"]

    # Gets a kerberos ticket for the worker account. Ticket is needed in order for WinRM to work as kerberos transport
    # requires it. Needs to be generated with kinit hence use of subprocess
    def get_kerberos_ticket(self) -> bool:
        """

        :rtype: bool
        :return: 
        """
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


    # returns a WinRM session for the specified computer
    def establish_winrm_session(self, computer_fqdn) -> winrm.Session | bool:
        """

        :rtype: Session | bool
        :param computer_fqdn: 
        :return: 
        """
        if self.get_kerberos_ticket():
            user_with_principal = f"{self.user_name}@{self.AD_CONFIG['DomainDNSName']}" # @principal is required for transport to work correctly
            return winrm.Session(computer_fqdn, auth=(user_with_principal, self.password), transport="kerberos", server_cert_validation="ignore")
        else:
            logging.error("Failed to get Kerberos ticket")
            return False

    # returns a list of admins in the format NETBIOS\\samAccountName
    # It gets both domain users and locally added / created users
    def get_computer_administrators(self, session) -> list:
        """

        :rtype: list
        :param session: 
        :return: 
        """
        try:
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
        except requests.exceptions.ConnectTimeout as e:
            logging.error(e)
            return []
        except requests.exceptions.ConnectionError as e:
            logging.error(e)
            return []
    def add_windows_admin(self, session, username) -> bool:
        try:
            ps_script_add_administrator = f"""
            Add-LocalGroupMember -Group "Administrators" -Member {username}
            """
            response = session.run_ps(ps_script_add_administrator)
            if response.status_code == 0:
                logging.info(f"Successfully added {username} from Administrators group")
                return True
            else:
                logging.warning(f"Failed to add {username} from Administrators group, this could be as they were already present in the group")
                return False
        except requests.exceptions.ConnectTimeout as e:
            logging.error(e)
            return False
        except requests.exceptions.ConnectionError as e:
            logging.error(e)
            return False
    def remove_windows_admin(self, session, username) -> bool:
        """

        :rtype: bool
        :param session: 
        :param username: 
        :return: 
        """
        try:
            ps_script_add_administrator = f"""
            Remove-LocalGroupMember -Group "Administrators" -Member {username}
            """
            response = session.run_ps(ps_script_add_administrator)
            if response.status_code == 0:
                logging.info(f"Successfully removed {username} from Administrators group")
                return True
            else:
                logging.warning(f"Failed to remove {username} from Administrators group, this could be because they did not exist in the group")
                return False
        except requests.exceptions.ConnectTimeout as e:
            logging.error(e)
            return False
        except requests.exceptions.ConnectionError as e:
            logging.error(e)
            return False

    def check_admin_removed(self, session, username) -> bool:
        """

        :rtype: bool
        :param session: 
        :param username: 
        :return: 
        """
        admins = self.get_computer_administrators(session)
        print(f"Username: {username}\nAdmins: {admins}")
        if username not in admins:
            return True
        return False