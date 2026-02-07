from typing import TYPE_CHECKING, Optional
from core.definition import MReputation

if TYPE_CHECKING:
    from core.loader import Loader

class Reputation:

    UID_REPUTATION_DB: list[MReputation] = []

    def __init__(self, loader: 'Loader'):
        """

        Args:
            loader (Loader): The Loader instance.
        """
        self._ctx = loader

    def insert(self, new_reputation_user: MReputation) -> bool:
        """Insert a new Reputation User object

        Args:
            new_reputation_user (MReputation): New Reputation Model object

        Returns:
            bool: True if inserted
        """
        if not isinstance(new_reputation_user, MReputation):
            self._ctx.Logs.debug('Wrong object, you must pass an MReputation object!')
            return False

        _ruser = self.get_reputation(new_reputation_user.uid)

        if _ruser is None:
            self.UID_REPUTATION_DB.append(new_reputation_user)
            self._ctx.Logs.debug(f'New Reputation User Captured: ({new_reputation_user})')
            return True

        return False

    def update(self, uid: str, new_nickname: str) -> bool:
        """Update the nickname starting from the UID

        Args:
            uid (str): UID of the user
            new_nickname (str): New nickname

        Returns:
            bool: True if updated
        """

        reputation_obj = self.get_reputation(uid)

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
        _ruser = self.get_reputation(uid)
        if _ruser:
            self._ctx.Logs.debug(f'UID ({_ruser.uid}) has been deleted')
            self.UID_REPUTATION_DB.remove(_ruser)
            return True

        return False

    def get_reputation(self, uidornickname: str) -> Optional[MReputation]:
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

        reputation_obj = self.get_reputation(uidornickname)

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
        reputation_obj = self.get_reputation(uidornickname)

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

        reputation_obj = self.get_reputation(uidornickname)

        if isinstance(reputation_obj, MReputation):
            return True
        
        return False
