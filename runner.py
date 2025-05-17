from Scanner import scanner
from DB.DBController import DBInterface
import yaml
# admins = scanner.get_computer_admins_windows('WINSERVFYP.FYP.LOC')
#
# interface = DBInterface()
#
# interface.setup_add_computer_admins(admins, "WINSERVFYP.FYP.LOC", "FYP")

# def setup():
#     # Initial setup for users and computers
#     scanner.add_computers()
#     scanner.add_users()
#
#     # Gets the admins already on the computer and adds them to the authorised admins list
#     interface.setup_add_computer_admins(admins, "WINSERVFYP.FYP.LOC", "FYP")

def load_config():
    with open("domain_config.yaml", "r") as config_file:
        ad_config = yaml.safe_load(config_file)
    return ad_config


def main_loop():
    """
    Steps:
    1) Get all AD Users
    2) Get all AD Computers
    3) Get Admins
    4) Add and Remove as applicable
    """
    ad_config = load_config()

    scanner.add_users() # Step 1
    scanner.add_computers() # Step 2

    # Step 3

    # Get all computers
    interface = DBInterface()
    db_computers = interface.get_all_database_computers()
    # Get admin list for each computer
    for computer in db_computers:
        # Get admin list from computer itself (windows)
        if "Windows" in computer[1]:
            admins_from_computer = scanner.get_computer_admins_windows(computer[0])
        else:
            # TODO Linux check
            continue
        if not admins_from_computer:
            continue
        # Get admin list from db
        admins_from_db = interface.get_computer_admins(computer[0])
        print(f"Computer: {computer}\nAdmin List (Windows): {admins_from_computer}\nAdmin List (DB): {admins_from_db}")

        # Convert admin from windows to IDs
        admins_from_computer_database_ids = []
        for admin in admins_from_computer:
            if admin[:3] == ad_config["DomainNetBIOSName"]:
                tmp = admin.split("\\")[-1]
                admin_user_id = interface.get_user_id(tmp)
                admins_from_computer_database_ids.append(admin_user_id)
            else:
                # If the account is a local account then it will be added using its FQDN as it will not have a database ID
                admins_from_computer_database_ids.append(admin)
        print(f"Admin List ID (Database from Windows): {admins_from_computer_database_ids}")
        # Compare lists
        for user in admins_from_computer_database_ids:
            # User should be in the admin list, no issue
            if user in admins_from_db:
                print(f"User {user} is a valid admin")
            else:
                print(f"User {user} is not a valid admin")
                # remove invalid admin from target
                user_name_from_id = interface.get_user_from_id(user)
                if not user_name_from_id: # Likely means it is a local account and therefore the account name is the same as the ID
                    user_name_from_id = user
                scanner.remove_admin_windows(computer[0], user_name_from_id)
                if scanner.check_admin_removed(computer[0], user_name_from_id):
                    print(f"Admin {user} successfully removed")
                else:
                    print(f"Admin {user} unsuccessfully removed")

# test

if __name__ == '__main__':
    # main_loop()
    # sudoers = scanner.get_computer_admins_linux("LINSERVFYP.FYP.LOC")
    # print(sudoers)
    # result = scanner.add_sudoer_linux("LINSERVFYP.FYP.LOC", "basic@FYP.LOC")
    # print(result)
    # sudoers = scanner.get_computer_admins_linux("LINSERVFYP.FYP.LOC")
    # print(sudoers)
    result = scanner.remove_sudoer_linux("LINSERVFYP.FYP.LOC", "basic@FYP.LOC")
    print(result)