import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional
from core.classes.interfaces.imodule import IModule
from core.definition import DTask, MChannel
from mods.autolimit import schemas
from mods.autolimit.helper import ALHelper

if TYPE_CHECKING:
    from core.loader import Loader

class Autolimit(IModule):

    DB_AL_CHANNELS: list[schemas.ALChannel] = []
    __TABLENAME__: str = 'autolimit_channels'

    MOD_HEADER: dict[str, str] = {
        'name':'Autolimit',
        'version':'0.0.1',
        'description':'Autolimit module',
        'author':'Defender Team',
        'core_version':'Defender-6'
    }

    @dataclass
    class ModConfModel(schemas.ModConfModel):
        ...

    @property
    def mod_config(self) -> ModConfModel:
        return self._mod_config

    def __init__(self, context: 'Loader') -> None:
        super().__init__(context)
        self._mod_config: Optional[schemas.ModConfModel] = None
        self._is_running = True
        self._io = context.DAsyncio
        self.task_increment_autolimit: Optional[DTask] = None

    async def load(self):
        # Variable qui va contenir les options de configuration du module Defender
        self._mod_config: schemas.ModConfModel  = self.ModConfModel()

        # Create tables
        await self.create_tables()

        # sync the database with local variable (Mandatory)
        await self.sync_db()

        # Create module commands (Mandatory)
        self.ctx.Commands.build_command(1, self.module_name, 'autolimit', 'SET, DEL or LIST')

        # Init Helper
        self.helper = ALHelper(self)
        await self.helper.init()
        self.task_increment_autolimit = self._io.create_task(self.increment_autolimit, task_flag=True)

    async def unload(self):
        self.task_increment_autolimit.event.clear()
        for _channel in self.ctx.Channel.UID_CHANNEL_DB:
            await self.ctx.Irc.Protocol.send_set_mode('-l', channel_name=_channel.name)

    async def create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """

        table_autolimit = f'''CREATE TABLE IF NOT EXISTS {self.__TABLENAME__} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_on TEXT,
            channel TEXT,
            amount INTEGER,
            interval INTEGER)
        '''

        await self.ctx.Base.db_execute_query(table_autolimit)
        return None

    async def apply_mode(self, mchan: MChannel, db_chan: Optional[schemas.ALChannel] = None):
        if self.mod_config.global_autolimit == 1:
            _interval = self.mod_config.global_interval
            _amount = self.mod_config.global_amount
            _channel = mchan.name
        else:
            _interval = db_chan.interval
            _amount = db_chan.amount
            _channel = db_chan.channel

        await asyncio.sleep(_interval)
        await self.ctx.Irc.Protocol.send_set_mode('+l', channel_name=_channel, params=len(mchan.uids) + _amount)

    async def increment_autolimit(self, event: asyncio.Event) -> None:
        uid_channel_db_copy: list[dict[str, int]] = [{"name": c.name, "uids_count": 0} for c in self.ctx.Channel.UID_CHANNEL_DB]
        chan_list: list[str] = [c.name for c in self.ctx.Channel.UID_CHANNEL_DB]

        while event.is_set():
            for _channel in self.ctx.Channel.UID_CHANNEL_DB:
                if self.mod_config.global_autolimit == 1:
                    for chan_copy in uid_channel_db_copy:
                        if chan_copy["name"] == _channel.name and len(_channel.uids) != chan_copy.get('uids_count'):
                            self.ctx.DAsyncio.create_task(self.apply_mode, _channel)
                            chan_copy['uids_count'] = len(_channel.uids)
                else:
                    for chan_copy in uid_channel_db_copy:
                        _db_chan = self.helper.get_al_channel(_channel.name)
                        if _db_chan:
                            if chan_copy.get('name') == _db_chan.channel and len(_channel.uids) != chan_copy.get('uids_count'):
                                self.ctx.DAsyncio.create_task(self.apply_mode, _channel, _db_chan)
                                chan_copy['uids_count'] = len(_channel.uids)

                if chan_copy.get('uids_count') == 0 and chan_copy.get('name') == _channel.name:
                    uid_channel_db_copy.remove({'name': _channel.name, 'uids_count': 0})

                if _channel.name not in chan_list:
                    uid_channel_db_copy.append({'name': _channel.name, 'uids_count': 0})
                    chan_list.append(_channel.name)
                    chan_list = list(set(chan_list))

            await asyncio.sleep(0.3)

    async def cmd(self, data: list[str]) -> None:
        """All messages coming from the IRCD server will be handled using this method (Mandatory)

        Args:
            data (list): Messages coming from the IRCD server.
        """
        if not data or len(data) < 2:
            return None
        cmd = data.copy() if isinstance(data, list) else list(data).copy()
        p = self.ctx.Irc.Protocol

        try:
            index, command = self.ctx.Irc.Protocol.get_ircd_protocol_poisition(cmd)
            if index == -1:
                return None
            
            match command:
                case 'PART':
                    # ['@unrealircd.org', ':001IN5101', 'PART', '#EFKnockr', ':Closing', 'Window']
                    ...

                case 'SJOIN':
                    # ['@msgid...', ':001', 'SJOIN', '1769989165', '#test', ':@001IN5101']
                    ...

                case _:
                    pass

        except Exception as err:
            self.ctx.Logs.error(f"General Error {err}", exc_info=True)

    async def hcmds(self, user: str, channel: Any, cmd: list, fullcmd: Optional[list] = None) -> None:
        """All messages coming from the user commands (Mandatory)

        Args:
            user (str): The user who send the request.
            channel (Any): The channel from where is coming the message (could be None).
            cmd (list): The messages coming from the IRCD server.
            fullcmd (list, optional): The full messages coming from the IRCD server. Defaults to [].
        """
        u = self.ctx.User.get_user(user)
        c = self.ctx.Channel.get_channel(channel) if self.ctx.Channel.is_valid_channel(channel) else None
        proto = self.ctx.Irc.Protocol
        if u is None:
            return None

        command = str(cmd[0]).lower()
        if command != 'autolimit':
            return None

        args = cmd[1] if len(cmd) > 1 else None

        dnickname = self.ctx.Config.SERVICE_NICKNAME

        match args:
            case 'set':
                # Syntax. AUTOLIMIT SET #channel <amount> <interval>
                if len(cmd) < 5:
                    await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT SET <channel> <amount> <interval>")
                    return None

                _channel = str(cmd[2]) if self.ctx.Channel.is_valid_channel(cmd[2]) else ''
                _amount = self.ctx.Utils.convert_to_int(cmd[3])
                _interval = self.ctx.Utils.convert_to_int(cmd[4])

                if _amount is None or _interval is None:
                    await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg=f"You must use string in Amount or Interval!")
                    await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT SET <channel> <amount> <interval>")
                    return None

                if not _channel:
                    await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg=f"The channel ({_channel}) is not valid!")
                    return None

                _query = f'SELECT id FROM {self.__TABLENAME__} WHERE channel=:channel'
                _params = {'channel': _channel.lower()}
                result = await self.ctx.Base.db_execute_query(_query, _params)
                if len(result.fetchall()) > 0:
                    _query = f'UPDATE {self.__TABLENAME__} SET amount = :amount, interval = :interval  WHERE channel=:channel'
                    _params = {'channel': _channel.lower(), 'amount': _amount, 'interval': _interval}
                    result = await self.ctx.Base.db_execute_query(_query, _params)
                    if result.rowcount > 0:
                        _al_chan = self.helper.get_al_channel(_channel.lower())
                        if _al_chan:
                            _al_chan.amount = _amount
                            _al_chan.interval = _interval

                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg=f"The channel ({_channel}) has been updated!")
                        return None
                    return None

                _query = f'INSERT INTO {self.__TABLENAME__} (created_on, channel, amount, interval) VALUES (:created_on, :channel, :amount, :interval)'
                _params = {'created_on': self.ctx.Utils.get_sdatetime(),
                           'channel': _channel.lower(),
                           'amount': _amount,
                           'interval': _interval}
                
                result = await self.ctx.Base.db_execute_query(_query, _params)
                if result.rowcount > 0:
                    self.helper.insert_al_channel(schemas.ALChannel(_channel.lower(), _amount, _interval))
                    await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg=f"{_channel} has been added to the autolimit database!")

                return None

            case 'list':
                try:
                    red = self.ctx.Config.COLORS.red
                    nogc = self.ctx.Config.COLORS.nogc
                    bold = self.ctx.Config.COLORS.bold

                    if self.mod_config.global_autolimit == 1:
                        await self.ctx.Irc.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=u.nickname,
                            msg=f"[AUTOLIMIT] The system is working {red}{bold}globally{nogc}")

                    for autolimit in self.DB_AL_CHANNELS:
                        await self.ctx.Irc.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=u.nickname,
                            msg=f"Channel: {autolimit.channel} | Amount: {autolimit.amount} | Interval: {autolimit.interval}")

                    return None

                except Exception as err:
                    self.ctx.Logs.error(f"Unknown Error: {err}")
                    return None

            case 'del':
                try:
                    # AUTOLIMIT DEL <channel> <channel>
                    if len(cmd) < 4:
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT DEL <channel> <channel>")
                        return None
                    _channel = str(cmd[2]).lower() if self.ctx.Channel.is_valid_channel(cmd[2]) else None
                    _channel_confirmation = str(cmd[3]).lower()

                    if _channel is None:
                        await proto.send_notice(nick_from=dnickname,
                                                nick_to=u.nickname,
                                                msg="The channel is not valid! you should start with #")
                        return None

                    if _channel != _channel_confirmation:
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="The confirmation channel is not matching!")
                        return None

                    _db_channel = self.helper.get_al_channel(_channel)
                    if _db_channel is None:
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname,
                                                msg=f"{_channel} is not available in the autolimit database")
                        return None

                    _query = f'DELETE FROM {self.__TABLENAME__} WHERE channel = :channel'
                    params = {'channel': _channel}

                    _result = await self.ctx.Base.db_execute_query(_query, params)
                    if _result.rowcount > 0 and self.helper.remove_al_channel(_channel):
                        await proto.send_notice(
                            nick_from=dnickname, nick_to=u.nickname,
                            msg=f"{_channel} has been removed from autolimit system!")

                    return None

                except Exception as err:
                    self.ctx.Logs.error(f"Unknown Error: {err}")
                    return None

            case 'global':
                try:
                    # Syntax. AUTOLIMIT GLOBAL ON|OFF <amount> <interval>
                    if len(cmd) == 3:
                        _state = str(cmd[2]).lower() if str(cmd[2]).lower() in ['on', 'off'] else None
                        if _state is None:
                            await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg=f"You must use the correct keyword ON or OFF")
                            return None
                        
                        if _state == 'on' and self.mod_config.global_autolimit == 1:
                            await proto.send_notice(nick_from=dnickname,
                                                    nick_to=u.nickname,
                                                    msg="[AUTOLIMIT] Global System already activated! "
                                                    "Using these parameters "
                                                    f"Amount: {self.mod_config.global_amount} | Interval: {self.mod_config.global_interval}")
                            return None
                        elif _state == 'off' and self.mod_config.global_autolimit == 0:
                            await proto.send_notice(nick_from=dnickname,
                                                    nick_to=u.nickname,
                                                    msg="[AUTOLIMIT] Global System already deactivated! ")
                            return None

                        if _state == 'on':
                            await self.update_configuration('global_autolimit', 1)
                            await proto.send_notice(
                                nick_from=dnickname,
                                nick_to=u.nickname,
                                msg=f'[AUTOLIMIT] Global autolimit activated '
                                f'using these parameters '
                                f'Amount: {self.mod_config.global_amount} | Interval: {self.mod_config.global_interval}')
                        elif _state == 'off':
                            await self.update_configuration('global_autolimit', 0)
                            for _channel in self.ctx.Channel.UID_CHANNEL_DB:
                                if _channel.name not in [_c.channel for _c in self.DB_AL_CHANNELS]:
                                    await self.ctx.Irc.Protocol.send_set_mode('-l', channel_name=_channel.name)
                            await proto.send_notice(nick_from=dnickname, nick_to=u.nickname,
                                                    msg=f'[AUTOLIMIT] Global autolimit deactivated!')
                        return None
    
                    if len(cmd) < 5:
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT GLOBAL ON [amount] [interval]")
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT GLOBAL OFF")
                        return None

                    _state = str(cmd[2]).lower() if str(cmd[2]).lower() in ['on', 'off'] else None
                    _amount = self.ctx.Utils.convert_to_int(cmd[3])
                    _interval = self.ctx.Utils.convert_to_int(cmd[4])

                    if _amount is None or _interval is None or _state is None:
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg=f"You must use numbers for Amount or Interval!")
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg=f"Or you use the correct keyword ON or OFF")
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT GLOBAL ON [amount] [interval]")
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT GLOBAL OFF")
                        return None

                    if _state == 'on':
                        await self.update_configuration('global_autolimit', 1)
                        await proto.send_notice(
                            nick_from=dnickname,
                            nick_to=u.nickname,
                            msg='[AUTOLIMIT] Global autolimit activated '
                            'using these parameters '
                            f'Amount: {self.mod_config.global_amount} | Interval: {self.mod_config.global_interval}')
                    else:
                        await self.update_configuration('global_autolimit', 0)
                        for _channel in self.ctx.Channel.UID_CHANNEL_DB:
                            if _channel.name not in [_c.channel for _c in self.DB_AL_CHANNELS]:
                                await self.ctx.Irc.Protocol.send_set_mode('-l', channel_name=_channel.name)
                        await proto.send_notice(nick_from=dnickname, nick_to=u.nickname,
                                                msg='[AUTOLIMIT] Global autolimit deactivated!')

                    await self.update_configuration('global_amount', _amount)
                    await self.update_configuration('global_interval', _interval)

                except Exception as err:
                    self.ctx.Logs.error(f"Unknown Error: {err}")
                    return None

            case _:
                await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT SET <channel> <amount> <interval>")
                await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT GLOBAL ON [amount] [interval]")
                await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT GLOBAL OFF")
                await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT DEL <channel> <channel>")
                await proto.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="Syntax. AUTOLIMIT LIST")
                return None