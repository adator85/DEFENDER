from typing import TYPE_CHECKING, Optional
from .unreal6 import Unrealircd6
from .inspircd import Inspircd
from ..interfaces.iprotocol import IProtocol

if TYPE_CHECKING:
    from core.loader import Loader

class ProtocolFactorty:

    def __init__(self, context: 'Loader'):
        """ProtocolFactory init.

        Args:
            context (Loader): The Context object
        """
        self.__ctx = context

    def get(self) -> Optional[IProtocol]:

        protocol = self.__ctx.Config.SERVEUR_PROTOCOL

        match protocol:
            case 'unreal6':
                self.__ctx.Logs.debug(f"[PROTOCOL] {protocol} has been loaded")
                return Unrealircd6(self.__ctx)
            case 'inspircd':
                self.__ctx.Logs.debug(f"[PROTOCOL] {protocol} has been loaded")
                return Inspircd(self.__ctx)
            case _:
                self.__ctx.Logs.critical(f"[PROTOCOL ERROR] This protocol name ({protocol} is not valid!)")
                raise Exception("Unknown protocol!")
