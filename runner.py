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

    print("Adding users to Database")
    scanner.add_users() # Step 1
    print("Adding computers to Database")
    scanner.add_computers() # Step 2

    # Step 3

    # Get all computers
    interface = DBInterface()
    print("Getting DB computers")
    db_computers = interface.get_all_database_computers()
    print(db_computers)
    # Get admin list for each computer
    for computer in db_computers:
        # Get admin list from computer itself (windows)
        if "Windows" in computer[1]:
            print(f"Getting windows admins from {computer[0]}")
            admins_from_computer = scanner.get_computer_admins_windows(computer[0])
            print(admins_from_computer)
        else:
            print(f"Getting Linux admins from {computer[0]}")
            admins_from_computer = scanner.get_computer_admins_linux(computer[0])
            print(admins_from_computer)
        if not admins_from_computer:
            continue
        # Get admin list from db
        print("Getting admins from DB")
        admins_from_db = interface.get_computer_admins(computer[0])
        print(f"Computer: {computer}\nAdmin List: {admins_from_computer}\nAdmin List (DB): {admins_from_db}")

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
                if "windows" in computer[1].lower():
                    scanner.remove_admin_windows(computer[0], user_name_from_id)
                    if scanner.check_admin_removed_windows(computer[0], user_name_from_id):
                        print(f"Admin {user} successfully removed")
                    else:
                        print(f"Admin {user} unsuccessfully removed")
                elif "linux" in computer[1].lower():
                    scanner.remove_sudoer_linux(computer[0], user_name_from_id)
                    if scanner.check_admin_removed_linux(computer[0], user_name_from_id):
                        print(f"Admin {user} successfully removed")
                    else:
                        print(f"Admin {user} not removed")
                else:
                    print(f"Unknown OS for computer {computer[0]} {computer[1]}")

# test

def cli():
    print("1) Add admin")
    print("2) Remove admin")
    print("3) List admins")
    print("4) Exit")

    choice = input("Enter your choice: ")
    while choice not in ["1", "2", "3", "4"]:
        choice = input("Enter your choice: ")
    if choice == "4":
        exit()
    if choice == "1":
        computer_name = input("Enter computer name: ")
        computer_info = scanner.get_computer_info(computer_name)
        computer_os = computer_info[2]
        print(computer_os)
        username = input("Enter username in format DOMAIN\\\\USERNAME: ")
        if "windows" in computer_os.lower():
            if scanner.add_admin_windows(computer_name, username):
                print(f"Successfully added {username} to {computer_name}")
            else:
                print(f"Failed to add {username} to {computer_name}")
        elif "linux" in computer_os.lower():
            if scanner.add_sudoer_linux(computer_name, username):
                print(f"Successfully added {username} to {computer_name}")
            else:
                print(f"Failed to add {username} to {computer_name}")
        else:
            print(f"Failed to add {username} to {computer_name} due to unrecognised Operating System {computer_os}")
    elif choice == "2":
        computer_name = input("Enter computer name: ")
        computer_info = scanner.get_computer_info(computer_name)
        computer_os = computer_info[2]
        print(computer_os)
        username = input("Enter username in format DOMAIN\\\\USERNAME: ")
        if "windows" in computer_os.lower():
            if scanner.remove_admin_windows(computer_name, username):
                print(f"Successfully removed {username} from {computer_name}")
            else:
                print(f"Failed to remove {username} from {computer_name}")
        elif "linux" in computer_os.lower():
            if scanner.remove_sudoer_linux(computer_name, username):
                print(f"Successfully removed {username} from {computer_name}")
            else:
                print(f"Failed to remove {username} from {computer_name}")
        else:
            print(f"Failed to remove {username} from {computer_name} due to unrecognised Operating System {computer_os}")
    elif choice == "3":
        computer_name = input("Enter computer name: ")
        computer_info = scanner.get_computer_info(computer_name)
        computer_os = computer_info[2]
        print(computer_os)
        if "windows" in computer_os.lower():
            admins = scanner.get_computer_admins_windows(computer_name)
            if admins:
                print(f"Admins on {computer_name}", ", ".join(admins))
            else:
                print("Unable to get admins from computer")
        elif "linux" in computer_os.lower():
            admins = scanner.get_computer_admins_linux(computer_name)
            if admins:
                print(f"Admins on {computer_name}", ", ".join(admins))
            else:
                print("Unable to get admins from computer")

def setup():
    computers = scanner.get_computers()
    interface = DBInterface()
    for computer in computers:
        if "windows" in computer["operating_system"].lower():
            admins = scanner.get_computer_admins_windows(computer["FQDN"])
            interface.setup_add_computer_admins(admins, computer["FQDN"].upper(), "FYP")
            print(f"Added {admins} to {computer['FQDN']}")
        elif "linux" in computer["operating_system"].lower():
            admins = scanner.get_computer_admins_linux(computer["FQDN"])
            interface.setup_add_computer_admins(admins, computer["FQDN"].upper(), "FYP")
            print(f"Added {admins} to {computer['FQDN']}")
        else:
            print(f"Invalid OS on {computer['FQDN']}")

if __name__ == '__main__':
    # cli()
    # setup()
    main_loop()
    # sudoers = scanner.get_computer_admins_linux("LINSERVFYP.FYP.LOC")
    # print(sudoers)
    # result = scanner.add_sudoer_linux("LINSERVFYP.FYP.LOC", "basic@FYP.LOC")
    # print(result)
    # sudoers = scanner.get_computer_admins_linux("LINSERVFYP.FYP.LOC")
    # print(sudoers)
    # result = scanner.remove_sudoer_linux("LINSERVFYP.FYP.LOC", "basic@FYP.LOC")
    # print(result)