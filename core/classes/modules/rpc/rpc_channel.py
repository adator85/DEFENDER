from typing import TYPE_CHECKING
from starlette.responses import JSONResponse
from core.classes.interfaces.irpc_endpoint import IRPC

if TYPE_CHECKING:
    from core.loader import Loader

class RPCChannel(IRPC):
    def __init__(self, loader: 'Loader'):
        super().__init__(loader)
    
    def channel_list(self) -> JSONResponse:
        self.reset()
        self.response_model['result'] = [chan.to_dict() for chan in self.ctx.Channel.UID_CHANNEL_DB]
        return JSONResponse(self.response_model)
