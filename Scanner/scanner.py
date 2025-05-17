from ComputerInterface.linux import LinuxWorker
from ComputerInterface.windows import WindowsWorker
from DB.DBController import DBInterface
from ADScripts.GetADInformation import LDAPController
import logging

"""
scanner.py contains wrapper functions for other packages. The scanner will be run as a cronjob which will periodically
run the relevant functions as outlined in the scanner flowchart. Scanner will not run from scanner.py instead a wrapper
Python file

Scanner will perform the following functions:

1) Query all domain users, add any new users into the database
2) Query all domain computers, add any new computers into the database
3) Loop through domain computers
4) Worker connects to each computer in turn and queries the admin group
5) Members of admin group on the computer is compared to the authorised admin list in the database
6) Worker will add / remove admins as needed
"""

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

# adds an administrator to the specified Windows computer
def add_admin_windows(computer_fqdn, username):
    # add code to check if user exists
    win_interface = WindowsWorker()
    session = win_interface.establish_winrm_session(computer_fqdn)
    if session:
        return win_interface.add_windows_admin(session, username)
    else:
        logging.error("Unable to add admin due to missing session")

def remove_admin_windows(computer_fqdn, username):
    win_interface = WindowsWorker()
    session = win_interface.establish_winrm_session(computer_fqdn)
    if session:
        return win_interface.remove_windows_admin(session, username)
    else:
        logging.error("Unable to remove admin due to missing session")

def check_admin_removed_windows(computer_fqdn, username):
    win_interface = WindowsWorker()
    session = win_interface.establish_winrm_session(computer_fqdn)
    if session:
        return win_interface.check_admin_removed(session, username)
    else:
        logging.error("Unable to check admin removal due to missing session")

def get_computer_admins_linux(computer_fqdn):
    linux_interface = LinuxWorker()
    client = linux_interface.establish_connection(computer_fqdn)
    if client:
        return linux_interface.get_all_admins(client)

def add_sudoer_linux(computer_fqdn, username):
    linux_interface = LinuxWorker()
    session = linux_interface.establish_connection(computer_fqdn)
    if session:
        linux_interface.add_to_sudo(session, username)
        return linux_interface.check_added_to_sudo(session, username)

def remove_sudoer_linux(computer_fqdn, username):
    linux_interface = LinuxWorker()
    session = linux_interface.establish_connection(computer_fqdn)
    if session:
        linux_interface.remove_from_sudo(session, username)
        return linux_interface.check_removed_from_sudo(session, username)