import hashlib
import secrets
import sqlite3
import uuid
import logging
import yaml
import datetime

logging.basicConfig(
    level=logging.INFO,
    filename="database.log",
    encoding="utf-8",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S",
)
"""
DBConnector class. Functions to connect to the database.
Intended to be used as a parent class
"""
class DBConnector:
    def __init__(self):
        self.name = f"DB/privex.db"
        self.connection = None
        self.cursor = None
        self.establish_connection()

    # Attempts SQLite database connection
    def establish_connection(self):
        try:
            self.connection = sqlite3.connect(self.name, check_same_thread=False)
            self.cursor = self.connection.cursor()
        except sqlite3.DatabaseError as error:
            logging.error(f"{error}")

    def close_connection(self):
        if self.connection is not None:
            self.connection.close()

"""
DBInterface class

All activities involving the database are contained within this class. This class should be the only class making
requests to and from the SQLite Database
"""
class DBInterface(DBConnector):
    def __init__(self):
        super().__init__()
        with open("app_settings.yaml", "r") as yamlfile:
            self.app_config = yaml.safe_load(yamlfile)

    # Adds a single computer to the database
    def add_computer(self, computer: dict):
        # UUIDs are generated and then added to the database as a unique identifier for each computer
        computer_id = uuid.uuid4().hex
        while self.check_unique_computer_id(computer_id):
            computer_id = uuid.uuid4().hex
        computer["computer_id"] = computer_id
        try:
            sql = """
            INSERT INTO computers (computer_id, computer_name, objectSid, ip_addr, operating_system) VALUES (?, ?, ?, ?, ?)
            """ # SQL adds computer to the DB
            self.cursor.execute(sql, (computer["computer_id"], computer["FQDN"].upper(), computer["objectSid"], computer["ip_addr"], computer["operating_system"]))
            self.connection.commit()
            logging.info("Successfully added computer")
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            return False

    # Function to add a single user to the database
    def add_user(self, user: dict):
        user_id = uuid.uuid4().hex
        while self.check_unique_user_id(user_id):
            user_id = uuid.uuid4()
        user["user_id"] = user_id
        try:
            sql = """
            INSERT INTO ad_users (user_id, samAccountName, objectSid) VALUES (?, ?, ?)
            """
            self.cursor.execute(sql, (user["user_id"], user["samAccountName"], user["objectSid"]))
            self.connection.commit()
            logging.info(f"Successfully added {user['samAccountName']}")
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            return False

    def get_all_database_computers(self) -> list:
        try:
            sql = """
            SELECT computer_name, operating_system FROM computers
            """
            self.cursor.execute(sql)
            computers = self.cursor.fetchall()
            if computers is None:
                return []
            return computers
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            return []
    # Checks if the UUID generated is already in the database, returns False if the computer ID is not in the database
    def check_unique_computer_id(self, computer_id):
        sql = """
        SELECT computer_id FROM computers WHERE computer_id = ?
        """
        self.cursor.execute(sql, [computer_id])
        data = self.cursor.fetchone()
        if data is None:
            return False
        else:
            return True
    # Checks if the UUID generated is already in the database, returns False if the user ID is not in the database

    def check_unique_user_id(self, user_id):
        sql = """
        SELECT user_id FROM ad_users WHERE user_id = ?
        """
        self.cursor.execute(sql, [user_id])
        data = self.cursor.fetchone()
        if data is None:
            return False
        else:
            return True

    # Returns true if the computer is already in the database
    def check_unique_computer_sid(self, computer_sid):
        sql = """
        SELECT objectSid FROM computers WHERE objectSid = ?
        """
        self.cursor.execute(sql, [computer_sid])
        data = self.cursor.fetchone()
        if data is None:
            return False
        else:
            return True

    # returns true if the SID is not unique
    def check_unique_user_sid(self, user_sid):
        sql = """
        SELECT objectSid FROM ad_users WHERE objectSid = ?
        """
        self.cursor.execute(sql, [user_sid])
        data = self.cursor.fetchone()
        if data is None:
            return False
        else:
            return True

    # requests the computer ID from the database based off the FQDN
    def get_computer_id(self, computer_name) -> bool | str:
        sql = """
        SELECT computer_id FROM computers WHERE computer_name = ?
        """
        self.cursor.execute(sql, [computer_name])
        data = self.cursor.fetchone()
        if data is None:
            print("Computer not found")
            logging.warning("Unable to find computer")
            return False
        return data[0]

    # requests the user ID from the database based off the samAccountName
    def get_user_id(self, samAccountName):
        sql = """
        SELECT user_id FROM ad_users WHERE samAccountName = ?
        """
        self.cursor.execute(sql, [samAccountName])
        data = self.cursor.fetchone()
        if data is None:
            print("Unable to find user")
            logging.warning("Unable to find user")
            return False
        return data[0]

    def get_user_from_id(self, user_id):
        sql = """
        SELECT samAccountName from ad_users WHERE user_id = ?
        """
        self.cursor.execute(sql, [user_id])
        data = self.cursor.fetchone()
        if data is None:
            print("Unable to find user")
            logging.warning("Unable to find user")
            return False
        return data[0]


    # NOTE: This function should only be run during setup when it has been checked that only authorised admins are on the computer
    # All admins added via this function will be persistent
    def setup_add_computer_admins(self, admin_list, computer_name, domain_netbios):
        computer_id = self.get_computer_id(computer_name)
        persistent = True
        sql = """
        INSERT INTO authorised_admins (computer_id, user_id, persistent, domain) VALUES (?, ?, ?, ?)
        """
        for admin in admin_list:
            try:
                # Check to see if the account is a domain account or a local account.
                # It is important to distinct this as the domain administrator has the same name as all local administrators
                if admin[:3] == domain_netbios:
                    tmp = admin.split("\\")[-1]
                    admin_user_id = self.get_user_id(tmp)
                    domain_account = True
                    self.cursor.execute(sql, (computer_id, admin_user_id, persistent, domain_account))
                    self.connection.commit()
                    logging.info("Successfully added admin")
                    print("Successfully added admin")
                    return True
                else:
                    domain_account = False
                    admin_user_id = admin # Test how this works with removal from admins
                    self.cursor.execute(sql, (computer_id, admin_user_id, persistent, domain_account))
                    self.connection.commit()
                    logging.info("Successfully added admin")
                    print("Successfully added admin")
                    return True
            except sqlite3.OperationalError as error:
                logging.error(f"{error}")
                return False
        return False

    def add_user_to_admin(self, user_name, computer_name, domain_netbios, persistent=False):
        computer_id = self.get_computer_id(computer_name)
        if not computer_id:
            logging.warning("Unable to find computer")
            print(f"unable to find computer {computer_name}")
            return False
        sql = """
        INSERT INTO authorised_admins (computer_id, user_id, persistent, domain) VALUES (?, ?, ?, ?)
        """
        print(user_name, computer_name, domain_netbios)
        try:
            if user_name[:3] == domain_netbios:
                tmp = user_name.split("\\")[-1]
                user_user_id = self.get_user_id(tmp)
                domain_account = True
                self.cursor.execute(sql, (computer_id, user_user_id, persistent, domain_account))
                self.connection.commit()
                logging.info("Successfully added admin")
                print("Successfully added admin")
                return True
            else:
                domain_account = False
                user_user_id = user_name
                self.cursor.execute(sql, (computer_id, user_user_id, persistent, domain_account))
                self.connection.commit()
                logging.info("Successfully added admin")
                print("Successfully added local admin")
                return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            return False

    def remove_user_from_admin(self, user_name, computer_name) -> bool:
        try:
            computer_id = self.get_computer_id(computer_name)
            user_id = self.get_user_id(user_name)
            if not user_id:
                user_id = user_name
            sql = """
            DELETE FROM authorised_admins WHERE user_id = ? AND computer_id = ?
            """
            self.cursor.execute(sql, [user_id, computer_id])
            self.connection.commit()
            logging.info("Successfully removed admin")
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            return False


    def get_computer_info(self, computer_name) -> bool | tuple:
        sql = """
        SELECT objectSid, ip_addr, operating_system FROM computers WHERE computer_name = ?
        """
        self.cursor.execute(sql, [computer_name])
        data = self.cursor.fetchone()
        if data is None:
            logging.warning("Unable to find computer")
            return False
        else:
            return data

    def get_computer_admins(self, computer_name) -> list:

        sql_computer_id = """
        SELECT computer_id FROM computers WHERE computer_name = ?
        """
        self.cursor.execute(sql_computer_id, [computer_name])
        computer_id = self.cursor.fetchone()[0]

        sql_admins = """
        SELECT user_id, persistent FROM authorised_admins WHERE computer_id = ?
        """
        self.cursor.execute(sql_admins, [computer_id])
        data = self.cursor.fetchall()
        clean_list = []
        for item in data:
            clean_list.append((item[0], item[1]))
        return clean_list

    def create_session_db(self, computer_name, user_name, reason) -> bool:
        sql = """
        INSERT INTO sessions (computer_id, user_id, start_time, expiry_time, reason, expired) VALUES (?, ?, ?, ?, ?, ?)
        """
        computer_id = self.get_computer_id(computer_name)
        if not computer_id:
            logging.error("Failed to create session due to invalid computer")
            print("Failed to create session due to invalid computer")
            return False
        user_name = user_name.split("\\")[-1]
        user_id = self.get_user_id(user_name)
        print(f"Username | UserID : {user_name} | {user_id}")
        if not user_id:
            logging.error("Failed to create session due to invalid user")
            print("Failed to create session due to invalid user")
            return False
        start_time = datetime.datetime.now()
        expiry_time = start_time + datetime.timedelta(minutes=self.app_config["MAX_SESSION_LENGTH_MINS"])
        try:
            self.cursor.execute(sql, [computer_id, user_id, start_time, expiry_time, reason, False])
            self.connection.commit()
            logging.info("Successfully created session in database.")
            print("Successfully created session in database.")
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Unable to create session in database.", error)
            return False

    def get_all_sessions_db(self):
        sql = """
        SELECT computer_id, user_id, start_time, expiry_time, reason FROM sessions
        """
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        return data

    def get_sessions_by_computer_db(self, computer_name) -> list:
        sql = """
        SELECT computer_id, user_id, start_time, expiry_time, reason, expired FROM sessions WHERE computer_id = ?
        """
        computer_id = self.get_computer_id(computer_name.upper())
        if not computer_id:
            print(f"Unable to get ID for computer {computer_name}")
            return []
        self.cursor.execute(sql, [computer_id])
        data = self.cursor.fetchall()
        return data

    def get_non_expired_sessions_by_computer_and_user(self, computer_name, user_name) -> list:
        sql = """
        SELECT session_id, computer_id, user_id, start_time, expiry_time, reason, expired FROM sessions WHERE computer_id = ? AND user_id = ? AND expired = 0
        """
        computer_id = self.get_computer_id(computer_name)
        user_id = self.get_user_id(user_name)
        if not computer_id and not user_id:
            print(f"Unable to get ID for computer {computer_name} or user {user_name}")
            return []
        self.cursor.execute(sql, [computer_id, user_id])
        data = self.cursor.fetchall()
        return data

    def expire_session(self, session_id):
        sql = """
        UPDATE sessions SET expired = TRUE WHERE session_id = ?
        """
        self.cursor.execute(sql, [session_id])
        self.connection.commit()

    # ==================
    # All below here should be web app related

    def add_web_user(self, user_name, password, samAccountName):
        sql = """
        INSERT INTO webapp_users (user_id, user_name, password, salt, ad_user_id, site_admin) VALUES (?, ?, ?, ?, ?, ?)
        """
        user_exists = self.get_web_user(user_name)
        if user_exists:
            print("User already exists")
            return False
        salt = secrets.token_urlsafe(16)
        user_name = user_name.lower()
        salted_password = password + salt

        hashed_password = hashlib.sha512(salted_password.encode()).hexdigest()

        ad_user_exists = self.get_user_id(samAccountName)
        if not ad_user_exists:
            print("AD does not exist")
            return False

        user_id = uuid.uuid4().hex
        user_id_exists = self.get_web_user_from_id(user_id)
        while user_id_exists:
            user_id = uuid.uuid4().hex
            user_id_exists = self.get_web_user_from_id(user_id)

        try:
            self.cursor.execute(sql, [user_id, user_name, hashed_password, salt, ad_user_exists, False])
            self.connection.commit()
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Unable to create user in database.", error)
            return False

    def get_web_user_from_id(self, user_id):
        try:
            sql = """
            SELECT user_id, user_name, password, salt, ad_user_id, site_admin FROM webapp_users WHERE user_id = ?
            """
            self.cursor.execute(sql, [user_id])
            data = self.cursor.fetchall()
            return data
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Unable to get user in database.", error)
            return []

    def get_web_user(self, user_name):
        try:
            sql = """
            SELECT user_id, password, salt, ad_user_id, site_admin FROM webapp_users WHERE user_name = ?
            """
            self.cursor.execute(sql, [user_name])
            data = self.cursor.fetchone()
            return data
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to get web user from database.")
            return []

    def remove_web_user(self, user_name):
        sql = """
        DELETE FROM webapp_users WHERE user_name = ?
        """
        try:
            self.cursor.execute(sql, [user_name])
            self.connection.commit()
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to remove web user from database.")
            return False



    def reset_web_password(self, user_name, password):
        salt = secrets.token_urlsafe(16)
        salted_password = password + salt
        hashed_password = hashlib.sha512(salted_password.encode()).hexdigest()

        sql = """
        UPDATE webapp_users SET password = ?, SALT = ? WHERE user_name = ?
        """
        try:
            self.cursor.execute(sql, [hashed_password, salt, user_name])
            self.connection.commit()
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to reset web password.", error)
            return False

    def make_web_admin(self, user_name):
        sql = """
        UPDATE webapp_users SET site_admin = 1 WHERE user_name = ?
        """

        try:
            self.cursor.execute(sql, [user_name])
            self.connection.commit()
            print(f"Updated user {user_name} to web admin")
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to make web admin for database.", error)
            return False

    def get_all_web_admins(self):
        try:
            sql = """
            SELECT user_id, user_name, password, salt, ad_user_id, site_admin FROM webapp_users WHERE site_admin = 1
            """

            self.cursor.execute(sql)
            data = self.cursor.fetchall()
            return data
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to get web admins from database.", error)
            return []

    def get_all_web_users(self):
        try:
            sql = """
            SELECT user_id, user_name, password, salt, ad_user_id, site_admin FROM webapp_users
            """
            self.cursor.execute(sql)
            data = self.cursor.fetchall()
            return data
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to get web users from database.", error)
            return []

    def web_get_all_database_computers(self):
        try:
            sql = """
            SELECT computer_name, computer_id FROM computers
            """

            self.cursor.execute(sql)
            data = self.cursor.fetchall()
            clean_data = [computer[0] for computer in data]
            return data
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to get computers from database.", error)
            return []
    def web_get_computer_details(self, computer_id):
        try:
            sql = """
            SELECT computer_id, computer_name, objectSid, ip_addr, operating_system FROM computers WHERE computer_id = ?
            """
            self.cursor.execute(sql, [computer_id])
            data = self.cursor.fetchone()
            return data
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to get computer details from database.", error)
            return []

    def web_get_ad_name(self, user_name):
        try:
            sql = """
            SELECT ad_user_id FROM webapp_users WHERE user_name = ?
            """
            self.cursor.execute(sql, [user_name])
            data = self.cursor.fetchone()
            return data[0]
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed to get ad name from database.", error)
            return []

    def web_check_allowed_to_elevate(self, computer_id, ad_user_id):
        try:
            print("[DEBUG] Testing if allowed to elevate")
            sql = """
            SELECT id FROM authorised_admins WHERE computer_id = ? AND user_id = ?
            """

            self.cursor.execute(sql, [computer_id, ad_user_id])
            data = self.cursor.fetchone()
            print("[DEBUG]", data)
            return data
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            print("Failed check to elevate from database.", error)
            return []
