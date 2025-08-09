from typing import Optional
from core.base import Base
import core.definition as df

class Admin:

    UID_ADMIN_DB: list[df.MAdmin] = []

    def __init__(self, base: Base) -> None:
        self.Logs = base.logs

    def insert(self, new_admin: df.MAdmin) -> bool:

        result = False
        exist = False

        for record in self.UID_ADMIN_DB:
            if record.uid == new_admin.uid:
                # If the admin exist then return False and do not go further
                exist = True
                self.Logs.debug(f'{record.uid} already exist')
                return result

        if not exist:
            self.UID_ADMIN_DB.append(new_admin)
            result = True
            self.Logs.debug(f'UID ({new_admin.uid}) has been created')

        if not result:
            self.Logs.critical(f'The User Object was not inserted {new_admin}')

        return result

    def update_nickname(self, uid: str, new_admin_nickname: str) -> bool:

        result = False

        for record in self.UID_ADMIN_DB:
            if record.uid == uid:
                # If the admin exist, update and do not go further
                record.nickname = new_admin_nickname
                result = True
                self.Logs.debug(f'UID ({record.uid}) has been updated with new nickname {new_admin_nickname}')
                return result

        if not result:
            self.Logs.debug(f'The new nickname {new_admin_nickname} was not updated, uid = {uid} - The Client is not an admin')

        return result

    def update_level(self, nickname: str, new_admin_level: int) -> bool:

        result = False

        for record in self.UID_ADMIN_DB:
            if record.nickname == nickname:
                # If the admin exist, update and do not go further
                record.level = new_admin_level
                result = True
                self.Logs.debug(f'Admin ({record.nickname}) has been updated with new level {new_admin_level}')
                return result

        if not result:
            self.Logs.debug(f'The new level {new_admin_level} was not updated, nickname = {nickname} - The Client is not an admin')

        return result

    def delete(self, uidornickname: str) -> bool:

        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                # If the admin exist, delete and do not go further
                self.UID_ADMIN_DB.remove(record)
                self.Logs.debug(f'UID ({record.uid}) has been deleted')
                return True
            if record.nickname == uidornickname:
                # If the admin exist, delete and do not go further
                self.UID_ADMIN_DB.remove(record)
                self.Logs.debug(f'nickname ({record.nickname}) has been deleted')
                return True

        self.Logs.critical(f'The UID {uidornickname} was not deleted')

        return False

    def get_Admin(self, uidornickname: str) -> Optional[df.MAdmin]:

        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                return record
            elif record.nickname == uidornickname:
                return record

        return None

    def get_uid(self, uidornickname:str) -> Optional[str]:

        for record in self.UID_ADMIN_DB:
            if record.uid == uidornickname:
                return record.uid
            if record.nickname == uidornickname:
                return record.uid

        return None

    def get_nickname(self, uidornickname:str) -> Optional[str]:

        for record in self.UID_ADMIN_DB:
            if record.nickname == uidornickname:
                return record.nickname
            if record.uid == uidornickname:
                return record.nickname

        return None