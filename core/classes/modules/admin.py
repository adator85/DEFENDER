from typing import TYPE_CHECKING, Optional
from core.definition import MAdmin, MUser

if TYPE_CHECKING:
    from core.loader import Loader

class Admin:

    def __init__(self, loader: 'Loader') -> None:
        """
        Args:
            loader (Loader): The Loader Instance.
        """
        self._ctx = loader
        self.UID_ADMIN_DB: list[MAdmin] = []

    def insert(self, new_admin: MAdmin) -> bool:
        """Insert a new admin object model

        Args:
            new_admin (MAdmin): The new admin object model to insert

        Returns:
            bool: True if it was inserted
        """

        for record in self.UID_ADMIN_DB:
            if record.uid == new_admin.uid:
                self._ctx.Logs.debug('[ ADMIN ] %s already exist', record.uid)
                return False

        self.UID_ADMIN_DB.append(new_admin)
        self._ctx.Logs.debug('[ ADMIN ] New admin (%s) has been created', new_admin.nickname)
        return True

    def insert_from_client(self, client: MUser, account: str, level: int, language: str | None = None) -> bool:
        """Insert a new admin into the MAdmin object using the client (MUser) object.

        Args:
            client (MUser): The client object
            account (str): The account name.
            level (int): The level of the admin
            language (str): The language of the admin

        Returns:
            bool: True if success.
        """
        if not client:
            return False

        language = language or self._ctx.Settings.global_lang

        _admin = MAdmin(**client.to_dict(),
                        language=language,
                        account=account,
                        level=int(level))

        if self.insert(_admin):
            self._ctx.Settings.current_admin = _admin
            return True

        return False

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
                self._ctx.Logs.debug('[ ADMIN ] UID (%s) has been updated with new nickname %s',
                                     record.uid, new_admin_nickname)
                return True


        self._ctx.Logs.debug('[ ADMIN ] The new nickname %s was not updated, '
                             'uid = %s - The Client is not an admin',
                             new_admin_nickname, uid)
        return False

    def update_level(self, nickname: str, new_admin_level: int) -> bool:
        """Update the admin level

        Args:
            nickname (str): The admin nickname
            new_admin_level (int): The new level of the admin

        Returns:
            bool: True if the admin level has been updated
        """
        admin_obj = self.get_admin(nickname)
        if admin_obj:
            # If the admin exist, update and do not go further
            admin_obj.level = new_admin_level
            self._ctx.Logs.debug('[ ADMIN ] Admin (%s) has been updated with new level %s',
                                 admin_obj.nickname, new_admin_level)
            return True

        self._ctx.Logs.debug('[ ADMIN ] The new level %s was not updated in local variable, '
                             'nickname = %s is not logged in!',
                             new_admin_level, nickname)

        return False

    def delete(self, uidornickname: str) -> bool:
        """Delete admin

        Args:
            uidornickname (str): The UID or nickname of the admin

        Returns:
            bool: True if the admin has been deleted
        """
        admin_obj = self.get_admin(uidornickname)
        if admin_obj:
            self.UID_ADMIN_DB.remove(admin_obj)
            self._ctx.Logs.debug('[ ADMIN ] UID (%s) has been deleted',
                                 admin_obj.uid)
            return True

        self._ctx.Logs.debug('[ ADMIN ] The UID %s was not deleted '
                             'from the local variable (admin not connected)',
                             uidornickname)

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
    
    def get_language(self, uidornickname: str) -> Optional[str]:
        """Get the language of the admin

        Args:
            uidornickname (str): The user ID or the Nickname of the admin

        Returns:
            Optional[str]: The language selected by the admin.
        """
        admin = self.get_admin(uidornickname)

        if admin is None:
            return None

        return admin.language

    async def db_auth_admin_via_fingerprint(self, fp: str, uidornickname: str) -> bool:
        """Check the fingerprint

        Args:
            fp (str): The unique fingerprint of the user
            uidornickname (str): The UID or the Nickname of the user

        Returns:
            bool: True if found
        """
        if not fp:
            return False

        query = f"SELECT user, level, language FROM {self._ctx.Config.TABLE_ADMIN} WHERE fingerprint = :fp"
        data = {'fp': fp}
        exe = await self._ctx.Base.db_execute_query(query, data)
        result = exe.fetchone()
        if result:
            account = result[0]
            level = result[1]
            language = result[2]
            user_obj = self._ctx.User.get_user(uidornickname)
            if user_obj:
                admin_obj = self._ctx.Definition.MAdmin(**user_obj.to_dict(), account=account, level=level, language=language)
                if self.insert(admin_obj):
                    self._ctx.Settings.current_admin = admin_obj
                    self._ctx.Logs.debug("[ ADMIN ] %s (%s) has been logged in successfully using fingerprint!",
                                         user_obj.nickname, admin_obj.account)
                    return True
        
        return False

    async def db_auth_admin_legacy(self, client: MUser, account: str, password: str) -> bool:
        """Admin authentication legacy.

        Args:
            client (MUser): The Client object
            account (str): The account name.
            password (str): The password

        Returns:
            bool: True if success.
        """
        mes_donnees = {'user': account, 'password': self._ctx.Utils.hash_password(password)}
        query = f"SELECT id, user, level, language FROM {self._ctx.Config.TABLE_ADMIN} WHERE user = :user AND password = :password"
        result = await self._ctx.Base.db_execute_query(query, mes_donnees)
        user_from_db = result.fetchone()

        if user_from_db:
            account = str(user_from_db[1])
            level = int(user_from_db[2])
            language = user_from_db[3] or self._ctx.Settings.global_lang

            _admin = MAdmin(
                    **client.to_dict(),
                    language=language,
                    account=account,
                    level=int(level)
                )

            if self.insert(_admin):
                self._ctx.Settings.current_admin = _admin
                return True

        return False

    async def db_is_admin_exist(self, admin_nickname: str) -> bool:
        """Verify if the admin exist in the database!

        Args:
            admin_nickname (str): The nickname admin to check.

        Returns:
            bool: True if the admin exist otherwise False.
        """

        mes_donnees = {'admin': admin_nickname}
        query_search_user = f"SELECT id FROM {self._ctx.Config.TABLE_ADMIN} WHERE user = :admin"
        r = await self._ctx.Base.db_execute_query(query_search_user, mes_donnees)
        exist_user = r.fetchone()
        if exist_user:
            return True
        else:
            return False
