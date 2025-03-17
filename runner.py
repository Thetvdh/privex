from Scanner import scanner
from DB.DBController import DBInterface

admins = scanner.get_computer_admins_windows('WINSERVFYP.FYP.LOC')

interface = DBInterface()

interface.setup_add_computer_admins(admins, "WINSERVFYP.FYP.LOC", "FYP")
