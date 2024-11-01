import re
from typing import Union, TYPE_CHECKING
from dataclasses import asdict

if TYPE_CHECKING:
    from core.base import Base
    from core.definition import MUser

class User:

    UID_DB: list['MUser'] = []

    def __init__(self, baseObj: 'Base') -> None:

        self.Logs = baseObj.logs
        self.Base = baseObj

        return None

    def insert(self, newUser: 'MUser') -> bool:
        """Insert a new User object

        Args:
            newUser (UserModel): New userModel object

        Returns:
            bool: True if inserted
        """
        result = False
        exist = False

        for record in self.UID_DB:
            if record.uid == newUser.uid:
                # If the user exist then return False and do not go further
                exist = True
                self.Logs.debug(f'{record.uid} already exist')
                return result

        if not exist:
            self.UID_DB.append(newUser)
            result = True
            # self.Logs.debug(f'New User Created: ({newUser})')

        if not result:
            self.Logs.critical(f'The User Object was not inserted {newUser}')

        return result

    def update(self, uid: str, newNickname: str) -> bool:
        """Update the nickname starting from the UID

        Args:
            uid (str): UID of the user
            newNickname (str): New nickname

        Returns:
            bool: True if updated
        """
        result = False

        for record in self.UID_DB:
            if record.uid == uid:
                # If the user exist then update and return True and do not go further
                record.nickname = newNickname
                result = True
                # self.Logs.debug(f'UID ({record.uid}) has been updated with new nickname {newNickname}')
                return result

        if not result:
            self.Logs.critical(f'The new nickname {newNickname} was not updated, uid = {uid}')

        return result

    def delete(self, uid: str) -> bool:
        """Delete the User starting from the UID

        Args:
            uid (str): UID of the user

        Returns:
            bool: True if deleted
        """
        result = False

        for record in self.UID_DB:
            if record.uid == uid:
                # If the user exist then remove and return True and do not go further
                self.UID_DB.remove(record)
                result = True
                # self.Logs.debug(f'UID ({record.uid}) has been deleted')
                return result

        if not result:
            self.Logs.critical(f'The UID {uid} was not deleted')

        return result

    def get_User(self, uidornickname: str) -> Union['MUser', None]:
        """Get The User Object model

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            UserModel|None: The UserModel Object | None
        """
        User = None
        for record in self.UID_DB:
            if record.uid == uidornickname:
                User = record
            elif record.nickname == uidornickname:
                User = record

        # self.Logs.debug(f'Search {uidornickname} -- result = {User}')

        return User

    def get_uid(self, uidornickname:str) -> Union[str, None]:
        """Get the UID of the user starting from the UID or the Nickname

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            str|None: Return the UID
        """
        uid = None
        for record in self.UID_DB:
            if record.uid == uidornickname:
                uid = record.uid
            if record.nickname == uidornickname:
                uid = record.uid

        # if not uid is None:
        #     self.Logs.debug(f'The UID that you are looking for {uidornickname} has been found {uid}')

        return uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:
        """Get the Nickname starting from UID or the nickname

        Args:
            uidornickname (str): UID or Nickname of the user

        Returns:
            str|None: the nickname
        """
        nickname = None
        for record in self.UID_DB:
            if record.nickname == uidornickname:
                nickname = record.nickname
            if record.uid == uidornickname:
                nickname = record.nickname
        # self.Logs.debug(f'The value to check {uidornickname} -> {nickname}')
        return nickname

    def get_User_AsDict(self, uidornickname: str) -> Union[dict[str, any], None]:

        userObj = self.get_User(uidornickname=uidornickname)

        if not userObj is None:
            user_as_dict = asdict(userObj)
            return user_as_dict
        else:
            return None

    def clean_uid(self, uid: str) -> str:
        """Clean UID by removing @ / % / + / ~ / * / :

        Args:
            uid (str): The UID to clean

        Returns:
            str: Clean UID without any sign
        """

        pattern = fr'[:|@|%|\+|~|\*]*'
        parsed_UID = re.sub(pattern, '', uid)

        return parsed_UID