from ComputerInterface.windows import WindowsWorker
from DB.DBController import DBInterface
from ADScripts.GetADInformation import LDAPController
from ComputerInterface import windows
import logging

logging.basicConfig(
    filename="scanner.log",
    encoding="utf-8",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S",
)


database = DBInterface()
ldap_controller = LDAPController()

def get_computers():
    computers = ldap_controller.get_ad_computers()
    return computers

# Function to add computers in AD to the local database
def add_computers():
    computers = get_computers()
    for computer in computers:
        if database.check_unique_computer_sid(computer["objectSid"]):
            logging.info(f"Computer {computer['FQDN']} already exists")
            continue
        if not database.add_computer(computer):
            logging.error(f"Failed to add computer {computer['FQDN']}")


def get_users():
    users = ldap_controller.get_ad_users()
    return users

def add_users():
    users = get_users()
    for user in users:
        if database.check_unique_user_sid(user["objectSid"]):
            logging.info(f"User {user['samAccountName']} already exists")
            continue
        if not database.add_user(user):
            logging.info(f"Failed to add user {user['samAccountName']}")

def get_computer_admins_windows(computer_fqdn):
    win_interface = WindowsWorker()
    session = win_interface.establish_winrm_session(computer_fqdn)
    return win_interface.get_computer_administrators(session)


