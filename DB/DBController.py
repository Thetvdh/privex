import sqlite3
import uuid

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
            print(f"[ERROR] {error}")

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
            print("[SUCCESS] Successfully added computer")
            return True
        except sqlite3.OperationalError as error:
            print(f"[ERROR] {error}")
            return False

    def add_user(self, user: dict):
        user_id = uuid.uuid4().hex
        while self.check_unique_user_id(user_id):
            user_id = uuid.uuid4()
        user["user_id"] = user_id
        try:
            sql = """
            INSERT INTO users (user_id, samAccountName, objectSid) VALUES (?, ?, ?)
            """
            self.cursor.execute(sql, (user["user_id"], user["samAccountName"], user["objectSid"]))
            self.connection.commit()
            print("[SUCCESS] Successfully added user")
            return True
        except sqlite3.OperationalError as error:
            print(f"[ERROR] {error}")
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
        SELECT user_id FROM users WHERE user_id = ?
        """
        self.cursor.execute(sql, [user_id])
        data = self.cursor.fetchone()
        if data is None:
            return False
        else:
            return True