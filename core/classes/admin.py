from typing import Union
import core.definition as df
from core.base import Base


class Admin:

    UID_ADMIN_DB: list[df.MAdmin] = []

    def __init__(self, baseObj: Base) -> None:
        self.Logs = baseObj.logs
        pass

    def insert(self, newAdmin: df.MAdmin) -> bool:

        result = False
        exist = False

        for record in self.UID_ADMIN_DB:
            if record.uid == newAdmin.uid:
                # If the admin exist then return False and do not go further
                exist = True
                self.Logs.debug(f'{record.uid} already exist')
                return result

        if not exist:
            self.UID_ADMIN_DB.append(newAdmin)
            result = True
            self.Logs.debug(f'UID ({newAdmin.uid}) has been created')

        if not result:
            self.Logs.critical(f'The User Object was not inserted {newAdmin}')

        return result

    def update_nickname(self, uid: str, newNickname: str) -> bool:

        result = False

        if not self.is_exist(uid):
            return result

        for record in self.UID_ADMIN_DB:
            if record.uid == uid:
                # If the admin exist, update and do not go further
                record.nickname = newNickname
                result = True
                self.Logs.debug(f'UID ({record.uid}) has been updated with new nickname {newNickname}')
                return result

        if not result:
            self.Logs.critical(f'Admin: The new nickname {newNickname} was not updated, uid = {uid}')

        return result

    def update_level(self, nickname: str, newLevel: int) -> bool:

        result = False

        for record in self.UID_ADMIN_DB:
            if record.nickname == nickname:
                # If the admin exist, update and do not go further
                record.level = newLevel
                result = True
                self.Logs.debug(f'Admin ({record.nickname}) has been updated with new level {newLevel}')
                return result

        if not result:
            self.Logs.critical(f'The new level {newLevel} was not updated, nickname = {nickname}')

        return result

    def delete(self, uidornickname: str) -> bool:

        result = False

        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                # If the admin exist, delete and do not go further
                self.UID_ADMIN_DB.remove(record)
                result = True
                self.Logs.debug(f'UID ({record.uid}) has been deleted')
                return result
            if record.nickname == uidornickname:
                # If the admin exist, delete and do not go further
                self.UID_ADMIN_DB.remove(record)
                result = True
                self.Logs.debug(f'nickname ({record.nickname}) has been deleted')
                return result

        if not result:
            self.Logs.critical(f'The UID {uidornickname} was not deleted')

        return result

    def get_Admin(self, uidornickname: str) -> Union[df.MAdmin, None]:

        Admin = None
        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                Admin = record
            elif record.nickname == uidornickname:
                Admin = record

        #self.Logs.debug(f'Search {uidornickname} -- result = {Admin}')

        return Admin

    def get_uid(self, uidornickname:str) -> Union[str, None]:

        uid = None
        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                uid = record.uid
            if record.nickname == uidornickname:
                uid = record.uid

        self.Logs.debug(f'The UID that you are looking for {uidornickname} has been found {uid}')
        return uid

    def get_nickname(self, uidornickname:str) -> Union[str, None]:

        nickname = None
        for record in self.UID_ADMIN_DB:
            if record.nickname == uidornickname:
                nickname = record.nickname
            if record.uid == uidornickname:
                nickname = record.nickname
        self.Logs.debug(f'The value {uidornickname} -- {nickname}')
        return nickname

    def is_exist(self, uidornickname: str) -> bool:
        """Check if this uid or nickname is logged in as an admin

        Args:
            uidornickname (str): The UID or the Nickname

        Returns:
            bool: True if the Nickname or UID is an admin
        """
        if self.get_Admin(uidornickname) is None:
            return False
        else:
            return True