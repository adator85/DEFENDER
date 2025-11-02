from typing import TYPE_CHECKING, Optional
from .unreal6 import Unrealircd6
from .inspircd import Inspircd
from ..interfaces.iprotocol import IProtocol

if TYPE_CHECKING:
    from core.irc import Irc

class ProtocolFactorty:

    def __init__(self, uplink: 'Irc'):
        """ProtocolFactory init.

        Args:
            uplink (Irc): The Irc object
        """
        self.__Config = uplink.Config
        self.__uplink = uplink

    def get(self) -> Optional[IProtocol]:

        protocol = self.__Config.SERVEUR_PROTOCOL

        match protocol:
            case 'unreal6':
                self.__uplink.Logs.debug(f"[PROTOCOL] {protocol} has been loaded")
                return Unrealircd6(self.__uplink)
            case 'inspircd':
                self.__uplink.Logs.debug(f"[PROTOCOL] {protocol} has been loaded")
                return Inspircd(self.__uplink)
            case _:
                self.__uplink.Logs.critical(f"[PROTOCOL ERROR] This protocol name ({protocol} is not valid!)")
                raise Exception("Unknown protocol!")
