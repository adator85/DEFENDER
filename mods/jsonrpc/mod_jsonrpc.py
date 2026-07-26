import asyncio
import logging
import core.definition as dfn
import mods.jsonrpc.schemas as schemas
import mods.jsonrpc.threads as thds
from typing import TYPE_CHECKING, Optional
from unrealircd_rpc_py.objects.Definition import LiveRPCResult
import core.definition as dfn
from core.classes.interfaces.imodule import IModule
from core.constants import Colors as colors
from unrealircd_rpc_py.ConnectionFactory import ConnectionFactory
from unrealircd_rpc_py.LiveConnectionFactory import LiveConnectionFactory

if TYPE_CHECKING:
    from core.loader import Loader

class Jsonrpc(IModule):

    @dfn.dataclass
    class ModConfModel(schemas.ModConfModel):
        """The Model containing the module parameters
        """
        ...

    MOD_HEADER: dict[str, str] = {
        'name':'JsonRPC',
        'version':'1.0.0',
        'description':'Module using the unrealircd-rpc-py library',
        'author':'Defender Team',
        'core_version':'Defender-6'
    }

    def __init__(self, context: 'Loader') -> None:
        super().__init__(context)
        self._mod_config: Optional[schemas.ModConfModel] = None
        self._task_subscribe: Optional[dfn.DTask] = None
        self._task_unsubscribe: Optional[dfn.DTask] = None

    @property
    def mod_config(self) -> ModConfModel:
        return self._mod_config

    async def callback_sent_to_irc(self, response: LiveRPCResult) -> None:

        _proto = self.ctx.Irc.Protocol
        _dnickname = self.ctx.Config.SERVICE_NICKNAME
        _dchanlog = self.ctx.Config.SERVICE_CHANLOG
        _json_url = self.ctx.Config.JSONRPC_URL

        if response.error.code != 0:
            await _proto.send_priv_msg(
                nick_from=_dnickname,
                msg=f"[{colors.bold}{colors.red}JSONRPC ERROR{colors.nogc}{colors.bold}] {response.error.message} ({response.error.code})",
                channel=_dchanlog)
            return None

        if isinstance(response.result, bool):
            if response.result:
                await _proto.send_priv_msg(
                        nick_from=_dnickname,
                        msg=f"[ {colors.bold}{colors.green}JSONRPC INFO{colors.nogc}{colors.bold} ] IRCd json-rpc Event activated on {_json_url}",
                        channel=_dchanlog)
                return None

        level = response.result.level if hasattr(response.result, 'level') else ''
        subsystem = response.result.subsystem if hasattr(response.result, 'subsystem') else ''
        event_id = response.result.event_id if hasattr(response.result, 'event_id') else ''
        log_source = response.result.log_source if hasattr(response.result, 'log_source') else ''
        msg = response.result.msg if hasattr(response.result, 'msg') else ''

        build_msg = f"{colors.green}{log_source}{colors.nogc}: [{colors.bold}{level}{colors.bold}] {subsystem}.{event_id} - {msg}"
        await _proto.send_priv_msg(nick_from=_dnickname, msg=build_msg, channel=_dchanlog)
        
        return None

    def create_tables(self) -> None:
        return None

    async def load(self) -> None:

        logging.getLogger('websockets').setLevel(logging.WARNING)
        logging.getLogger('unrealircd-rpc-py').setLevel(logging.CRITICAL)
        logging.getLogger('unrealircd-liverpc-py').setLevel(logging.CRITICAL)

        self._mod_config = self.ModConfModel(jsonrpc=0)

        await self.sync_db()

        if self.ctx.Config.SERVEUR_PROTOCOL.lower() != 'unreal6':
            await self.ctx.ModuleUtils.unload_one_module(self.module_name, False)
            return None

        # Is RPC Active?
        self.is_streaming = False

        # Create module commands (Mandatory)
        self.ctx.Commands.build_command(1, self.module_name, 'jsonrpc', 'Activate the JSON RPC Live connection [ON|OFF]')
        self.ctx.Commands.build_command(1, self.module_name, 'jruser', 'Get Information about a user using JSON RPC')
        self.ctx.Commands.build_command(1, self.module_name, 'jrinstances', 'Get number of instances')

        try:
            self.Rpc = ConnectionFactory(self.ctx.Config.DEBUG_LEVEL).get(self.ctx.Config.JSONRPC_METHOD)
            self.LiveRpc = LiveConnectionFactory(self.ctx.Config.DEBUG_LEVEL).get(self.ctx.Config.JSONRPC_METHOD)
            
            sync_unixsocket = {'path_to_socket_file': self.ctx.Config.JSONRPC_PATH_TO_SOCKET_FILE}
            sync_http = {'url': self.ctx.Config.JSONRPC_URL, 'username': self.ctx.Config.JSONRPC_USER, 'password': self.ctx.Config.JSONRPC_PASSWORD}
            
            live_unixsocket = {'path_to_socket_file': self.ctx.Config.JSONRPC_PATH_TO_SOCKET_FILE,
                               'callback_object_instance' : self, 'callback_method_or_function_name': 'callback_sent_to_irc'}
            live_http = {'url': self.ctx.Config.JSONRPC_URL, 'username': self.ctx.Config.JSONRPC_USER, 'password': self.ctx.Config.JSONRPC_PASSWORD, 
                         'callback_object_instance' : self, 'callback_method_or_function_name': 'callback_sent_to_irc'}

            sync_param = sync_unixsocket if self.ctx.Config.JSONRPC_METHOD == 'unixsocket' else sync_http
            live_param = live_unixsocket if self.ctx.Config.JSONRPC_METHOD == 'unixsocket' else live_http

            self.Rpc.setup(sync_param)
            self.LiveRpc.setup(live_param)

            if self.mod_config.jsonrpc == 1:
                self._task_subscribe = self.ctx.DAsyncio.create_safe_task(thds.thread_subscribe(self))
            
            return None
        except Exception as err:
            await self.ctx.Irc.Protocol.send_priv_msg(
                    nick_from=self.ctx.Config.SERVICE_NICKNAME,
                    msg=f"[ {self.ctx.Const.Colors.red}JSONRPC ERROR{self.ctx.Const.Colors.nogc} ] {err.__str__()}",
                    channel=self.ctx.Config.SERVICE_CHANLOG
                    )
            self.ctx.Logs.error(f"JSONRPC ERROR: {err.__str__()}")

    async def unload(self) -> None:

        if self.ctx.Config.SERVEUR_PROTOCOL != 'unreal6':
            await self.ctx.ModuleUtils.unload_one_module(self.ctx.Irc, self.module_name, False)
            return None

        if self.is_streaming:
            await self.ctx.Irc.Protocol.send_priv_msg(
                        nick_from=self.ctx.Config.SERVICE_NICKNAME,
                        msg=f"[ {colors.green}JSONRPC INFO{colors.nogc} ] Shutting down IRCd json-rpc system!",
                        channel=self.ctx.Config.SERVICE_CHANLOG
                    )

        if self.mod_config.jsonrpc == 1:
            self._task_unsubscribe = self.ctx.DAsyncio.create_safe_task(thds.thread_unsubscribe(self))
            await asyncio.wait_for(self._task_unsubscribe.task, timeout=10)
            await asyncio.wait_for(self._task_subscribe.task, timeout=10)

        self.ctx.Commands.drop_command_by_module(self.module_name)
        self.ctx.Logs.debug(f"Unloading {self.module_name}")
        return None

    def cmd(self, data: list[str]) -> None:

        return None

    async def hcmds(self, user: str, channel: Optional[str], cmd: list[str], fullcmd: Optional[list[str]]) -> None:

        _proto = self.ctx.Irc.Protocol
        _log = self.ctx.Logs
        command = str(cmd[0]).lower()
        dnickname = self.ctx.Config.SERVICE_NICKNAME
        dchannel = self.ctx.Config.SERVICE_CHANLOG
        fromuser = user
        fromchannel = str(channel) if not channel is None else None

        match command:

            case 'jsonrpc':
                try:
                    if len(cmd) < 2:
                        await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jsonrpc on')
                        await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jsonrpc off')
                        return None

                    option = str(cmd[1]).lower()
                    match option:

                        case 'on':
                            self._task_subscribe = self.ctx.DAsyncio.create_safe_task(thds.thread_subscribe(self))
                            await self.update_configuration('jsonrpc', 1)

                        case 'off':
                            self._task_unsubscribe = self.ctx.DAsyncio.create_safe_task(thds.thread_unsubscribe(self))
                            await self.update_configuration('jsonrpc', 0)

                except IndexError as ie:
                    _log.error(ie)

            case 'jruser':
                try:
                    if len(cmd) < 2:
                        await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jruser get nickname')
                        return None

                    option = str(cmd[1]).lower()
                    match option:
                        case 'get':
                            nickname = str(cmd[2])
                            rpc = self.Rpc

                            UserInfo = rpc.User.get(nickname)
                            if UserInfo.error.code != 0:
                                await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'{UserInfo.error.message}')
                                return None

                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'UID                  : {UserInfo.id}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'NICKNAME             : {UserInfo.name}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'USERNAME             : {UserInfo.user.username}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'REALNAME             : {UserInfo.user.realname}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'MODES                : {UserInfo.user.modes}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CHANNELS             : {[chan.name for chan in UserInfo.user.channels]}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'SECURITY GROUP       : {UserInfo.user.security_groups}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'REPUTATION           : {UserInfo.user.reputation}')

                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'IP                   : {UserInfo.ip}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'COUNTRY CODE         : {UserInfo.geoip.country_code}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'ASN                  : {UserInfo.geoip.asn}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'ASNAME               : {UserInfo.geoip.asname}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CLOAKED HOST         : {UserInfo.user.cloakedhost}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'HOSTNAME             : {UserInfo.hostname}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'VHOST                : {UserInfo.user.vhost}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CLIENT PORT          : {UserInfo.client_port}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'SERVER PORT          : {UserInfo.server_port}')
                            
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CERTFP               : {UserInfo.tls.certfp}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CIPHER               : {UserInfo.tls.cipher}')

                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'IDLE SINCE           : {UserInfo.idle_since}')
                            await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CONNECTED SINCE      : {UserInfo.connected_since}')

                except IndexError as ie:
                    _log.error(ie)

            case 'jrinstances':
                try:
                    await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"GC Collect: {self.ctx.Utils.run_python_garbage_collector()}")
                    await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Nombre d'instance LiveWebsock: {self.ctx.Utils.get_number_gc_objects(LiveConnectionFactory)}")
                    await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Nombre d'instance ConnectionFactory: {self.ctx.Utils.get_number_gc_objects(ConnectionFactory)}")
                    await _proto.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Nombre de toute les instances: {self.ctx.Utils.get_number_gc_objects()}")
                except Exception as err:
                    _log.error(f"Unknown Error: {err}")
