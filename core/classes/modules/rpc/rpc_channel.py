from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.loader import Loader

class RPCChannel:
    def __init__(self, loader: 'Loader'):
        self._Loader = loader
        self._Channel = loader.Channel
    
    def channel_list(self) -> list[dict]:
        return [chan.to_dict() for chan in self._Channel.UID_CHANNEL_DB]