from typing import Literal, TYPE_CHECKING
from .protocols.unreal6 import Unrealircd6

if TYPE_CHECKING:
    from core.irc import Irc

class Protocol:

    def __init__(self, protocol: Literal['unreal6'], ircInstance: 'Irc'):

        self.Protocol = None
        if protocol == 'unreal6':
            self.Protocol: Unrealircd6 = Unrealircd6(ircInstance)
        else:
            self.Protocol = None