from re import sub
from typing import Any, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from core.loader import Loader
    from core.definition import MClient

class Client:

    CLIENT_DB: list['MClient'] = []

    def __init__(self, loader: 'Loader'):
        """

        Args:
            loader (Loader): The Loader instance.
        """
        self._ctx = loader

    def insert(self, new_client: 'MClient') -> bool:
        """Insert a new User object

        Args:
            new_client (MClient): New Client object

        Returns:
            bool: True if inserted
        """

        client_obj = self.get_client(new_client.uid)

        if not client_obj is None:
            # User already created return False
            return False

        self.CLIENT_DB.append(new_client)

        return True

    def update_nickname(self, uid: str, new_nickname: str) -> bool:
        """Update the nickname starting from the UID

        Args:
            uid (str): UID of the user
            new_nickname (str): New nickname

        Returns:
            bool: True if updated
        """
        user_obj = self.get_client(uidornickname=uid)

        if user_obj is None:
            return False

        user_obj.nickname = new_nickname

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
        user_obj = self.get_client(uidornickname=uidornickname)

        if user_obj is None:
            return False

        action = modes[0]
        new_modes = modes[1:]

        existing_umodes = user_obj.umodes
        umodes = user_obj.umodes

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
        final_umodes_liste = [x for x in self._ctx.Base.Settings.PROTOCTL_USER_MODES if x in liste_umodes]
        final_umodes = ''.join(final_umodes_liste)

        user_obj.umodes = f"+{final_umodes}"

        return response

    def delete(self, uid: str) -> bool:
        """Delete the User starting from the UID

        Args:
            uid (str): UID of the user

        Returns:
            bool: True if deleted
        """

        user_obj = self.get_client(uidornickname=uid)

        if user_obj is None:
            return False

        self.CLIENT_DB.remove(user_obj)

        return True

    def get_client(self, uidornickname: str) -> Optional['MClient']:
        """Get The Client Object model

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            UserModel|None: The UserModel Object | None
        """
        for record in self.CLIENT_DB:
            if record.uid == uidornickname:
                return record
            elif record.nickname == uidornickname:
                return record

        return None

    def get_uid(self, uidornickname:str) -> Optional[str]:
        """Get the UID of the user starting from the UID or the Nickname

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            str|None: Return the UID
        """

        client_obj = self.get_client(uidornickname=uidornickname)

        if client_obj is None:
            return None

        return client_obj.uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:
        """Get the Nickname starting from UID or the nickname

        Args:
            uidornickname (str): UID or Nickname of the user

        Returns:
            str|None: the nickname
        """
        client_obj = self.get_client(uidornickname=uidornickname)

        if client_obj is None:
            return None

        return client_obj.nickname

    def is_exist(self, uidornickname: str) -> bool:
        """Check if the UID or the nickname exist in the USER DB

        Args:
            uidornickname (str): The UID or the NICKNAME

        Returns:
            bool: True if exist
        """
        user_obj = self.get_client(uidornickname=uidornickname)

        if user_obj is None:
            return False

        return True

    async def db_is_account_exist(self, account: str) -> bool:
        """Check if the account exist in the database

        Args:
            account (str): The account to check

        Returns:
            bool: True if exist
        """

        table_client = self._ctx.Base.Config.TABLE_CLIENT
        account_to_check = {'account': account.lower()}
        account_to_check_query = await self._ctx.Base.db_execute_query(f"""
                    SELECT id FROM {table_client} WHERE LOWER(account) = :account
                    """, account_to_check)

        account_to_check_result = account_to_check_query.fetchone()
        if account_to_check_result:
            self._ctx.Logs.error(f"Account ({account}) already exist")
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
        parsed_uid = sub(pattern, '', uid)

        if not parsed_uid:
            return None

        return parsed_uid