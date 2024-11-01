from dataclasses import dataclass
from core.irc import Irc
from unrealircd_rpc_py.Live import Live
from unrealircd_rpc_py.Loader import Loader


class Jsonrpc():

    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """
        jsonrpc: int = 0

    def __init__(self, ircInstance:Irc) -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = ircInstance

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
                    callback_method_name='callback_sent_to_irc',
                    debug_level=10
                    )

        self.Rpc: Loader = Loader(
            req_method=self.Config.JSONRPC_METHOD,
            url=self.Config.JSONRPC_URL,
            username=self.Config.JSONRPC_USER,
            password=self.Config.JSONRPC_PASSWORD
        )

        self.subscribed = False

        if self.Rpc.Error.code != 0:
            self.Irc.sendPrivMsg(f"[{self.Config.COLORS.red}ERROR{self.Config.COLORS.nogc}] {self.Rpc.Error.message}", self.Config.SERVICE_CHANLOG)

        if self.UnrealIrcdRpcLive.Error.code != 0:
            self.Irc.sendPrivMsg(f"[{self.Config.COLORS.red}ERROR{self.Config.COLORS.nogc}] {self.UnrealIrcdRpcLive.Error.message}", self.Config.SERVICE_CHANLOG)

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
            self.Irc.sendPrivMsg(msg=f"[{bold}{green}JSONRPC{nogc}{bold}] Event activated", channel=dchanlog)
            return None

        level = json_response.result.level
        subsystem = json_response.result.subsystem
        event_id = json_response.result.event_id
        log_source = json_response.result.log_source
        msg = json_response.result.msg

        build_msg = f"{green}{log_source}{nogc}: [{bold}{level}{bold}] {subsystem}.{event_id} - {msg}"

        self.Irc.sendPrivMsg(msg=build_msg, channel=dchanlog)

    def thread_start_jsonrpc(self):

        if self.UnrealIrcdRpcLive.Error.code == 0:
            self.UnrealIrcdRpcLive.subscribe(["all"])
            self.subscribed = True
        else:
            self.Irc.sendPrivMsg(f"[{self.Config.COLORS.red}ERROR{self.Config.COLORS.nogc}] {self.UnrealIrcdRpcLive.Error.message}", self.Config.SERVICE_CHANLOG)

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
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} jsonrpc on')
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} jsonrpc off')

                    match option:

                        case 'on':
                            for thread in self.Base.running_threads:
                                if thread.getName() == 'thread_start_jsonrpc':
                                    if thread.is_alive():
                                        self.Irc.sendPrivMsg(f"Thread {thread.getName()} is running", dchannel)
                                    else:
                                        self.Irc.sendPrivMsg(f"Thread {thread.getName()} is not running, wait untill the process will be cleaned up", dchannel)

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
                        self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :/msg {dnickname} jruser get nickname')

                    match option:

                        case 'get':
                            nickname = str(cmd[2])
                            uid_to_get = self.User.get_uid(nickname)
                            if uid_to_get is None:
                                return None

                            rpc = self.Rpc

                            UserInfo = rpc.User.get(uid_to_get)
                            if rpc.Error.code != 0:
                                self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :{rpc.Error.message}')
                                return None

                            chan_list = []
                            for chan in UserInfo.user.channels:
                                chan_list.append(chan.name)

                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :UID                  : {UserInfo.id}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :NICKNAME             : {UserInfo.name}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :USERNAME             : {UserInfo.user.username}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :REALNAME             : {UserInfo.user.realname}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :MODES                : {UserInfo.user.modes}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :CHANNELS             : {chan_list}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :SECURITY GROUP       : {UserInfo.user.security_groups}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :REPUTATION           : {UserInfo.user.reputation}')

                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :IP                   : {UserInfo.ip}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :COUNTRY CODE         : {UserInfo.geoip.country_code}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :ASN                  : {UserInfo.geoip.asn}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :ASNAME               : {UserInfo.geoip.asname}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :CLOAKED HOST         : {UserInfo.user.cloakedhost}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :HOSTNAME             : {UserInfo.hostname}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :VHOST                : {UserInfo.user.vhost}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :CLIENT PORT          : {UserInfo.client_port}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :SERVER PORT          : {UserInfo.server_port}')
                            
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :CERTFP               : {UserInfo.tls.certfp}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :CIPHER               : {UserInfo.tls.cipher}')

                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :IDLE SINCE           : {UserInfo.idle_since}')
                            self.Irc.send2socket(f':{dnickname} NOTICE {fromuser} :CONNECTED SINCE      : {UserInfo.connected_since}')

                except IndexError as ie:
                    self.Logs.error(ie)

            case 'ia':
                try:

                    self.Base.create_thread(self.thread_ask_ia, ('',))

                    self.Irc.send2socket(f":{dnickname} NOTICE {fromuser} : This is a notice to the sender ...")
                    self.Irc.send2socket(f":{dnickname} PRIVMSG {fromuser} : This is private message to the sender ...")

                    if not fromchannel is None:
                        self.Irc.send2socket(f":{dnickname} PRIVMSG {fromchannel} : This is channel message to the sender ...")

                    # How to update your module configuration
                    self.__update_configuration('param_exemple2', 7)

                    # Log if you want the result
                    self.Logs.debug(f"Test logs ready")

                except Exception as err:
                    self.Logs.error(f"Unknown Error: {err}")