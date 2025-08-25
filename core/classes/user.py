from re import sub
from typing import Any, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from core.loader import Loader
    from core.definition import MUser

class User:

    UID_DB: list['MUser'] = []

    @property
    def get_current_user(self) -> 'MUser':
        return self.current_user

    def __init__(self, loader: 'Loader'):

        self.Logs = loader.Logs
        self.Base = loader.Base
        self.current_user: Optional['MUser'] = None

    def insert(self, new_user: 'MUser') -> bool:
        """Insert a new User object

        Args:
            newUser (UserModel): New userModel object

        Returns:
            bool: True if inserted
        """

        user_obj = self.get_user(new_user.uid)
        if not user_obj is None:
            # User already created return False
            return False

        self.UID_DB.append(new_user)

        return True

    def update_nickname(self, uid: str, new_nickname: str) -> bool:
        """Update the nickname starting from the UID

        Args:
            uid (str): UID of the user
            new_nickname (str): New nickname

        Returns:
            bool: True if updated
        """
        user_obj = self.get_user(uidornickname=uid)

        if user_obj is None:
            return False

        user_obj.nickname = new_nickname

        return True

    def update_mode(self, uidornickname: str, modes: str) -> bool:
        """Updating user mode

        Args:
            uidornickname (str): The UID or Nickname of the user
            modes (str): new modes to update

        Returns:
            bool: True if user mode has been updaed
        """
        response = True
        user_obj = self.get_user(uidornickname=uidornickname)

        if user_obj is None:
            return False

        action = modes[0]
        new_modes = modes[1:]

        existing_umodes = user_obj.umodes
        umodes = user_obj.umodes

        if action == '+':

            for nm in new_modes:
                if nm not in existing_umodes:
                    umodes += nm

        elif action == '-':
            for nm in new_modes:
                if nm in existing_umodes:
                    umodes = umodes.replace(nm, '')
        else:
            return False

        liste_umodes = list(umodes)
        final_umodes_liste = [x for x in self.Base.Settings.PROTOCTL_USER_MODES if x in liste_umodes]
        final_umodes = ''.join(final_umodes_liste)

        user_obj.umodes = f"+{final_umodes}"

        return response

    def delete(self, uid: str) -> bool:
        """Delete the User starting from the UID

        Args:
            uid (str): UID of the user

        Returns:
            bool: True if deleted
        """

        user_obj = self.get_user(uidornickname=uid)

        if user_obj is None:
            return False

        self.UID_DB.remove(user_obj)

        return True

    def get_user(self, uidornickname: str) -> Optional['MUser']:
        """Get The User Object model

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            UserModel|None: The UserModel Object | None
        """
        for record in self.UID_DB:
            if record.uid == uidornickname:
                self.current_user = record
                return record
            elif record.nickname == uidornickname:
                self.current_user = record
                return record

        return None

    def get_uid(self, uidornickname:str) -> Optional[str]:
        """Get the UID of the user starting from the UID or the Nickname

        Args:
            uidornickname (str): UID or Nickname

        Returns:
            str|None: Return the UID
        """

        user_obj = self.get_user(uidornickname=uidornickname)

        if user_obj is None:
            return None

        self.current_user = user_obj
        return user_obj.uid

    def get_nickname(self, uidornickname:str) -> Optional[str]:
        """Get the Nickname starting from UID or the nickname

        Args:
            uidornickname (str): UID or Nickname of the user

        Returns:
            str|None: the nickname
        """
        user_obj = self.get_user(uidornickname=uidornickname)

        if user_obj is None:
            return None

        self.current_user = user_obj
        return user_obj.nickname

    def get_user_asdict(self, uidornickname: str) -> Optional[dict[str, Any]]:
        """Transform User Object to a dictionary

        Args:
            uidornickname (str): The UID or The nickname

        Returns:
            Union[dict[str, any], None]: User Object as a dictionary or None
        """
        user_obj = self.get_user(uidornickname=uidornickname)

        if user_obj is None:
            return None

        return user_obj.to_dict()

    def is_exist(self, uidornikname: str) -> bool:
        """Check if the UID or the nickname exist in the USER DB

        Args:
            uidornickname (str): The UID or the NICKNAME

        Returns:
            bool: True if exist
        """
        user_obj = self.get_user(uidornickname=uidornikname)

        if user_obj is None:
            return False

        return True

    def clean_uid(self, uid: str) -> Optional[str]:
        """Clean UID by removing @ / % / + / ~ / * / :

        Args:
            uid (str): The UID to clean

        Returns:
            str: Clean UID without any sign
        """

        pattern = fr'[:|@|%|\+|~|\*]*'
        parsed_UID = sub(pattern, '', uid)

        if not parsed_UID:
            return None

        return parsed_UID

    def get_user_uptime_in_minutes(self, uidornickname: str) -> float:
        """Retourne depuis quand l'utilisateur est connecté (in minutes).

        Args:
            uid (str): The uid or le nickname

        Returns:
            int: How long in minutes has the user been connected?
        """

        get_user = self.get_user(uidornickname)
        if get_user is None:
            return 0

        # Convertir la date enregistrée dans UID_DB en un objet {datetime}
        connected_time_string = get_user.connexion_datetime

        if isinstance(connected_time_string, datetime):
            connected_time = connected_time_string
        else:
            connected_time = datetime.strptime(connected_time_string, "%Y-%m-%d %H:%M:%S.%f")

        # What time is it ?
        current_datetime = datetime.now()

        uptime = current_datetime - connected_time
        convert_to_minutes = uptime.seconds / 60
        uptime_minutes = round(number=convert_to_minutes, ndigits=2)

        return uptime_minutes
