from typing import TYPE_CHECKING
from starlette.responses import JSONResponse
from core.classes.interfaces.irpc_endpoint import IRPC
from core.classes.modules.rpc.rpc_errors import JSONRPCErrorCode

if TYPE_CHECKING:
    from core.loader import Loader

class RPCCommand(IRPC):
    def __init__(self, loader: 'Loader'):
        super().__init__(loader)
    
    def command_list(self, **kwargs) -> JSONResponse:
        self.reset()
        self.response_model['result'] = [command.to_dict() for command in self.ctx.Commands.DB_COMMANDS]
        return JSONResponse(self.response_model)
    
    def command_get_by_module(self, **kwargs) -> JSONResponse:
        self.reset()
        module_name: str = kwargs.get('module_name', '')

        if not module_name:
            self.response_model['error'] = self.create_error_response(JSONRPCErrorCode.INVALID_PARAMS, {'module_name': 'The param to use is module_name'})
            return JSONResponse(self.response_model, self.http_status_code.HTTP_405_METHOD_NOT_ALLOWED)

        self.response_model['result'] = [command.to_dict() for command in self.ctx.Commands.DB_COMMANDS if command.module_name.lower() == module_name.lower()]
        return JSONResponse(self.response_model)

    def command_get_by_name(self, **kwargs) -> JSONResponse:
        self.reset()

        command_name: str = kwargs.get('command_name', '')
        if not command_name:
            self.response_model['error'] = self.create_error_response(JSONRPCErrorCode.INVALID_PARAMS, {'command_name': f'The param to use is command_name'})
            return JSONResponse(self.response_model, self.http_status_code.HTTP_405_METHOD_NOT_ALLOWED)

        command_to_return: list[dict] = []
        for command in self.ctx.Commands.DB_COMMANDS:
            if command.command_name.lower() == command_name.lower():
                command_to_return.append(command.to_dict())
        
        self.response_model['result'] = command_to_return

        return JSONResponse(self.response_model)