from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.loader import Loader
    from core.definition import MUser

class RPCUser:
    def __init__(self, loader: 'Loader'):
        self._ctx = loader
    
    def user_list(self, **kwargs) -> list[dict]:
        users = self._ctx.User.UID_DB.copy()
        copy_users: list['MUser'] = []

        for user in users:
            copy_user = user.copy()
            copy_user.connexion_datetime = copy_user.connexion_datetime.strftime('%d-%m-%Y')
            copy_users.append(copy_user)
        
        return [user.to_dict() for user in copy_users]

    def user_get(self, **kwargs) -> Optional[dict]:
        uidornickname = kwargs.get('uid_or_nickname', None)
        user = self._ctx.User.get_user(uidornickname)
        if user:
            user_copy = user.copy()
            user_copy.connexion_datetime = user_copy.connexion_datetime.strftime('%d-%m-%Y')
            return user_copy.to_dict()
        
        return None