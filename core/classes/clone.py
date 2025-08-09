from core.definition import MClone
from typing import Any, Optional
from core.base import Base

class Clone:

    UID_CLONE_DB: list[MClone] = []

    def __init__(self, baseObj: Base) -> None:

        self.Logs = baseObj.logs

        return None

    def insert(self, newCloneObject: MClone) -> bool:
        """Create new Clone object

        Args:
            newCloneObject (CloneModel): New CloneModel object

        Returns:
            bool: True if inserted
        """
        result = False
        exist = False

        for record in self.UID_CLONE_DB:
            if record.nickname == newCloneObject.nickname:
                # If the user exist then return False and do not go further
                exist = True
                self.Logs.warning(f'Nickname {record.nickname} already exist')
                return result
            if record.uid == newCloneObject.uid:
                exist = True
                self.Logs.warning(f'UID: {record.uid} already exist')
                return result

        if not exist:
            self.UID_CLONE_DB.append(newCloneObject)
            result = True
            # self.Logs.debug(f'New Clone Object Created: ({newCloneObject})')

        if not result:
            self.Logs.critical(f'The Clone Object was not inserted {newCloneObject}')

        return result

    def delete(self, uidornickname: str) -> bool:
        """Delete the Clone Object starting from the nickname or the UID

        Args:
            uidornickname (str): UID or nickname of the clone

        Returns:
            bool: True if deleted
        """

        cloneObj = self.get_Clone(uidornickname=uidornickname)

        if cloneObj is None:
            return False

        self.UID_CLONE_DB.remove(cloneObj)

        return True

    def exists(self, nickname: str) -> bool:
        """Check if the nickname exist

        Args:
            nickname (str): Nickname of the clone

        Returns:
            bool: True if the nickname exist
        """
        clone = self.get_Clone(nickname)
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
        clone = self.get_Clone(uid)
        if isinstance(clone, MClone):
            return True
        
        return False

    def get_Clone(self, uidornickname: str) -> Optional[MClone]:
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

    def get_Clone_AsDict(self, uidornickname: str) -> Optional[dict[str, Any]]:

        clone_obj = self.get_Clone(uidornickname=uidornickname)

        if clone_obj is None:
            return None
        
        return clone_obj.to_dict()

    def kill(self, nickname:str) -> bool:

        response = False

        for cloneObject in self.UID_CLONE_DB:
            if cloneObject.nickname == nickname:
                cloneObject.alive = False # Kill the clone
                response = True

        return response