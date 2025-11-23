import base64
import json
import uvicorn
import core.classes.modules.rpc.rpc_errors as rpcerr
import starlette.status as http_status_code
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route
from typing import TYPE_CHECKING, Any, Optional
from core.classes.modules.rpc.rpc_user import RPCUser
from core.classes.modules.rpc.rpc_channel import RPCChannel
from core.classes.modules.rpc.rpc_command import RPCCommand

if TYPE_CHECKING:
    from core.loader import Loader

class JSonRpcServer:

    def __init__(self, context: 'Loader'):
        self._ctx = context
        self.live: bool = False
        self.host = context.Config.RPC_HOST
        self.port = context.Config.RPC_PORT
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

    async def start_rpc_server(self):

        if not self.live:
            self.routes = [Route('/api', self.request_handler, methods=['POST'])]
            self.app_jsonrpc = Starlette(debug=False, routes=self.routes)
            config = uvicorn.Config(self.app_jsonrpc, host=self.host, port=self.port, log_level=self._ctx.Config.DEBUG_LEVEL+10)
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
    
    async def stop_rpc_server(self):
        
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
            "method": method,
            "id": request_data.get('id', 123)
        }

        rip = request.client.host
        rport = request.client.port
        http_code = http_status_code.HTTP_200_OK

        if method in self.methods:
            r: JSONResponse = self.methods[method](**params)
            resp = json.loads(r.body)
            resp['id'] = request_data.get('id', 123)
            resp['method'] = method
            return JSONResponse(resp, r.status_code)

        response_data['error'] = rpcerr.create_error_response(rpcerr.JSONRPCErrorCode.METHOD_NOT_FOUND)
        self._ctx.Logs.debug(f'[RPC ERROR] {method} recieved from {rip}:{rport}')
        http_code = http_status_code.HTTP_404_NOT_FOUND
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
            'error': rpcerr.create_error_response(rpcerr.JSONRPCErrorCode.AUTHENTICATION_ERROR)
        }
        return JSONResponse(response_data, http_status_code.HTTP_403_FORBIDDEN)
