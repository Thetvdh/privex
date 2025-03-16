from Scanner import scanner
from ComputerInterface import windows

# scanner.get_computers()
#
# scanner.add_computers()
#
# scanner.add_users()

win_scanner = windows.WindowsWorker()

session = win_scanner.establish_winrm_session('WINSERVFYP.FYP.LOC')
print("\n\n\n\n\n")

admins = win_scanner.get_computer_administrators(session)

print(admins)
#
# win_scanner.get_kerberos_ticket()
# win_scanner.debug()

