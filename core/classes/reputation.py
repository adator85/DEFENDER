from typing import Optional
from core.definition import MReputation
from core.base import Base

class Reputation:

    UID_REPUTATION_DB: list[MReputation] = []

    def __init__(self, baseObj: Base) -> None:

        self.Logs = baseObj.logs
        self.MReputation: MReputation = MReputation

        return None

    def insert(self, new_reputation_user: MReputation) -> bool:
        """Insert a new Reputation User object

        Args:
            new_reputation_user (MReputation): New Reputation Model object

        Returns:
            bool: True if inserted
        """
        result = False
        exist = False

        for record in self.UID_REPUTATION_DB:
            if record.uid == new_reputation_user.uid:
                # If the user exist then return False and do not go further
                exist = True
                self.Logs.debug(f'{record.uid} already exist')
                return result

        if not exist:
            self.UID_REPUTATION_DB.append(new_reputation_user)
            result = True
            self.Logs.debug(f'New Reputation User Captured: ({new_reputation_user})')

        if not result:
            self.Logs.critical(f'The Reputation User Object was not inserted {new_reputation_user}')

        return result

    def update(self, uid: str, new_nickname: str) -> bool:
        """Update the nickname starting from the UID

        Args:
            uid (str): UID of the user
            newNickname (str): New nickname

        Returns:
            bool: True if updated
        """

        reputation_obj = self.get_Reputation(uid)

        if reputation_obj is None:
            return False

        reputation_obj.nickname = new_nickname

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

    def get_Reputation(self, uidornickname: str) -> Optional[MReputation]:
        """Get The User Object model

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            UserModel|None: The UserModel Object | None
        """
        for record in self.UID_REPUTATION_DB:
            if record.uid == uidornickname:
                return record
            elif record.nickname == uidornickname:
                return record

        return None

    def get_uid(self, uidornickname: str) -> Optional[str]:
        """Get the UID of the user starting from the UID or the Nickname

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            str|None: Return the UID
        """

        reputation_obj = self.get_Reputation(uidornickname)

        if reputation_obj is None:
            return None

        return reputation_obj.uid

    def get_nickname(self, uidornickname: str) -> Optional[str]:
        """Get the Nickname starting from UID or the nickname

        Args:
            uidornickname (str): UID or Nickname of the user

        Returns:
            str|None: the nickname
        """
        reputation_obj = self.get_Reputation(uidornickname)

        if reputation_obj is None:
            return None

        return reputation_obj.nickname

    def is_exist(self, uidornickname: str) -> bool:
        """Check if the UID or the nickname exist in the reputation DB

        Args:
            uidornickname (str): The UID or the NICKNAME

        Returns:
            bool: True if exist
        """

        reputation_obj = self.get_Reputation(uidornickname)

        if isinstance(reputation_obj, MReputation):
            return True
        
        return False
