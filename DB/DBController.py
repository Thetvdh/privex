import sqlite3
import uuid
import logging
from distutils.command.clean import clean

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
            self.connection = sqlite3.connect(self.name)
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
    def get_computer_id(self, computer_name):
        sql = """
        SELECT computer_id FROM computers WHERE computer_name = ?
        """
        self.cursor.execute(sql, [computer_name])
        data = self.cursor.fetchone()
        if data is None:
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
                else:
                    domain_account = False
                    admin_user_id = admin # Test how this works with removal from admins
                    self.cursor.execute(sql, (computer_id, admin_user_id, persistent, domain_account))
                    self.connection.commit()
                    logging.info("Successfully added admin")
            except sqlite3.OperationalError as error:
                logging.error(f"{error}")
                return False


    def get_computer_admins(self, computer_name) -> list:

        sql_computer_id = """
        SELECT computer_id FROM computers WHERE computer_name = ?
        """
        self.cursor.execute(sql_computer_id, [computer_name])
        computer_id = self.cursor.fetchone()[0]

        sql_admins = """
        SELECT user_id FROM authorised_admins WHERE computer_id = ?
        """
        self.cursor.execute(sql_admins, [computer_id])
        data = self.cursor.fetchall()
        clean_list = []
        for item in data:
            clean_list.append(item[0])
        return clean_list