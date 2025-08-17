from typing import TYPE_CHECKING, Optional
from core.base import Base
from core.definition import MAdmin

if TYPE_CHECKING:
    from core.loader import Loader

class Admin:

    UID_ADMIN_DB: list[MAdmin] = []

    def __init__(self, loader: 'Loader') -> None:
        self.Logs = loader.Logs

    def insert(self, new_admin: MAdmin) -> bool:
        """Insert a new admin object model

        Args:
            new_admin (MAdmin): The new admin object model to insert

        Returns:
            bool: True if it was inserted
        """

        for record in self.UID_ADMIN_DB:
            if record.uid == new_admin.uid:
                # If the admin exist then return False and do not go further
                self.Logs.debug(f'{record.uid} already exist')
                return False

        self.UID_ADMIN_DB.append(new_admin)
        self.Logs.debug(f'A new admin ({new_admin.nickname}) has been created')
        return True

    def update_nickname(self, uid: str, new_admin_nickname: str) -> bool:
        """Update nickname of an admin

        Args:
            uid (str): The Admin UID
            new_admin_nickname (str): The new nickname of the admin

        Returns:
            bool: True if the nickname has been updated.
        """

        for record in self.UID_ADMIN_DB:
            if record.uid == uid:
                # If the admin exist, update and do not go further
                record.nickname = new_admin_nickname
                self.Logs.debug(f'UID ({record.uid}) has been updated with new nickname {new_admin_nickname}')
                return True


        self.Logs.debug(f'The new nickname {new_admin_nickname} was not updated, uid = {uid} - The Client is not an admin')
        return False

    def update_level(self, nickname: str, new_admin_level: int) -> bool:
        """Update the admin level

        Args:
            nickname (str): The admin nickname
            new_admin_level (int): The new level of the admin

        Returns:
            bool: True if the admin level has been updated
        """

        for record in self.UID_ADMIN_DB:
            if record.nickname == nickname:
                # If the admin exist, update and do not go further
                record.level = new_admin_level
                self.Logs.debug(f'Admin ({record.nickname}) has been updated with new level {new_admin_level}')
                return True

        self.Logs.debug(f'The new level {new_admin_level} was not updated, nickname = {nickname} - The Client is not an admin')

        return False

    def delete(self, uidornickname: str) -> bool:
        """Delete admin

        Args:
            uidornickname (str): The UID or nickname of the admin

        Returns:
            bool: True if the admin has been deleted
        """

        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                # If the admin exist, delete and do not go further
                self.UID_ADMIN_DB.remove(record)
                self.Logs.debug(f'UID ({record.uid}) has been deleted')
                return True
            if record.nickname.lower() == uidornickname.lower():
                # If the admin exist, delete and do not go further
                self.UID_ADMIN_DB.remove(record)
                self.Logs.debug(f'nickname ({record.nickname}) has been deleted')
                return True

        self.Logs.debug(f'The UID {uidornickname} was not deleted')

        return False

    def get_admin(self, uidornickname: str) -> Optional[MAdmin]:
        """Get the admin object model

        Args:
            uidornickname (str): UID or Nickname of the admin

        Returns:
            Optional[MAdmin]: The MAdmin object model if exist
        """

        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                return record
            elif record.nickname.lower() == uidornickname.lower():
                return record

        return None

    def get_uid(self, uidornickname:str) -> Optional[str]:
        """Get the UID of the admin

        Args:
            uidornickname (str): The UID or nickname of the admin

        Returns:
            Optional[str]: The UID of the admin
        """

        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                return record.uid
            if record.nickname.lower() == uidornickname.lower():
                return record.uid

        return None

    def get_nickname(self, uidornickname:str) -> Optional[str]:
        """Get the nickname of the admin

        Args:
            uidornickname (str): The UID or the nickname of the admin

        Returns:
            Optional[str]: The nickname of the admin
        """

        for record in self.UID_ADMIN_DB:
            if record.nickname.lower() == uidornickname.lower():
                return record.nickname
            if record.uid == uidornickname:
                return record.nickname

        return None