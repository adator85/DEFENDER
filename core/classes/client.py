from re import sub
from typing import Any, Optional, Union, TYPE_CHECKING
from dataclasses import asdict

if TYPE_CHECKING:
    from core.base import Base
    from core.definition import MClient

class Client:

    CLIENT_DB: list['MClient'] = []

    def __init__(self, baseObj: 'Base') -> None:

        self.Logs = baseObj.logs
        self.Base = baseObj

        return None

    def insert(self, newUser: 'MClient') -> bool:
        """Insert a new User object

        Args:
            newUser (UserModel): New userModel object

        Returns:
            bool: True if inserted
        """

        userObj = self.get_Client(newUser.uid)

        if not userObj is None:
            # User already created return False
            return False

        self.CLIENT_DB.append(newUser)

        return True

    def update_nickname(self, uid: str, newNickname: str) -> bool:
        """Update the nickname starting from the UID

        Args:
            uid (str): UID of the user
            newNickname (str): New nickname

        Returns:
            bool: True if updated
        """
        userObj = self.get_Client(uidornickname=uid)

        if userObj is None:
            return False

        userObj.nickname = newNickname

        return True

    def update_mode(self, uidornickname: str, modes: str) -> bool:
        """Updating user mode

        Args:
            uidornickname (str): The UID or Nickname of the user
            modes (str): new modes to update

        Returns:
            bool: True if user mode has been updaed
        """
        response = True
        userObj = self.get_Client(uidornickname=uidornickname)

        if userObj is None:
            return False

        action = modes[0]
        new_modes = modes[1:]

        existing_umodes = userObj.umodes
        umodes = userObj.umodes

        if action == '+':

            for nm in new_modes:
                if nm not in existing_umodes:
                    umodes += nm

        elif action == '-':
            for nm in new_modes:
                if nm in existing_umodes:
                    umodes = umodes.replace(nm, '')
        else:
            return False

        liste_umodes = list(umodes)
        final_umodes_liste = [x for x in self.Base.Settings.PROTOCTL_USER_MODES if x in liste_umodes]
        final_umodes = ''.join(final_umodes_liste)

        userObj.umodes = f"+{final_umodes}"

        return response

    def delete(self, uid: str) -> bool:
        """Delete the User starting from the UID

        Args:
            uid (str): UID of the user

        Returns:
            bool: True if deleted
        """

        userObj = self.get_Client(uidornickname=uid)

        if userObj is None:
            return False

        self.CLIENT_DB.remove(userObj)

        return True

    def get_Client(self, uidornickname: str) -> Union['MClient', None]:
        """Get The Client Object model

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            UserModel|None: The UserModel Object | None
        """
        User = None
        for record in self.CLIENT_DB:
            if record.uid == uidornickname:
                User = record
            elif record.nickname == uidornickname:
                User = record

        return User

    def get_uid(self, uidornickname:str) -> Union[str, None]:
        """Get the UID of the user starting from the UID or the Nickname

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            str|None: Return the UID
        """

        userObj = self.get_Client(uidornickname=uidornickname)

        if userObj is None:
            return None

        return userObj.uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:
        """Get the Nickname starting from UID or the nickname

        Args:
            uidornickname (str): UID or Nickname of the user

        Returns:
            str|None: the nickname
        """
        userObj = self.get_Client(uidornickname=uidornickname)

        if userObj is None:
            return None

        return userObj.nickname

    def get_client_asdict(self, uidornickname: str) -> Optional[dict[str, Any]]:
        """Transform User Object to a dictionary

        Args:
            uidornickname (str): The UID or The nickname

        Returns:
            Union[dict[str, any], None]: User Object as a dictionary or None
        """
        client_obj = self.get_Client(uidornickname=uidornickname)

        if client_obj is None:
            return None

        return client_obj.to_dict()

    def is_exist(self, uidornikname: str) -> bool:
        """Check if the UID or the nickname exist in the USER DB

        Args:
            uidornickname (str): The UID or the NICKNAME

        Returns:
            bool: True if exist
        """
        userObj = self.get_Client(uidornickname=uidornikname)

        if userObj is None:
            return False

        return True

    def db_is_account_exist(self, account: str) -> bool:
        """Check if the account exist in the database

        Args:
            account (str): The account to check

        Returns:
            bool: True if exist
        """

        table_client = self.Base.Config.TABLE_CLIENT
        account_to_check = {'account': account.lower()}
        account_to_check_query = self.Base.db_execute_query(f"""
                    SELECT id FROM {table_client} WHERE LOWER(account) = :account
                    """, account_to_check)

        account_to_check_result = account_to_check_query.fetchone()
        if account_to_check_result:
            self.Logs.error(f"Account ({account}) already exist")
            return True

        return False

    def clean_uid(self, uid: str) -> Union[str, None]:
        """Clean UID by removing @ / % / + / ~ / * / :

        Args:
            uid (str): The UID to clean

        Returns:
            str: Clean UID without any sign
        """

        pattern = fr'[:|@|%|\+|~|\*]*'
        parsed_UID = sub(pattern, '', uid)

        if not parsed_UID:
            return None

        return parsed_UID