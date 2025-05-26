from ldap3 import Server, Connection, ALL, NTLM
import json
import socket
from ADScripts import ad_config

from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError


class LDAPController:
    def __init__(self):
        self.AD_CONFIG = ad_config
        self.AD_SERVER = f'ldap://{self.AD_CONFIG["DomainPreferredLDAPServer"]}'
        self.USER = f"{self.AD_CONFIG['DomainNetBIOSName']}\\{self.AD_CONFIG['ScannerUsername']}"
        self.PASSWORD = self.AD_CONFIG['ScannerPassword']
        self.BASE_DN = self.AD_CONFIG['DomainBaseDN']
        self.conn = self.bind_connection()


    def bind_connection(self):
        # Create an LDAP server object using SSL
        server = Server(self.AD_SERVER, get_info=ALL, use_ssl=True)

        # Create a connection to the server
        try:
            conn = Connection(server, user=self.USER, password=self.PASSWORD, authentication=NTLM, auto_bind=True)
            if not conn.bind():
                print("Failed to bind", conn.result)
                return False
            return conn
        except LDAPBindError as e:
            print("[ERROR] Unable to bind to LDAP server", e)
            return False
        except LDAPSocketOpenError as e:
            print("[ERROR] Unable to connect to LDAP server", e)
            return False


    def get_ad_computers(self):
        if not self.conn:
            print("[ERROR] no valid LDAP connection")
            return False
        # Search filter for computers
        search_filter = "(objectClass=computer)"

        # Attributes to retrieve
        attributes = ['dnsHostName', 'objectSid', 'OperatingSystem']

        self.conn.search(self.BASE_DN, search_filter, attributes=attributes)

        computers = []
        for entry in self.conn.entries:
            hostname = entry.dnsHostName.value
            # Attempts to get IP Address of the host using sockets
            if hostname:
                try:
                    ip_addr = socket.gethostbyname(hostname)
                except socket.gaierror:
                    ip_addr = "N/A"
            else:
                ip_addr = "N/A"
            # Creates python dictionary containing computer information
            computer_info = {
                'FQDN': entry.dnsHostName.value,
                'ip_addr': ip_addr,
                'objectSid': entry.objectSid.value,
                'operating_system': entry.OperatingSystem.value
            }
            computers.append(computer_info)
        return computers

    def get_ad_users(self):
        # Search filter for users
        search_filter = "(objectClass=user)"

        # Attributes to retrieve
        attributes = ['SamAccountName', 'objectSid']

        # Perform the search
        self.conn.search(self.BASE_DN, search_filter, attributes=attributes)

        # Process the results
        users = []
        for entry in self.conn.entries:
            user_info = {
                "samAccountName": entry.SamAccountName.value,
                "objectSid": entry.ObjectSid.value
            }
            users.append(user_info)
        return users
    # Debug function for testing LDAP connection status, not used in ordinary operation
    def check_connection(self):
        # Prints conn status, returns false if conn is not established
        print("Testing LDAP connection status")
        print(self.conn)
        if not self.conn:
            return False
        else:
            return True

    def __str__(self):
        return f"DEBUG\n{self.USER}, {self.PASSWORD}"

if __name__ == '__main__':
    controller = LDAPController()
    controller.check_connection()
    ad_computers = controller.get_ad_computers()
    ad_users = controller.get_ad_users()
    print(json.dumps(ad_computers, indent=4))
    print("\n\n\n\n")
    print(json.dumps(ad_users, indent=4))