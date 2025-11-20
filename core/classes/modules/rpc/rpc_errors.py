from enum import Enum

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