import datetime

from ldap3.operation.compare import compare_response_to_dict

from ComputerInterface.linux import LinuxWorker
from ComputerInterface.windows import WindowsWorker
from DB import database
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




ldap_controller = LDAPController()




def get_computers():
    if not ldap_controller.conn:
        print("Unable to get ldap controller connection")
        logging.error("Unable to get ldap controller connection")
        return []
    computers = ldap_controller.get_ad_computers()
    return computers

# Function to add computers in AD to the local database
def add_computers():
    computers = get_computers()
    for computer in computers:
        if database.check_unique_computer_sid(computer.get("objectSid")):
            logging.info(f"Computer {computer['FQDN']} already exists")
            continue
        if not database.add_computer(computer):
            logging.error(f"Failed to add computer {computer.get('FQDN')}")


def get_users():
    if not ldap_controller.conn:
        print("Unable to get ldap controller connection")
        logging.error("Unable to get ldap controller connection")
        return []
    users = ldap_controller.get_ad_users()
    return users

def add_users():
    users = get_users()
    for user in users:
        if database.check_unique_user_sid(user.get("objectSid")):
            logging.info(f"User {user['samAccountName']} already exists")
            continue
        if not database.add_user(user):
            logging.info(f"Failed to add user {user['samAccountName']}")

def get_computer_admins_windows(computer_fqdn) -> list:
    win_interface = WindowsWorker()
    session = win_interface.establish_winrm_session(computer_fqdn)
    return win_interface.get_computer_administrators(session)

# adds an administrator to the specified Windows computer
def add_admin_windows(computer_fqdn, username) -> bool:
    # add code to check if user exists
    win_interface = WindowsWorker()
    session = win_interface.establish_winrm_session(computer_fqdn)
    if session:
        return win_interface.add_windows_admin(session, username)
    else:
        logging.error("Unable to add admin due to missing session")
        return False

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

def check_admin_removed_linux(computer_fqdn, username):
    linux_interface = LinuxWorker()
    client = linux_interface.establish_connection(computer_fqdn)
    if client:
        removed = linux_interface.check_removed_from_sudo(client, username)
        if removed:
            logging.info(f"Admin {username} removed")
            print(f"Admin {username} removed")
            return True
        else:
            logging.error(f"Unable to remove {username} from sudo")
            print(f"Unable to remove {username} from sudo")
            return False
    else:
        logging.error(f"Unable to connect to {computer_fqdn}")
        return False


def get_computer_admins_linux(computer_fqdn) -> list:
    """
    Gets a list of all admins on a linux computer, not database
    :rtype: list
    :param computer_fqdn: 
    :return: 
    """
    linux_interface = LinuxWorker()
    client = linux_interface.establish_connection(computer_fqdn)
    if client:
        return linux_interface.get_all_admins(client)
    else:
        return []

def add_admin_database(computer_fqdn, username) -> bool:
    database.add_user_to_admin(username, computer_fqdn)


def add_sudoer_linux(computer_fqdn, username):
    """
    Adds sudoer to Linux computer, not database
    :param computer_fqdn:
    :param username:
    :return:
    """
    linux_interface = LinuxWorker()
    session = linux_interface.establish_connection(computer_fqdn)
    if session:
        linux_interface.add_to_sudo(session, username)
        if linux_interface.check_added_to_sudo(session, username):
            logging.info(f"Added user {username} successfully to {computer_fqdn}")
            return True

def remove_sudoer_linux(computer_fqdn, username):
    """
    Removes sudoer from Linux computer, not database
    :param computer_fqdn: 
    :param username: 
    :return: 
    """
    linux_interface = LinuxWorker()
    session = linux_interface.establish_connection(computer_fqdn)
    if session:
        linux_interface.remove_from_sudo(session, username)
        return linux_interface.check_removed_from_sudo(session, username)

def get_computer_info(computer_fqdn) -> bool | tuple:
    return database.get_computer_info(computer_fqdn)

def create_session(computer_fqdn, username, reason) -> str:
    """
    Function to create session on a domain computer
    1) Check user is permitted to elevate permissions on that computer
    2) Check computer OS
    3) Add user
    4) Add session to database if useradd is successful
    5) Return message to display to user
    :param computer_fqdn:
    :param username:
    :param reason:
    :return:
    """
    print("[DEBUG] Attempting to create session")
    admins = database.get_computer_admins(computer_fqdn)
    if not admins:
        return "Failed to create session due to database error"
    admins_dict = dict(admins)
    print(admins_dict.keys())

    user_id = database.get_user_id(username)

    if user_id not in admins_dict.keys():
        return f"Insufficient permissions to create session for user {username}"

    computer_info = get_computer_info(computer_fqdn)
    if "windows" in computer_info[2].lower():
        add_admin_windows(computer_fqdn, username)
    elif "linux" in computer_info[2].lower():
        add_sudoer_linux(computer_fqdn, username)
    else:
        return f"Failed to create session due to invalid OS for computer {computer_fqdn}"

    result = database.create_session_db(computer_fqdn, username, reason)
    if not result:
        return "Failed to create session due to database error"
    return f"Successfully created session for user {username} on computer {computer_fqdn}"


def check_session_validity_computer(computer_fqdn, username):
    sessions = database.get_non_expired_sessions_by_computer_and_user(computer_fqdn, username)
    if not sessions:
        return False  # Returns false as no valid session exists for that user
    any_expired = False
    for session in sessions:
        expiry_time = datetime.datetime.strptime(session[4], "%Y-%m-%d %H:%M:%S.%f")
        # If any have expired and there are multiple then all sessions need expiring. Should be 1 session per user per computer
        if expiry_time < datetime.datetime.now() or any_expired:
            any_expired = True
            database.expire_session(session[0])  # Expires the session

    return not any_expired
