from typing import TYPE_CHECKING
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
        self.__protocols = {'unreal6': Unrealircd6,
                            'inspircd': Inspircd}

    def get(self) -> IProtocol:
        """Get the requested protocol instance.

        Raises:
            ValueError: If the protocol is not supported.

        Returns:
            IProtocol: The requested protocol instance.
        """
        protocol = self.__ctx.Config.SERVEUR_PROTOCOL
        _proto_class = self.__protocols.get(protocol.lower())

        if _proto_class is None:
            raise ValueError(f'Unsupported IRCd: {protocol}')

        return _proto_class(self.__ctx)
