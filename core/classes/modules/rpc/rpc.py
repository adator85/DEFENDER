import base64
import json
import logging
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, Any, Optional
from core.classes.modules.rpc.rpc_user import RPCUser
from core.classes.modules.rpc.rpc_channel import RPCChannel
from core.classes.modules.rpc.rpc_command import RPCCommand

if TYPE_CHECKING:
    from core.loader import Loader

ProxyLoader: Optional['Loader'] = None

class RPCRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        logs = ProxyLoader.Logs
        self.server_version = 'Defender6'
        self.sys_version = ProxyLoader.Config.CURRENT_VERSION
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request_data: dict = json.loads(body)
        rip, rport = self.client_address

        if not self.authenticate(request_data):
            return None

        response_data = {
            'jsonrpc': '2.0',
            'id': request_data.get('id', 123)
        }

        method = request_data.get("method")
        params: dict[str, Any] = request_data.get("params", {})
        response_data['method'] = method
        http_code = 200

        match method:
            case 'user.list':
                user = RPCUser(ProxyLoader)
                response_data['result'] = user.user_list()
                logs.debug(f'[RPC] {method} recieved from {rip}:{rport}')
                del user
            
            case 'user.get':
                user = RPCUser(ProxyLoader)
                uid_or_nickname = params.get('uid_or_nickname', None)
                response_data['result'] = user.user_get(uid_or_nickname)
                logs.debug(f'[RPC] {method} recieved from {rip}:{rport}')
                del user

            case 'channel.list':
                channel = RPCChannel(ProxyLoader)
                response_data['result'] = channel.channel_list()
                logs.debug(f'[RPC] {method} recieved from {rip}:{rport}')
                del channel

            case 'command.list':
                command = RPCCommand(ProxyLoader)
                response_data['result'] = command.command_list()
                logs.debug(f'[RPC] {method} recieved from {rip}:{rport}')
                del command

            case 'command.get.by.module':
                command = RPCCommand(ProxyLoader)
                module_name = params.get('name', None)
                response_data['result'] = command.command_get_by_module(module_name)
                logs.debug(f'[RPC] {method} recieved from {rip}:{rport}')
                del command

            case 'command.get.by.name':
                command = RPCCommand(ProxyLoader)
                command_name = params.get('name', None)
                response_data['result'] = command.command_get_by_name(command_name)
                logs.debug(f'[RPC] {method} recieved from {rip}:{rport}')
                del command

            case _:
                response_data['error'] = create_error_response(JSONRPCErrorCode.METHOD_NOT_FOUND)
                logs.debug(f'[RPC ERROR] {method} recieved from {rip}:{rport}')
                http_code = 404

        self.send_response(http_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

        return None

    def do_GET(self):
        self.server_version = 'Defender6'
        self.sys_version = ProxyLoader.Config.CURRENT_VERSION
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request_data: dict = json.loads(body)
        
        if not self.authenticate(request_data):
            return None

        response_data = {'jsonrpc': '2.0', 'id': request_data.get('id', 321),
                         'error': create_error_response(JSONRPCErrorCode.INVALID_REQUEST)}

        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

        return None


    def authenticate(self, request_data: dict) -> bool:
        logs = ProxyLoader.Logs
        auth = self.headers.get('Authorization', None)
        if auth is None:
            self.send_auth_error(request_data)
            return False
        
        # Authorization header format: Basic base64(username:password)
        auth_type, auth_string = auth.split(' ', 1)
        if auth_type.lower() != 'basic':
            self.send_auth_error(request_data)
            return False

        try:
            # Decode the base64-encoded username:password
            decoded_credentials = base64.b64decode(auth_string).decode('utf-8')
            username, password = decoded_credentials.split(":", 1)
            
            # Check the username and password.
            for rpcuser in ProxyLoader.Irc.Config.RPC_USERS:
                if rpcuser.get('USERNAME', None) == username and rpcuser.get('PASSWORD', None) == password:
                    return True

            self.send_auth_error(request_data)
            return False

        except Exception as e:
            self.send_auth_error(request_data)
            logs.error(e)
            return False
   
    def send_auth_error(self, request_data: dict) -> None:
     
        response_data = {
            'jsonrpc': '2.0',
            'id': request_data.get('id', 123),
            'error': create_error_response(JSONRPCErrorCode.AUTHENTICATION_ERROR)
        }

        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Authorization Required"')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

class JSONRPCServer:
    def __init__(self, loader: 'Loader'):
        global ProxyLoader

        ProxyLoader = loader
        self._Loader = loader
        self._Base = loader.Base
        self._Logs = loader.Logs
        self.rpc_server: Optional[HTTPServer] = None
        self.connected: bool = False

    def start_server(self, server_class=HTTPServer, handler_class=RPCRequestHandler, *, hostname: str = 'localhost', port: int = 5000):
        logging.getLogger('http.server').setLevel(logging.CRITICAL)
        server_address = (hostname, port)
        self.rpc_server = server_class(server_address, handler_class)
        self._Logs.debug(f"Server ready on http://{hostname}:{port}...")
        self._Base.create_thread(self.thread_start_rpc_server, (), True)

    def thread_start_rpc_server(self) -> None:
        self._Loader.Irc.Protocol.send_priv_msg(
            self._Loader.Config.SERVICE_NICKNAME, "Defender RPC Server has started successfuly!", self._Loader.Config.SERVICE_CHANLOG
        )
        self.connected = True
        self.rpc_server.serve_forever()
        ProxyLoader.Logs.debug(f"RPC Server down!")

    def stop_server(self):
        self._Base.create_thread(self.thread_stop_rpc_server)
    
    def thread_stop_rpc_server(self):
        self.rpc_server.shutdown()
        ProxyLoader.Logs.debug(f"RPC Server shutdown!")
        self.rpc_server.server_close()
        ProxyLoader.Logs.debug(f"RPC Server clean-up!")
        self._Base.garbage_collector_thread()
        self._Loader.Irc.Protocol.send_priv_msg(
            self._Loader.Config.SERVICE_NICKNAME, "Defender RPC Server has stopped successfuly!", self._Loader.Config.SERVICE_CHANLOG
        )
        self.connected = False

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