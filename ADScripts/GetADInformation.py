from ldap3 import Server, Connection, ALL, NTLM
import json
import yaml
import socket

def load_config():
    with open("domain_config.yaml", "r") as config_file:
        ad_config = yaml.safe_load(config_file)
    return ad_config


class LDAPController:
    def __init__(self):
        self.AD_CONFIG = load_config()
        self.AD_SERVER = f'ldap://{self.AD_CONFIG["DomainPreferredLDAPServer"]}'
        self.USER = f"{self.AD_CONFIG['DomainNetBIOSName']}\\{self.AD_CONFIG['ScannerUsername']}"
        self.PASSWORD = self.AD_CONFIG['ScannerPassword']
        self.BASE_DN = self.AD_CONFIG['DomainBaseDN']
        self.conn = self.bind_connection()


    def bind_connection(self):
        # Create an LDAP server object using SSL
        server = Server(self.AD_SERVER, get_info=ALL, use_ssl=True)

        # Create a connection to the server
        conn = Connection(server, user=self.USER, password=self.PASSWORD, authentication=NTLM, auto_bind=True)

        if not conn.bind():
            # TODO add error handling for failed bind
            print("Failed to bind", conn.result)
        return conn

    def get_ad_computers(self):
        # Search filter for computers
        search_filter = "(objectClass=computer)"

        # Attributes to retrieve
        attributes = ['dnsHostName', 'objectSid']

        # Perform the search
        self.conn.search(self.BASE_DN, search_filter, attributes=attributes)

        computers = []
        for entry in self.conn.entries:
            hostname = entry.dnsHostName.value
            # Attempts to get IP Address of the host
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
                'IP Address': ip_addr,
                'SID': entry.objectSid.value
            }
            computers.append(computer_info)
        return computers

    def get_ad_users(self):
        # Search filter for users
        search_filter = "(objectClass=user)"

        # Attributes to retrieve
        attributes = ['SamAccountName', 'UserPrincipalName', 'objectSid']

        # Perform the search
        self.conn.search(self.BASE_DN, search_filter, attributes=attributes)

        # Process the results
        users = []
        for entry in self.conn.entries:
            user_info = {
                "samAccountName": entry.SamAccountName.value,
                "UserPrincipalName": entry.UserPrincipalName.value,
                "objectSid": entry.ObjectSid.value
            }
            users.append(user_info)
        return users
    # Debug function for testing LDAP connection status, not used in ordinary operation
    def check_connection(self):
        print("Testing LDAP connection status")
        print(self.conn.result)

if __name__ == '__main__':
    controller = LDAPController()
    ad_computers = controller.get_ad_computers()
    ad_users = controller.get_ad_users()
    print(json.dumps(ad_computers, indent=4))
    print("\n\n\n\n")
    print(json.dumps(ad_users, indent=4))