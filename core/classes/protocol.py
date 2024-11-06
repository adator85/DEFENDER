from typing import Literal, TYPE_CHECKING
from .protocols.unreal6 import Unrealircd6
from .protocols.inspircd import Inspircd

if TYPE_CHECKING:
    from core.irc import Irc

class Protocol:

    def __init__(self, protocol: Literal['unreal6','inspircd'], ircInstance: 'Irc'):

        self.Protocol = None
        match protocol:
            case 'unreal6':
                self.Protocol: Unrealircd6 = Unrealircd6(ircInstance)
            case 'inspircd':
                self.Protocol: Inspircd = Inspircd(ircInstance)
            case _:
                self.Protocol: Unrealircd6 = Unrealircd6(ircInstance)
