import logging
from typing import TYPE_CHECKING
from dataclasses import dataclass
from unrealircd_rpc_py.Live import Live
from unrealircd_rpc_py.Loader import Loader

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

        # Add logs object to the module (Mandatory)
        self.Logs = ircInstance.Base.logs

        # Add User object to the module (Mandatory)
        self.User = ircInstance.User

        # Add Channel object to the module (Mandatory)
        self.Channel = ircInstance.Channel

        # Create module commands (Mandatory)
        self.commands_level = {
            1: ['jsonrpc', 'jruser']
        }

        # Init the module
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Insert module commands into the core one (Mandatory)
        self.__set_commands(self.commands_level)
        logging.getLogger('websockets').setLevel(logging.WARNING)

        # Create you own tables (Mandatory)
        # self.__create_tables()

        # Load module configuration and sync with core one (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

        # self.UnrealIrcdRpcLive: Live = Live(
        #                 req_method='unixsocket',
        #                 path_to_socket_file=self.Config.JSONRPC_PATH_TO_SOCKET_FILE,
        #                 callback_object_instance=self,
        #                 callback_method_name='callback_sent_to_irc'
        #                )

        self.UnrealIrcdRpcLive: Live = Live(
                    req_method='websocket',
                    url=self.Config.JSONRPC_URL,
                    username=self.Config.JSONRPC_USER,
                    password=self.Config.JSONRPC_PASSWORD,
                    callback_object_instance=self,
                    callback_method_name='callback_sent_to_irc'
                    )

        self.Rpc: Loader = Loader(
            req_method=self.Config.JSONRPC_METHOD,
            url=self.Config.JSONRPC_URL,
            username=self.Config.JSONRPC_USER,
            password=self.Config.JSONRPC_PASSWORD
        )

        self.subscribed = False

        if self.Rpc.Error.code != 0:
            self.Protocol.sendPrivMsg(
                nick_from=self.Config.SERVICE_NICKNAME,
                msg=f"[{self.Config.COLORS.red}ERROR{self.Config.COLORS.nogc}] {self.Rpc.Error.message}", 
                channel=self.Config.SERVICE_CHANLOG
                )

        if self.UnrealIrcdRpcLive.Error.code != 0:
            self.Protocol.sendPrivMsg(
                    nick_from=self.Config.SERVICE_NICKNAME,
                    msg=f"[{self.Config.COLORS.red}ERROR{self.Config.COLORS.nogc}] {self.UnrealIrcdRpcLive.Error.message}", 
                    channel=self.Config.SERVICE_CHANLOG
                )

        if self.ModConfig.jsonrpc == 1:
            self.Base.create_thread(self.thread_start_jsonrpc, run_once=True)

        return None

    def __set_commands(self, commands:dict[int, list[str]]) -> None:
        """### Rajoute les commandes du module au programme principal

        Args:
            commands (list): Liste des commandes du module
        """
        for level, com in commands.items():
            for c in commands[level]:
                if not c in self.Irc.commands:
                    self.Irc.commands_level[level].append(c)
                    self.Irc.commands.append(c)

        return None

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

    def callback_sent_to_irc(self, json_response: str):

        dnickname = self.Config.SERVICE_NICKNAME
        dchanlog = self.Config.SERVICE_CHANLOG
        green = self.Config.COLORS.green
        nogc = self.Config.COLORS.nogc
        bold = self.Config.COLORS.bold
        red = self.Config.COLORS.red

        if json_response.result == True:
            self.Protocol.sendPrivMsg(
                nick_from=self.Config.SERVICE_NICKNAME,
                msg=f"[{bold}{green}JSONRPC{nogc}{bold}] Event activated", 
                channel=dchanlog)
            return None

        level = json_response.result.level
        subsystem = json_response.result.subsystem
        event_id = json_response.result.event_id
        log_source = json_response.result.log_source
        msg = json_response.result.msg

        build_msg = f"{green}{log_source}{nogc}: [{bold}{level}{bold}] {subsystem}.{event_id} - {msg}"

        self.Protocol.sendPrivMsg(nick_from=dnickname, msg=build_msg, channel=dchanlog)

    def thread_start_jsonrpc(self):

        if self.UnrealIrcdRpcLive.Error.code == 0:
            self.UnrealIrcdRpcLive.subscribe(["all"])
            self.subscribed = True
        else:
            self.Protocol.sendPrivMsg(
                    nick_from=self.Config.SERVICE_NICKNAME,
                    msg=f"[{self.Config.COLORS.red}ERROR{self.Config.COLORS.nogc}] {self.UnrealIrcdRpcLive.Error.message}", 
                    channel=self.Config.SERVICE_CHANLOG
                )

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

    def __update_configuration(self, param_key: str, param_value: str):
        """Update the local and core configuration

        Args:
            param_key (str): The parameter key
            param_value (str): The parameter value
        """
        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    def unload(self) -> None:
        if self.UnrealIrcdRpcLive.Error.code != -1:
            self.UnrealIrcdRpcLive.unsubscribe()
        return None

    def cmd(self, data:list) -> None:

        return None

    def _hcmds(self, user:str, channel: any, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        dnickname = self.Config.SERVICE_NICKNAME
        dchannel = self.Config.SERVICE_CHANLOG
        fromuser = user
        fromchannel = str(channel) if not channel is None else None

        match command:

            case 'jsonrpc':
                try:
                    option = str(cmd[1]).lower()

                    if len(command) == 1:
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jsonrpc on')
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jsonrpc off')

                    match option:

                        case 'on':
                            for thread in self.Base.running_threads:
                                if thread.getName() == 'thread_start_jsonrpc':
                                    if thread.is_alive():
                                        self.Protocol.sendPrivMsg(
                                            nick_from=self.Config.SERVICE_NICKNAME,
                                            msg=f"Thread {thread.getName()} is running",
                                            channel=dchannel
                                            )
                                    else:
                                        self.Protocol.sendPrivMsg(
                                            nick_from=self.Config.SERVICE_NICKNAME,
                                            msg=f"Thread {thread.getName()} is not running, wait untill the process will be cleaned up",
                                            channel=dchannel
                                            )

                            self.Base.create_thread(self.thread_start_jsonrpc, run_once=True)
                            self.__update_configuration('jsonrpc', 1)

                        case 'off':
                            self.UnrealIrcdRpcLive.unsubscribe()
                            self.__update_configuration('jsonrpc', 0)

                except IndexError as ie:
                    self.Logs.error(ie)

            case 'jruser':
                try:
                    option = str(cmd[1]).lower()

                    if len(command) == 1:
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'/msg {dnickname} jruser get nickname')

                    match option:

                        case 'get':
                            nickname = str(cmd[2])
                            uid_to_get = self.User.get_uid(nickname)
                            if uid_to_get is None:
                                return None

                            rpc = self.Rpc

                            UserInfo = rpc.User.get(uid_to_get)
                            if rpc.Error.code != 0:
                                self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'{rpc.Error.message}')
                                return None

                            chan_list = []
                            for chan in UserInfo.user.channels:
                                chan_list.append(chan.name)

                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'UID                  : {UserInfo.id}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'NICKNAME             : {UserInfo.name}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'USERNAME             : {UserInfo.user.username}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'REALNAME             : {UserInfo.user.realname}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'MODES                : {UserInfo.user.modes}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'CHANNELS             : {chan_list}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'SECURITY GROUP       : {UserInfo.user.security_groups}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'REPUTATION           : {UserInfo.user.reputation}')

                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'IP                   : {UserInfo.ip}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'COUNTRY CODE         : {UserInfo.geoip.country_code}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'ASN                  : {UserInfo.geoip.asn}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'ASNAME               : {UserInfo.geoip.asname}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'CLOAKED HOST         : {UserInfo.user.cloakedhost}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'HOSTNAME             : {UserInfo.hostname}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'VHOST                : {UserInfo.user.vhost}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'CLIENT PORT          : {UserInfo.client_port}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'SERVER PORT          : {UserInfo.server_port}')
                            
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'CERTFP               : {UserInfo.tls.certfp}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'CIPHER               : {UserInfo.tls.cipher}')

                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'IDLE SINCE           : {UserInfo.idle_since}')
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f'CONNECTED SINCE      : {UserInfo.connected_since}')

                except IndexError as ie:
                    self.Logs.error(ie)

            case 'ia':
                try:

                    self.Base.create_thread(self.thread_ask_ia, ('',))

                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" This is a notice to the sender ...")
                    self.Protocol.sendPrivMsg(nick_from=dnickname, msg="This is private message to the sender ...", nick_to=fromuser)

                    if not fromchannel is None:
                        self.Protocol.sendPrivMsg(nick_from=dnickname, msg="This is channel message to the sender ...", channel=fromchannel)

                    # How to update your module configuration
                    self.__update_configuration('param_exemple2', 7)

                    # Log if you want the result
                    self.Logs.debug(f"Test logs ready")

                except Exception as err:
                    self.Logs.error(f"Unknown Error: {err}")