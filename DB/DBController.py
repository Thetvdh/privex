import sqlite3

class DBConnector:
    def __init__(self):
        self.name = "privex.db"
        self.connection = None
        self.cursor = None
        self.establish_conection()

    def establish_conection(self):
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

    def add_computers(self, computers: list):
        pass
