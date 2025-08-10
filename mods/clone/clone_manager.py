from typing import Optional, TYPE_CHECKING
from core.definition import MClone

if TYPE_CHECKING:
    from mods.clone.mod_clone import Clone

class CloneManager:

    UID_CLONE_DB: list[MClone] = []

    def __init__(self, uplink: 'Clone'):

        self.Logs = uplink.Logs

    def insert(self, new_clone_object: MClone) -> bool:
        """Create new Clone object

        Args:
            newCloneObject (CloneModel): New CloneModel object

        Returns:
            bool: True if inserted
        """
        result = False
        exist = False

        for record in self.UID_CLONE_DB:
            if record.nickname == new_clone_object.nickname:
                # If the user exist then return False and do not go further
                exist = True
                self.Logs.warning(f'Nickname {record.nickname} already exist')
                return result
            if record.uid == new_clone_object.uid:
                exist = True
                self.Logs.warning(f'UID: {record.uid} already exist')
                return result

        if not exist:
            self.UID_CLONE_DB.append(new_clone_object)
            result = True

        if not result:
            self.Logs.critical(f'The Clone Object was not inserted {new_clone_object}')

        return result

    def delete(self, uidornickname: str) -> bool:
        """Delete the Clone Object starting from the nickname or the UID

        Args:
            uidornickname (str): UID or nickname of the clone

        Returns:
            bool: True if deleted
        """

        clone_obj = self.get_clone(uidornickname=uidornickname)

        if clone_obj is None:
            return False

        self.UID_CLONE_DB.remove(clone_obj)

        return True

    def nickname_exists(self, nickname: str) -> bool:
        """Check if the nickname exist

        Args:
            nickname (str): Nickname of the clone

        Returns:
            bool: True if the nickname exist
        """
        clone = self.get_clone(nickname)
        if isinstance(clone, MClone):
            return True
        
        return False

    def uid_exists(self, uid: str) -> bool:
        """Check if the nickname exist

        Args:
            uid (str): uid of the clone

        Returns:
            bool: True if the nickname exist
        """
        clone = self.get_clone(uid)
        if isinstance(clone, MClone):
            return True
        
        return False

    def group_exists(self, groupname: str) -> bool:
        """Verify if a group exist

        Args:
            groupname (str): The group name

        Returns:
            bool: _description_
        """
        for clone in self.UID_CLONE_DB:
            if clone.group.strip().lower() == groupname.strip().lower():
                return True

        return False

    def get_clone(self, uidornickname: str) -> Optional[MClone]:
        """Get MClone object or None

        Args:
            uidornickname (str): The UID or the Nickname

        Returns:
            Union[MClone, None]: Return MClone object or None
        """
        for clone in self.UID_CLONE_DB:
            if clone.uid == uidornickname:
                return clone
            if clone.nickname == uidornickname:
                return clone

        return None

    def get_clones_from_groupname(self, groupname: str) -> list[MClone]:
        """Get list of clone objects by group name

        Args:
            groupname (str): The group name

        Returns:
            list[MClone]: List of clones in the group
        """
        group_of_clone: list[MClone] = []

        if self.group_exists(groupname):
            for clone in self.UID_CLONE_DB:
                if clone.group.strip().lower() == groupname.strip().lower():
                    group_of_clone.append(clone)

        return group_of_clone

    def get_uid(self, uidornickname: str) -> Optional[str]:
        """Get the UID of the clone starting from the UID or the Nickname

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            str|None: Return the UID
        """
        for record in self.UID_CLONE_DB:
            if record.uid == uidornickname:
                return record.uid
            if record.nickname == uidornickname:
                return record.uid

        return None

    def kill(self, nickname:str) -> bool:

        response = False

        for clone in self.UID_CLONE_DB:
            if clone.nickname == nickname:
                clone.alive = False # Kill the clone
                response = True

        return response