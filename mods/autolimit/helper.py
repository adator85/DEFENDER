from typing import Optional, TYPE_CHECKING

from requests.utils import is_valid_cidr
from mods.autolimit.schemas import ALChannel

if TYPE_CHECKING:
    from mods.autolimit.mod_autolimit import Autolimit

class ALHelper:

    def __init__(self, uplink: 'Autolimit'):
        self._ctx = uplink
        self._base = uplink.ctx.Base
        self.db_channels: list[ALChannel] = uplink.DB_AL_CHANNELS
    
    async def init(self) -> None:
        # Get information from database
        _query = 'SELECT channel, amount, interval FROM autolimit_channels'
        _cresults = await self._base.db_execute_query(_query)
        results = _cresults.fetchall()
        for result in results:
            _channel, _amount, _interval = result
            self.insert_al_channel(ALChannel(_channel, _amount, _interval))

    def insert_al_channel(self, obj: ALChannel) -> bool:

        if self.get_al_channel(obj.channel.lower()) is not None:
            return False

        if not self._ctx.ctx.Channel.is_valid_channel(obj.channel):
            return False

        self._ctx.DB_AL_CHANNELS.append(obj)
        return True
    
    def get_al_channel(self, channel_name: str) -> Optional[ALChannel]:
        if channel_name is None:
            return None

        for alchan in self._ctx.DB_AL_CHANNELS:
            if alchan.channel.lower() == channel_name.lower():
                return alchan

        return None

    def remove_al_channel(self, channel_name: str) -> bool:
        if channel_name is None:
            return bool

        _channel = self.get_al_channel(channel_name)
        if _channel is None:
            return False

        self._ctx.DB_AL_CHANNELS.remove(_channel)

        return True