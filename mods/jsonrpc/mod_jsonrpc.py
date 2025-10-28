import logging
import asyncio
from unrealircd_rpc_py.objects.Definition import LiveRPCResult
import mods.jsonrpc.utils as utils
import mods.jsonrpc.threads as thds
from time import sleep
from typing import TYPE_CHECKING
from dataclasses import dataclass
from unrealircd_rpc_py.ConnectionFactory import ConnectionFactory
from unrealircd_rpc_py.LiveConnectionFactory import LiveConnectionFactory

if TYPE_CHECKING:
    from core.irc import Irc

class Jsonrpc():

    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """
        jsonrpc: int = 0

    def __init__(self, ircInstance: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = ircInstance

        # Add Protocol to the module (Mandatory)
        self.Protocol = ircInstance.Protocol

        # Add Global Configuration to the module (Mandatory)
        self.Config = ircInstance.Config

        # Add Base object to the module (Mandatory)
        self.Base = ircInstance.Base

        # Add Main Utils (Mandatory)
        self.MainUtils = ircInstance.Utils

        # Add logs object to the module (Mandatory)
        self.Logs = ircInstance.Loader.Logs

        # Add User object to the module (Mandatory)
        self.User = ircInstance.User

        # Add Channel object to the module (Mandatory)
        self.Channel = ircInstance.Channel

        # Is RPC Active?
        self.is_streaming = False
        
        # Module Utils
        self.Utils = utils

        # Module threads
        self.Threads = thds

        # Run Garbage collector.
        self.Base.create_timer(10, self.MainUtils.run_python_garbage_collector)

        # Create module commands (Mandatory)
        self.Irc.build_command(1, self.module_name, 'jsonrpc', 'Activate the JSON RPC Live connection [ON|OFF]')
        self.Irc.build_command(1, self.module_name, 'jruser', 'Get Information about a user using JSON RPC')
        self.Irc.build_command(1, self.module_name, 'jrinstances', 'Get number of instances')

        # Init the module
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        logging.getLogger('websockets').setLevel(logging.WARNING)
        logging.getLogger('unrealircd-rpc-py').setLevel(logging.CRITICAL)
        logging.getLogger('unrealircd-liverpc-py').setLevel(logging.CRITICAL)

        # Create you own tables (Mandatory)
        # self.__create_tables()

        # Load module configuration and sync with core one (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

        try:
            self.Rpc = ConnectionFactory(self.Config.DEBUG_LEVEL).get(self.Config.JSONRPC_METHOD)
            self.LiveRpc = LiveConnectionFactory(self.Config.DEBUG_LEVEL).get(self.Config.JSONRPC_METHOD)
            
            sync_unixsocket = {'path_to_socket_file': self.Config.JSONRPC_PATH_TO_SOCKET_FILE}
            sync_http = {'url': self.Config.JSONRPC_URL, 'username': self.Config.JSONRPC_USER, 'password': self.Config.JSONRPC_PASSWORD}
            
            live_unixsocket = {'path_to_socket_file': self.Config.JSONRPC_PATH_TO_SOCKET_FILE,
                               'callback_object_instance' : self, 'callback_method_or_function_name': 'callback_sent_to_irc'}
            live_http = {'url': self.Config.JSONRPC_URL, 'username': self.Config.JSONRPC_USER, 'password': self.Config.JSONRPC_PASSWORD, 
                         'callback_object_instance' : self, 'callback_method_or_function_name': 'callback_sent_to_irc'}

            sync_param = sync_unixsocket if self.Config.JSONRPC_METHOD == 'unixsocket' else sync_http
            live_param = live_unixsocket if self.Config.JSONRPC_METHOD == 'unixsocket' else live_http

            self.Rpc.setup(sync_param)
            self.LiveRpc.setup(live_param)

            if self.ModConfig.jsonrpc == 1:
                self.Base.create_thread(func=self.Threads.thread_subscribe, func_args=(self, ), run_once=True)
            
            return None
        except Exception as err:
            self.Protocol.send_priv_msg(
                    nick_from=self.Config.SERVICE_NICKNAME,
                    msg=f"[{self.Config.COLORS.red}JSONRPC ERROR{self.Config.COLORS.nogc}] {err.__str__()}",
                    channel=self.Config.SERVICE_CHANLOG
                    )
            self.Logs.error(f"JSONRPC ERROR: {err.__str__()}")

    def __create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """

        table_logs = '''CREATE TABLE IF NOT EXISTS test_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            )
        '''

        self.Base.db_execute_query(table_logs)
        return None

    def callback_sent_to_irc(self, response: LiveRPCResult) -> None:

        dnickname = self.Config.SERVICE_NICKNAME
        dchanlog = self.Config.SERVICE_CHANLOG
        green = self.Config.COLORS.green
        nogc = self.Config.COLORS.nogc
        bold = self.Config.COLORS.bold
        red = self.Config.COLORS.red

        if response.error.code != 0:
            self.Protocol.send_priv_msg(nick_from=dnickname,
                        msg=f"[{bold}{red}JSONRPC ERROR{nogc}{bold}] {response.error.message} ({response.error.code})",
                        channel=dchanlog)
            return None

        if isinstance(response.result, bool):
            if response.result:
                self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"[{bold}{green}JSONRPC{nogc}{bold}] JSONRPC Event activated on {self.Config.JSONRPC_URL}",
                        channel=dchanlog)
                return None

        level = response.result.level if hasattr(response.result, 'level') else ''
        subsystem = response.result.subsystem if hasattr(response.result, 'subsystem') else ''
        event_id = response.result.event_id if hasattr(response.result, 'event_id') else ''
        log_source = response.result.log_source if hasattr(response.result, 'log_source') else ''
        msg = response.result.msg if hasattr(response.result, 'msg') else ''

        build_msg = f"{green}{log_source}{nogc}: [{bold}{level}{bold}] {subsystem}.{event_id} - {msg}"
        self.Protocol.send_priv_msg(nick_from=dnickname, msg=build_msg, channel=dchanlog)
        
        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Build the default configuration model (Mandatory)
            self.ModConfig = self.ModConfModel(jsonrpc=0)

            # Sync the configuration with core configuration (Mandatory)
            self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def update_configuration(self, param_key: str, param_value: str) -> None:
        """Update the local and core configuration

        Args:
            param_key (str): The parameter key
            param_value (str): The parameter value
        """
        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    def unload(self) -> None:
        if self.is_streaming:
            self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"[{self.Config.COLORS.green}JSONRPC INFO{self.Config.COLORS.nogc}] Shutting down RPC system!", 
                        channel=self.Config.SERVICE_CHANLOG
                    )
        self.Base.create_thread(func=self.Threads.thread_unsubscribe, func_args=(self, ), run_once=True)
        self.update_configuration('jsonrpc', 0)
        self.Irc.Commands.drop_command_by_module(self.module_name)
        self.Logs.debug(f"Unloading {self.module_name}")
        return None

    def cmd(self, data: list) -> None:

        return None

    def hcmds(self, user:str, channel: any, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        dnickname = self.Config.SERVICE_NICKNAME
        dchannel = self.Config.SERVICE_CHANLOG
        fromuser = user
        fromchannel = str(channel) if not channel is None else None

        match command:

            case 'jsonrpc':
                try:
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jsonrpc on')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jsonrpc off')
                        return None

                    option = str(cmd[1]).lower()
                    match option:

                        case 'on':
                            thread_name = 'thread_subscribe'
                            if self.Base.is_thread_alive(thread_name):
                                self.Protocol.send_priv_msg(nick_from=dnickname, channel=dchannel, msg=f"The Subscription is running")
                                return None
                            elif self.Base.is_thread_exist(thread_name):
                                self.Protocol.send_priv_msg(
                                    nick_from=dnickname, channel=dchannel,
                                    msg=f"The subscription is not running, wait untill the process will be cleaned up"
                                    )
                                return None

                            self.Base.create_thread(func=self.Threads.thread_subscribe, func_args=(self, ), run_once=True)
                            self.update_configuration('jsonrpc', 1)

                        case 'off':
                            self.Base.create_thread(func=self.Threads.thread_unsubscribe, func_args=(self, ), run_once=True)
                            self.update_configuration('jsonrpc', 0)

                except IndexError as ie:
                    self.Logs.error(ie)

            case 'jruser':
                try:
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jruser get nickname')
                    option = str(cmd[1]).lower()
                    match option:
                        case 'get':
                            nickname = str(cmd[2])
                            rpc = self.Rpc

                            UserInfo = rpc.User.get(nickname)
                            if UserInfo.error.code != 0:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'{UserInfo.error.message}')
                                return None

                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'UID                  : {UserInfo.id}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'NICKNAME             : {UserInfo.name}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'USERNAME             : {UserInfo.user.username}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'REALNAME             : {UserInfo.user.realname}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'MODES                : {UserInfo.user.modes}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CHANNELS             : {[chan.name for chan in UserInfo.user.channels]}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'SECURITY GROUP       : {UserInfo.user.security_groups}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'REPUTATION           : {UserInfo.user.reputation}')

                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'IP                   : {UserInfo.ip}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'COUNTRY CODE         : {UserInfo.geoip.country_code}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'ASN                  : {UserInfo.geoip.asn}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'ASNAME               : {UserInfo.geoip.asname}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CLOAKED HOST         : {UserInfo.user.cloakedhost}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'HOSTNAME             : {UserInfo.hostname}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'VHOST                : {UserInfo.user.vhost}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CLIENT PORT          : {UserInfo.client_port}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'SERVER PORT          : {UserInfo.server_port}')
                            
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CERTFP               : {UserInfo.tls.certfp}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CIPHER               : {UserInfo.tls.cipher}')

                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'IDLE SINCE           : {UserInfo.idle_since}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'CONNECTED SINCE      : {UserInfo.connected_since}')

                except IndexError as ie:
                    self.Logs.error(ie)

            case 'jrinstances':
                try:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"GC Collect: {self.MainUtils.run_python_garbage_collector()}")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Nombre d'instance LiveWebsock: {self.MainUtils.get_number_gc_objects(LiveConnectionFactory)}")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Nombre d'instance ConnectionFactory: {self.MainUtils.get_number_gc_objects(ConnectionFactory)}")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Nombre de toute les instances: {self.MainUtils.get_number_gc_objects()}")
                except Exception as err:
                    self.Logs.error(f"Unknown Error: {err}")