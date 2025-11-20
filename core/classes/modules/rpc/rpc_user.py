from typing import TYPE_CHECKING, Optional

from starlette.responses import JSONResponse
from core.classes.interfaces.irpc_endpoint import IRPC
from core.classes.modules.rpc.rpc_errors import JSONRPCErrorCode

if TYPE_CHECKING:
    from core.loader import Loader
    from core.definition import MUser

class RPCUser(IRPC):
    def __init__(self, loader: 'Loader'):
        super().__init__(loader)
    
    def user_list(self, **kwargs) -> JSONResponse:
        self.reset()
        users = self.ctx.User.UID_DB.copy()
        copy_users: list['MUser'] = []

        for user in users:
            copy_user = user.copy()
            copy_user.connexion_datetime = copy_user.connexion_datetime.strftime('%d-%m-%Y')
            copy_users.append(copy_user)
        
        self.response_model['result'] = [user.to_dict() for user in copy_users]

        return JSONResponse(self.response_model)

    def user_get(self, **kwargs) -> JSONResponse:
        self.reset()
        uidornickname = kwargs.get('uid_or_nickname', '')

        if not uidornickname:
            self.response_model['error'] = self.create_error_response(JSONRPCErrorCode.INVALID_PARAMS, {'uid_or_nickname': 'The param to use is uid_or_nickname'})
            return JSONResponse(self.response_model, self.http_status_code.HTTP_405_METHOD_NOT_ALLOWED)

        user = self.ctx.User.get_user(uidornickname)
        if user:
            user_copy = user.copy()
            user_copy.connexion_datetime = user_copy.connexion_datetime.strftime('%d-%m-%Y')
            self.response_model['result'] = user_copy.to_dict()
            return JSONResponse(self.response_model)
        
        self.response_model['result'] = 'User not found!'
        return JSONResponse(self.response_model, self.http_status_code.HTTP_204_NO_CONTENT)