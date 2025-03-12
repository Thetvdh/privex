import sqlite3
import uuid
import logging

logging.basicConfig(
    level=logging.INFO,
    filename="database.log",
    encoding="utf-8",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S",
)

class DBConnector:
    def __init__(self):
        self.name = f"DB/privex.db"
        self.connection = None
        self.cursor = None
        self.establish_connection()

    def establish_connection(self):
        try:
            self.connection = sqlite3.connect(self.name)
            self.cursor = self.connection.cursor()
        except sqlite3.DatabaseError as error:
            logging.error(f"{error}")

    def close_connection(self):
        if self.connection is not None:
            self.connection.close()


class DBInterface(DBConnector):
    def __init__(self):
        super().__init__()

    def add_computer(self, computer: dict):
        computer_id = uuid.uuid4().hex
        while self.check_unique_computer_id(computer_id):
            computer_id = uuid.uuid4()
        computer["computer_id"] = computer_id
        try:
            sql = """
            INSERT INTO computers (computer_id, computer_name, objectSid, ip_addr, operating_system) VALUES (?, ?, ?, ?, ?)
            """
            self.cursor.execute(sql, (computer["computer_id"], computer["FQDN"], computer["objectSid"], computer["ip_addr"], computer["operating_system"]))
            self.connection.commit()
            logging.info("Successfully added computer")
            return True
        except sqlite3.OperationalError as error:
            logging.error(f"{error}")
            return False

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

    # Returns false if the computer is not already in the database
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