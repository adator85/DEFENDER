import base64
import json
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route
import uvicorn
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from core.classes.modules.rpc.rpc_user import RPCUser
from core.classes.modules.rpc.rpc_channel import RPCChannel
from core.classes.modules.rpc.rpc_command import RPCCommand

if TYPE_CHECKING:
    from core.loader import Loader

class JSonRpcServer:

    def __init__(self, context: 'Loader', *, hostname: str = 'localhost', port: int = 5000):
        self._ctx = context
        self.live: bool = False
        self.host = hostname
        self.port = port
        self.routes: list[Route] = []
        self.server: Optional[uvicorn.Server] = None

        self.methods: dict = {
            'user.list': RPCUser(context).user_list,
            'user.get': RPCUser(context).user_get,
            'channel.list': RPCChannel(context).channel_list,
            'command.list': RPCCommand(context).command_list,
            'command.get.by.name': RPCCommand(context).command_get_by_name,
            'command.get.by.module': RPCCommand(context).command_get_by_module
        }

    async def start_server(self):

        if not self.live:
            self.routes = [Route('/api', self.request_handler, methods=['POST'])]
            self.app_jsonrpc = Starlette(debug=False, routes=self.routes)
            config = uvicorn.Config(self.app_jsonrpc, host=self.host, port=self.port, log_level=self._ctx.Config.DEBUG_LEVEL)
            self.server = uvicorn.Server(config)
            self.live = True
            await self._ctx.Irc.Protocol.send_priv_msg(
                self._ctx.Config.SERVICE_NICKNAME,
                "[DEFENDER JSONRPC SERVER] RPC Server started!",
                self._ctx.Config.SERVICE_CHANLOG
            )
            await self.server.serve()
            self._ctx.Logs.debug("Server is going to shutdown!")
        else:
            self._ctx.Logs.debug("Server already running")
    
    async def stop_server(self):
        
        if self.server:
            self.server.should_exit = True
            await self.server.shutdown()
            self.live = False
            self._ctx.Logs.debug("JSON-RPC Server off!")
            await self._ctx.Irc.Protocol.send_priv_msg(
                self._ctx.Config.SERVICE_NICKNAME,
                "[DEFENDER JSONRPC SERVER] RPC Server Stopped!",
                self._ctx.Config.SERVICE_CHANLOG
            )

    async def request_handler(self, request: Request) -> JSONResponse:

        request_data: dict = await request.json()
        method = request_data.get("method", None)
        params: dict[str, Any] = request_data.get("params", {})

        auth: JSONResponse = self.authenticate(request.headers, request_data)        
        if not json.loads(auth.body).get('result', False):
            return auth

        response_data = {
            "jsonrpc": "2.0",
            "id": request_data.get('id', 123)
        }

        response_data['method'] = method
        rip = request.client.host
        rport = request.client.port
        http_code = 200

        if method in self.methods:
            response_data['result'] = self.methods[method](**params)
            return JSONResponse(response_data, http_code)

        response_data['error'] = create_error_response(JSONRPCErrorCode.METHOD_NOT_FOUND)
        self._ctx.Logs.debug(f'[RPC ERROR] {method} recieved from {rip}:{rport}')
        http_code = 404
        return JSONResponse(response_data, http_code)

    def authenticate(self, headers: dict, body: dict) -> JSONResponse:
        ok_auth = {
            'jsonrpc': '2.0',
            'id': body.get('id', 123),
            'result': True
        }

        logs = self._ctx.Logs
        auth: str = headers.get('Authorization', '')
        if not auth:
            return self.send_auth_error(body)
        
        # Authorization header format: Basic base64(username:password)
        auth_type, auth_string = auth.split(' ', 1)
        if auth_type.lower() != 'basic':
            return self.send_auth_error(body)

        try:
            # Decode the base64-encoded username:password
            decoded_credentials = base64.b64decode(auth_string).decode('utf-8')
            username, password = decoded_credentials.split(":", 1)
            
            # Check the username and password.
            for rpcuser in self._ctx.Config.RPC_USERS:
                if rpcuser.get('USERNAME', None) == username and rpcuser.get('PASSWORD', None) == password:
                    return JSONResponse(ok_auth)

            return self.send_auth_error(body)

        except Exception as e:
            logs.error(e)
            return self.send_auth_error(body)
   
    def send_auth_error(self, request_data: dict) -> JSONResponse:
     
        response_data = {
            'jsonrpc': '2.0',
            'id': request_data.get('id', 123),
            'error': create_error_response(JSONRPCErrorCode.AUTHENTICATION_ERROR)
        }
        return JSONResponse(response_data)


class JSONRPCErrorCode(Enum):
    PARSE_ERROR = -32700      # Syntax error in the request (malformed JSON)
    INVALID_REQUEST = -32600  # Invalid Request (incorrect structure or missing fields)
    METHOD_NOT_FOUND = -32601 # Method not found (the requested method does not exist)
    INVALID_PARAMS = -32602   # Invalid Params (the parameters provided are incorrect)
    INTERNAL_ERROR = -32603   # Internal Error (an internal server error occurred)
    
    # Custom application-specific errors (beyond standard JSON-RPC codes)
    CUSTOM_ERROR = 1001       # Custom application-defined error (e.g., user not found)
    AUTHENTICATION_ERROR = 1002 # Authentication failure (e.g., invalid credentials)
    PERMISSION_ERROR = 1003   # Permission error (e.g., user does not have access to this method)
    RESOURCE_NOT_FOUND = 1004 # Resource not found (e.g., the requested resource does not exist)
    DUPLICATE_REQUEST = 1005  # Duplicate request (e.g., a similar request has already been processed)
    
    def description(self):
        """Returns a description associated with each error code"""
        descriptions = {
            JSONRPCErrorCode.PARSE_ERROR: "The JSON request is malformed.",
            JSONRPCErrorCode.INVALID_REQUEST: "The request is invalid (missing or incorrect fields).",
            JSONRPCErrorCode.METHOD_NOT_FOUND: "The requested method could not be found.",
            JSONRPCErrorCode.INVALID_PARAMS: "The parameters provided are invalid.",
            JSONRPCErrorCode.INTERNAL_ERROR: "An internal error occurred on the server.",
            JSONRPCErrorCode.CUSTOM_ERROR: "A custom error defined by the application.",
            JSONRPCErrorCode.AUTHENTICATION_ERROR: "User authentication failed.",
            JSONRPCErrorCode.PERMISSION_ERROR: "User does not have permission to access this method.",
            JSONRPCErrorCode.RESOURCE_NOT_FOUND: "The requested resource could not be found.",
            JSONRPCErrorCode.DUPLICATE_REQUEST: "The request is a duplicate or is already being processed.",
        }
        return descriptions.get(self, "Unknown error")

def create_error_response(error_code: JSONRPCErrorCode, details: dict = None) -> dict[str, str]:
    """Create a JSON-RPC error!"""
    response = {
            "code": error_code.value,
            "message": error_code.description(),
        }
    
    if details:
        response["data"] = details
    
    return response