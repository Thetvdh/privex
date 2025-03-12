from DB.DBController import DBInterface
from ADScripts.GetADInformation import LDAPController

database = DBInterface()
ldap_controller = LDAPController()

def get_computers():
    computers = ldap_controller.get_ad_computers()
    return computers


def add_computers():
    computers = get_computers()
    for computer in computers:
        if not database.add_computer(computer):
            print(f"Failed to add computer {computer['FQDN']}")


def get_users():
    users = ldap_controller.get_ad_users()
    return users

def add_users():
    users = get_users()
    for user in users:
        if not database.add_user(user):
            print(f"Failed to add user {user['samAccountName']}")

add_users()