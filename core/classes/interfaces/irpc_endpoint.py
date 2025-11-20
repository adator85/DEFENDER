import starlette.status as http_status_code
from typing import TYPE_CHECKING
from core.classes.modules.rpc.rpc_errors import JSONRPCErrorCode

if TYPE_CHECKING:
    from core.loader import Loader

class IRPC:

    def __init__(self, loader: 'Loader'):
        self.ctx = loader
        self.http_status_code = http_status_code
        self.response_model = {
            "jsonrpc": "2.0",
            "id": 123
        }
    
    def reset(self):
        self.response_model = {
            "jsonrpc": "2.0",
            "id": 123
        }

    def create_error_response(self, error_code: JSONRPCErrorCode, details: dict = None) -> dict[str, str]:
        """Create a JSON-RPC error!"""
        response = {
                "code": error_code.value,
                "message": error_code.description(),
            }
        
        if details:
            response["data"] = details
        
        return response