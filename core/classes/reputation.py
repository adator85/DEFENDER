from typing import Union
from core.definition import MReputation
from core.base import Base

class Reputation:

    UID_REPUTATION_DB: list[MReputation] = []

    def __init__(self, baseObj: Base) -> None:

        self.Logs = baseObj.logs
        self.MReputation: MReputation = MReputation

        return None

    def insert(self, newReputationUser: MReputation) -> bool:
        """Insert a new Reputation User object

        Args:
            newReputationUser (MReputation): New Reputation Model object

        Returns:
            bool: True if inserted
        """
        result = False
        exist = False

        for record in self.UID_REPUTATION_DB:
            if record.uid == newReputationUser.uid:
                # If the user exist then return False and do not go further
                exist = True
                self.Logs.debug(f'{record.uid} already exist')
                return result

        if not exist:
            self.UID_REPUTATION_DB.append(newReputationUser)
            result = True
            self.Logs.debug(f'New Reputation User Captured: ({newReputationUser})')

        if not result:
            self.Logs.critical(f'The Reputation User Object was not inserted {newReputationUser}')

        return result

    def update(self, uid: str, newNickname: str) -> bool:
        """Update the nickname starting from the UID

        Args:
            uid (str): UID of the user
            newNickname (str): New nickname

        Returns:
            bool: True if updated
        """

        reputationObj = self.get_Reputation(uid)

        if reputationObj is None:
            return False

        reputationObj.nickname = newNickname

        return True

    def delete(self, uid: str) -> bool:
        """Delete the User starting from the UID

        Args:
            uid (str): UID of the user

        Returns:
            bool: True if deleted
        """
        result = False

        if not self.is_exist(uid):
            return result

        for record in self.UID_REPUTATION_DB:
            if record.uid == uid:
                # If the user exist then remove and return True and do not go further
                self.UID_REPUTATION_DB.remove(record)
                result = True
                self.Logs.debug(f'UID ({record.uid}) has been deleted')
                return result

        if not result:
            self.Logs.critical(f'The UID {uid} was not deleted')

        return result

    def get_Reputation(self, uidornickname: str) -> Union[MReputation, None]:
        """Get The User Object model

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            UserModel|None: The UserModel Object | None
        """
        User = None
        for record in self.UID_REPUTATION_DB:
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

        reputationObj = self.get_Reputation(uidornickname)

        if reputationObj is None:
            return None

        return reputationObj.uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:
        """Get the Nickname starting from UID or the nickname

        Args:
            uidornickname (str): UID or Nickname of the user

        Returns:
            str|None: the nickname
        """
        reputationObj = self.get_Reputation(uidornickname)

        if reputationObj is None:
            return None

        return reputationObj.nickname

    def is_exist(self, uidornickname: str) -> bool:
        """Check if the UID or the nickname exist in the reputation DB

        Args:
            uidornickname (str): The UID or the NICKNAME

        Returns:
            bool: True if exist
        """

        reputationObj = self.get_Reputation(uidornickname)

        if reputationObj is None:
            return False
        else:
            return True
