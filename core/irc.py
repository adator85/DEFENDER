import sys
import socket
import ssl
import re
import time
from ssl import SSLSocket
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional, Union
from core.classes import rehash
from core.loader import Loader
from core.classes.protocol import Protocol
from core.utils import tr

if TYPE_CHECKING:
    from core.definition import MSasl

class Irc:
    _instance = None

    def __new__(cls, *agrs):

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self, loader: Loader) -> 'Irc':

        # Loader class
        self.Loader = loader

        # Load the configuration
        self.Config = self.Loader.Config

        # Load Main utils functions
        self.Utils = self.Loader.Utils

        # Date et heure de la premiere connexion de Defender
        self.defender_connexion_datetime = self.Config.DEFENDER_CONNEXION_DATETIME

        # Lancer toutes les 30 secondes des actions de nettoyages
        self.beat = self.Config.DEFENDER_HEARTBEAT_FREQUENCY

        # Heartbeat active
        self.hb_active = self.Config.DEFENDER_HEARTBEAT

        # ID du serveur qui accueil le service ( Host Serveur Id )
        self.HSID = self.Config.HSID

        # Charset utiliser pour décoder/encoder les messages
        self.CHARSET = self.Config.SERVEUR_CHARSET
        """0: utf-8 | 1: iso-8859-1"""

        # Use Base Instance
        self.Base = self.Loader.Base

        # Logger
        self.Logs = self.Loader.Logs

        # Get Settings.
        self.Settings = self.Base.Settings

        # Use User Instance
        self.User = self.Loader.User

        # Use Admin Instance
        self.Admin = self.Loader.Admin

        # Use Client Instance
        self.Client = self.Loader.Client

        # Use Channel Instance
        self.Channel = self.Loader.Channel

        # Use Reputation Instance
        self.Reputation = self.Loader.Reputation

        # Use Module Utils
        self.ModuleUtils = self.Loader.ModuleUtils

        # Use Main Sasl module
        self.Sasl = self.Loader.Sasl

        self.autolimit_started: bool = False
        """This variable is to make sure the thread is not running"""

        # define first reputation score to 0
        self.first_score: int = 0

        # Define first IP connexion
        self.first_connexion_ip: str = None

        # Load Commands Utils
        self.Commands = self.Loader.Commands
        """Command utils"""

        self.build_command(0, 'core', 'help', 'This provide the help')
        self.build_command(0, 'core', 'auth', 'Login to the IRC Service')
        self.build_command(0, 'core', 'copyright', 'Give some information about the IRC Service')
        self.build_command(0, 'core', 'uptime', 'Give you since when the service is connected')
        self.build_command(0, 'core', 'firstauth', 'First authentication of the Service')
        self.build_command(0, 'core', 'register', f'Register your nickname /msg {self.Config.SERVICE_NICKNAME} REGISTER <password> <email>')
        self.build_command(0, 'core', 'identify', f'Identify yourself with your password /msg {self.Config.SERVICE_NICKNAME} IDENTIFY <account> <password>')
        self.build_command(0, 'core', 'logout', 'Reverse the effect of the identify command')
        self.build_command(1, 'core', 'load', 'Load an existing module')
        self.build_command(1, 'core', 'unload', 'Unload a module')
        self.build_command(1, 'core', 'reload', 'Reload a module')
        self.build_command(1, 'core', 'deauth', 'Deauth from the irc service')
        self.build_command(1, 'core', 'checkversion', 'Check the version of the irc service')
        self.build_command(2, 'core', 'show_modules', 'Display a list of loaded modules')
        self.build_command(2, 'core', 'show_timers', 'Display active timers')
        self.build_command(2, 'core', 'show_threads', 'Display active threads in the system')
        self.build_command(2, 'core', 'show_channels', 'Display a list of active channels')
        self.build_command(2, 'core', 'show_users', 'Display a list of connected users')
        self.build_command(2, 'core', 'show_clients', 'Display a list of connected clients')
        self.build_command(2, 'core', 'show_admins', 'Display a list of administrators')
        self.build_command(2, 'core', 'show_configuration', 'Display the current configuration settings')
        self.build_command(2, 'core', 'show_cache', 'Display the current cache')
        self.build_command(2, 'core', 'clear_cache', 'Clear the cache!')
        self.build_command(3, 'core', 'quit', 'Disconnect the bot or user from the server.')
        self.build_command(3, 'core', 'restart', 'Restart the bot or service.')
        self.build_command(3, 'core', 'addaccess', 'Add a user or entity to an access list with specific permissions.')
        self.build_command(3, 'core', 'editaccess', 'Modify permissions for an existing user or entity in the access list.')
        self.build_command(3, 'core', 'delaccess', 'Remove a user or entity from the access list.')
        self.build_command(3, 'core', 'cert', 'Append your new fingerprint to your account!')
        self.build_command(4, 'core', 'rehash', 'Reload the configuration file without restarting')
        self.build_command(4, 'core', 'raw', 'Send a raw command directly to the IRC server')

        # Define the IrcSocket object
        self.IrcSocket: Optional[Union[socket.socket, SSLSocket]] = None

        self.__create_table()
        self.Base.create_thread(func=self.heartbeat, func_args=(self.beat, ))

    ##############################################
    #               CONNEXION IRC                #
    ##############################################
    def init_irc(self, ircInstance: 'Irc') -> None:
        """Create a socket and connect to irc server

        Args:
            ircInstance (Irc): Instance of Irc object.
        """
        try:
            self.init_service_user()
            self.Utils.create_socket(ircInstance)
            self.__connect_to_irc(ircInstance)

        except AssertionError as ae:
            self.Logs.critical(f'Assertion error: {ae}')

    def init_service_user(self) -> None:

        self.User.insert(self.Loader.Definition.MUser(
            uid=self.Config.SERVICE_ID,
            nickname=self.Config.SERVICE_NICKNAME,
            username=self.Config.SERVICE_USERNAME,
            realname=self.Config.SERVICE_REALNAME,
            hostname=self.Config.SERVICE_HOST,
            umodes=self.Config.SERVICE_SMODES
        ))
        return None

    def __connect_to_irc(self, ircInstance: 'Irc') -> None:
        try:
            self.init_service_user()
            self.ircObject = ircInstance              # créer une copie de l'instance Irc
            self.Protocol = Protocol(
                protocol=self.Config.SERVEUR_PROTOCOL,
                ircInstance=self.ircObject
                ).Protocol
            self.Protocol.send_link()                 # Etablir le link en fonction du protocol choisi
            self.signal = True                        # Une variable pour initier la boucle infinie
            self.join_saved_channels()                # Join existing channels
            self.ModuleUtils.db_load_all_existing_modules(self)

            while self.signal:
                try:
                    if self.Config.DEFENDER_RESTART == 1:
                        rehash.restart_service(self.ircObject)

                    # 4072 max what the socket can grab
                    buffer_size = self.IrcSocket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
                    data_in_bytes = self.IrcSocket.recv(buffer_size)
                    data = data_in_bytes.splitlines(True)
                    count_bytes = len(data_in_bytes)

                    while count_bytes > 4070:
                        # If the received message is > 4070 then loop and add the value to the variable
                        new_data = self.IrcSocket.recv(buffer_size)
                        data_in_bytes += new_data
                        count_bytes = len(new_data)

                    data = data_in_bytes.splitlines(True)

                    if not data:
                        break

                    self.send_response(data)

                except ssl.SSLEOFError as soe:
                    self.Logs.error(f"SSLEOFError __connect_to_irc: {soe} - {data}")
                except ssl.SSLError as se:
                    self.Logs.error(f"SSLError __connect_to_irc: {se} - {data}")
                    sys.exit(1)
                except OSError as oe:
                    self.Logs.error(f"SSLError __connect_to_irc: {oe} - {data}")
                except (socket.error, ConnectionResetError):
                    self.Logs.debug("Connexion reset")

            self.IrcSocket.shutdown(socket.SHUT_RDWR)
            self.IrcSocket.close()
            self.Logs.info("-- Fermeture de Defender ...")
            sys.exit(0)

        except AssertionError as ae:
            self.Logs.error(f'AssertionError: {ae}')
        except ValueError as ve:
            self.Logs.error(f'ValueError: {ve}')
        except ssl.SSLEOFError as soe:
            self.Logs.error(f"SSLEOFError: {soe}")
        except AttributeError as atte:
            self.Logs.critical(f"AttributeError: {atte}")
        except Exception as e:
            self.Logs.critical(f"General Error: {e}", exc_info=True)

    def join_saved_channels(self) -> None:
        """## Joining saved channels"""
        exec_query = self.Base.db_execute_query(f'SELECT distinct channel_name FROM {self.Config.TABLE_CHANNEL}')
        result_query = exec_query.fetchall()

        if result_query:
            for chan_name in result_query:
                chan = chan_name[0]
                self.Protocol.send_sjoin(channel=chan)

    def send_response(self, responses:list[bytes]) -> None:
        try:
            for data in responses:
                response = data.decode(self.CHARSET[0]).split()
                self.cmd(response)

        except UnicodeEncodeError as ue:
            for data in responses:
                response = data.decode(self.CHARSET[1],'replace').split()
                self.cmd(response)
            self.Logs.error(f'UnicodeEncodeError: {ue}')
            self.Logs.error(response)

        except UnicodeDecodeError as ud:
            for data in responses:
                response = data.decode(self.CHARSET[1],'replace').split()
                self.cmd(response)
            self.Logs.error(f'UnicodeDecodeError: {ud}')
            self.Logs.error(response)

        except AssertionError as ae:
            self.Logs.error(f"Assertion error : {ae}")

    def unload(self) -> None:
        # This is only to reference the method
        return None

    ##############################################
    #             FIN CONNEXION IRC              #
    ##############################################

    def build_command(self, level: int, module_name: str, command_name: str, command_description: str) -> None:
        """This method build the commands variable

        Args:
            level (int): The Level of the command
            module_name (str): The module name
            command_name (str): The command name
            command_description (str): The description of the command
        """
        # Build Model.
        self.Commands.build(self.Loader.Definition.MCommand(module_name, command_name, command_description, level))

        return None

    def generate_help_menu(self, nickname: str, module: Optional[str] = None) -> None:

        # Check if the nickname is an admin
        p = self.Protocol
        admin_obj = self.Admin.get_admin(nickname)
        dnickname = self.Config.SERVICE_NICKNAME
        color_nogc = self.Config.COLORS.nogc
        color_black = self.Config.COLORS.black
        current_level = 0

        if admin_obj is not None:
            current_level = admin_obj.level

        p.send_notice(nick_from=dnickname,nick_to=nickname, msg=f" ***************** LISTE DES COMMANDES *****************")
        header = f"  {'Level':<8}| {'Command':<25}| {'Module':<15}| {'Description':<35}"
        line = "-"*75
        p.send_notice(nick_from=dnickname,nick_to=nickname, msg=header)
        p.send_notice(nick_from=dnickname,nick_to=nickname, msg=f"  {line}")
        for cmd in self.Commands.get_commands_by_level(current_level):
            if module is None or cmd.module_name.lower() == module.lower():
                p.send_notice(
                        nick_from=dnickname, 
                        nick_to=nickname, 
                        msg=f"  {color_black}{cmd.command_level:<8}{color_nogc}| {cmd.command_name:<25}| {cmd.module_name:<15}| {cmd.description:<35}"
                        )
        
        return None

    def on_sasl_authentication_process(self, sasl_model: 'MSasl') -> bool:
        s = sasl_model
        if sasl_model:
            def db_get_admin_info(*, username: Optional[str] = None, password: Optional[str] = None, fingerprint: Optional[str] = None) -> Optional[dict[str, Any]]:
                if fingerprint:
                    mes_donnees = {'fingerprint': fingerprint}
                    query = f"SELECT user, level FROM {self.Config.TABLE_ADMIN} WHERE fingerprint = :fingerprint"
                else:
                    mes_donnees = {'user': username, 'password': self.Utils.hash_password(password)}
                    query = f"SELECT user, level FROM {self.Config.TABLE_ADMIN} WHERE user = :user AND password = :password"

                result = self.Base.db_execute_query(query, mes_donnees)
                user_from_db = result.fetchone()
                if user_from_db:
                    return {'user': user_from_db[0], 'level': user_from_db[1]}
                else:
                    return None

            if s.message_type == 'C' and s.mechanisme == 'PLAIN':
                # Connection via PLAIN
                admin_info = db_get_admin_info(username=s.username, password=s.password)
                if admin_info is not None:
                    s.auth_success = True
                    s.level = admin_info.get('level', 0)
                    self.Protocol.send2socket(f":{self.Config.SERVEUR_LINK} SASL {self.Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D S")
                    self.Protocol.send2socket(f":{self.Config.SERVEUR_LINK} 903 {s.username} :SASL authentication successful")
                else:
                    self.Protocol.send2socket(f":{self.Config.SERVEUR_LINK} SASL {self.Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D F")
                    self.Protocol.send2socket(f":{self.Config.SERVEUR_LINK} 904 {s.username} :SASL authentication failed")

            elif s.message_type == 'S' and s.mechanisme == 'EXTERNAL':
                # Connection using fingerprints
                admin_info = db_get_admin_info(fingerprint=s.fingerprint)
                
                if admin_info is not None:
                    s.auth_success = True
                    s.level = admin_info.get('level', 0)
                    s.username = admin_info.get('user', None)
                    self.Protocol.send2socket(f":{self.Config.SERVEUR_LINK} SASL {self.Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D S")
                    self.Protocol.send2socket(f":{self.Config.SERVEUR_LINK} 903 {s.username} :SASL authentication successful")
                else:
                    # "904 <nick> :SASL authentication failed"
                    self.Protocol.send2socket(f":{self.Config.SERVEUR_LINK} SASL {self.Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D F")
                    self.Protocol.send2socket(f":{self.Config.SERVEUR_LINK} 904 {s.username} :SASL authentication failed")

    def __create_table(self) -> None:
        """## Create core tables
        """
        pass

    def get_defender_uptime(self) -> str:
        """Savoir depuis quand Defender est connecté

        Returns:
            str: L'écart entre la date du jour et celle de la connexion de Defender
        """
        current_datetime = datetime.now()
        diff_date = current_datetime - self.defender_connexion_datetime
        uptime = timedelta(days=diff_date.days, seconds=diff_date.seconds)

        return uptime

    def heartbeat(self, beat:float) -> None:
        """Execute certaines commandes de nettoyage toutes les x secondes
        x étant définit a l'initialisation de cette class (self.beat)

        Args:
            beat (float): Nombre de secondes entre chaque exécution
        """
        while self.hb_active:
            time.sleep(beat)
            self.Base.execute_periodic_action()

    def insert_db_admin(self, uid: str, account: str, level: int) -> None:
        user_obj = self.User.get_user(uid)
        if user_obj is None:
            return None
       
        self.Admin.insert(
            self.Loader.Definition.MAdmin(
                **user_obj.to_dict(),
                account=account,
                level=int(level)
            )
        )

        return None

    def delete_db_admin(self, uid:str) -> None:

        if self.Admin.get_admin(uid) is None:
            return None

        if not self.Admin.delete(uid):
            self.Logs.critical(f'UID: {uid} was not deleted')

        return None

    def create_defender_user(self, nickname: str, level: int, password: str) -> str:

        # > addaccess [nickname] [level] [password]

        get_user = self.User.get_user(nickname)
        level = self.Base.convert_to_int(level)
        password = password

        if get_user is None:
            response = f'This nickname {nickname} does not exist, it is not possible to create this user'
            self.Logs.warning(response)
            return response

        if level is None:
            response = f'The level [{level}] must be a number from 1 to 4'
            self.Logs.warning(response)
            return response

        if level > 4:
            response = "Impossible d'ajouter un niveau > 4"
            self.Logs.warning(response)
            return response

        nickname = get_user.nickname
        response = ''

        hostname = get_user.hostname
        vhost = get_user.vhost
        spassword = self.Loader.Utils.hash_password(password)

        mes_donnees = {'admin': nickname}
        query_search_user = f"SELECT id FROM {self.Config.TABLE_ADMIN} WHERE user=:admin"
        r = self.Base.db_execute_query(query_search_user, mes_donnees)
        exist_user = r.fetchone()

        # On verifie si le user exist dans la base
        if not exist_user:
            mes_donnees = {'datetime': self.Utils.get_sdatetime(), 'user': nickname, 'password': spassword, 'hostname': hostname, 'vhost': vhost, 'level': level}
            self.Base.db_execute_query(f'''INSERT INTO {self.Config.TABLE_ADMIN} 
                    (createdOn, user, password, hostname, vhost, level) VALUES
                    (:datetime, :user, :password, :hostname, :vhost, :level)
                    ''', mes_donnees)
            response = f"{nickname} ajouté en tant qu'administrateur de niveau {level}"
            self.Protocol.send_notice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=nickname, msg=response)
            self.Logs.info(response)
            return response
        else:
            response = f'{nickname} Existe déjà dans les users enregistrés'
            self.Protocol.send_notice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=nickname, msg=response)
            self.Logs.info(response)
            return response

    def thread_check_for_new_version(self, fromuser: str) -> None:
        dnickname = self.Config.SERVICE_NICKNAME

        if self.Base.check_for_new_version(True):
            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" New Version available : {self.Config.CURRENT_VERSION} >>> {self.Config.LATEST_VERSION}")
            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=" Please run (git pull origin main) in the current folder")
        else:
            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=" You have the latest version of defender")

        return None

    def cmd(self, data: list[str]) -> None:
        """Parse server response

        Args:
            data (list[str]): Server response splitted in a list
        """
        try:
            original_response: list[str] = data.copy()
            RED = self.Config.COLORS.red
            GREEN = self.Config.COLORS.green
            NOGC = self.Config.COLORS.nogc

            if len(original_response) < 2:
                self.Logs.warning(f'Size ({str(len(original_response))}) - {original_response}')
                return None

            self.Logs.debug(f">> {self.Utils.hide_sensitive_data(original_response)}")
            parsed_protocol = self.Protocol.parse_server_msg(original_response.copy())
            match parsed_protocol:

                case 'PING':
                    self.Protocol.on_server_ping(serverMsg=original_response)

                case 'SERVER':
                    self.Protocol.on_server(serverMsg=original_response)

                case 'SJOIN':
                    self.Protocol.on_sjoin(serverMsg=original_response)

                case 'EOS':
                    self.Protocol.on_eos(serverMsg=original_response)

                case 'UID':
                    try:
                        self.Protocol.on_uid(serverMsg=original_response)
                        for module in self.ModuleUtils.model_get_loaded_modules().copy():
                            module.class_instance.cmd(original_response)

                        # SASL authentication
                        # ['@s2s-md/..', ':001', 'UID', 'adator__', '0', '1755987444', '...', 'desktop-h1qck20.mshome.net', '001XLTT0U', '0', '+iwxz', '*', 'Clk-EC2256B2.mshome.net', 'rBKAAQ==', ':...']
                        dnickname = self.Config.SERVICE_NICKNAME
                        dchanlog = self.Config.SERVICE_CHANLOG
                        uid = original_response[8]
                        nickname = original_response[3]
                        sasl_obj = self.Sasl.get_sasl_obj(uid)
                        if sasl_obj:
                            if sasl_obj.auth_success:
                                self.insert_db_admin(sasl_obj.client_uid, sasl_obj.username, sasl_obj.level)
                                self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                  msg=tr("[ %sSASL AUTH%s ] - %s (%s) is now connected successfuly to %s", GREEN, NOGC, nickname, sasl_obj.username, dnickname),
                                                  channel=dchanlog)
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Successfuly connected to %s", dnickname))
                            else:
                                self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                        msg=tr("[ %sSASL AUTH%s ] - %s provided a wrong password for this username %s", RED, NOGC, nickname, sasl_obj.username),
                                                        channel=dchanlog)
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Wrong password!"))

                            # Delete sasl object!
                            self.Sasl.delete_sasl_client(uid)

                        return None
                    except Exception as err:
                        self.Logs.error(f'General Error: {err}')

                case 'QUIT':
                    self.Protocol.on_quit(serverMsg=original_response)

                case 'PROTOCTL':
                    self.Protocol.on_protoctl(serverMsg=original_response)

                case 'SVS2MODE':
                    # >> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']
                    self.Protocol.on_svs2mode(serverMsg=original_response)

                case 'SQUIT':
                    self.Protocol.on_squit(serverMsg=original_response)

                case 'PART':
                    self.Protocol.on_part(serverMsg=original_response)

                case 'VERSION':
                    self.Protocol.on_version_msg(serverMsg=original_response)

                case 'UMODE2':
                    # [':adator_', 'UMODE2', '-i']
                    self.Protocol.on_umode2(serverMsg=original_response)

                case 'NICK':
                    self.Protocol.on_nick(serverMsg=original_response)

                case 'REPUTATION':
                    self.Protocol.on_reputation(serverMsg=original_response)

                case 'SMOD':
                    self.Protocol.on_smod(original_response)

                case 'SASL':
                    sasl_response = self.Protocol.on_sasl(original_response, self.Sasl)
                    self.on_sasl_authentication_process(sasl_response)

                case 'SLOG': # TODO
                    self.Logs.debug(f"[!] TO HANDLE: {parsed_protocol}")

                case 'MD': # TODO
                    self.Logs.debug(f"[!] TO HANDLE: {parsed_protocol}")

                case 'PRIVMSG':
                    self.Protocol.on_privmsg(serverMsg=original_response)

                case 'PONG': # TODO
                    self.Logs.debug(f"[!] TO HANDLE: {parsed_protocol}")

                case 'MODE': # TODO
                    #['@msgid=d0ySx56Yd0nc35oHts2SkC-/J9mVUA1hfM6...', ':001', 'MODE', '#a', '+nt', '1723207536']
                    #['@unrealircd.org/userhost=adator@localhost;...', ':001LQ0L0C', 'MODE', '#services', '-l']
                    self.Logs.debug(f"[!] TO HANDLE: {parsed_protocol}")

                case '320': # TODO
                    #:irc.deb.biz.st 320 PyDefender IRCParis07 :is in security-groups: known-users,webirc-users,tls-and-known-users,tls-users
                    self.Logs.debug(f"[!] TO HANDLE: {parsed_protocol}")

                case '318': # TODO
                    #:irc.deb.biz.st 318 PyDefender IRCParis93 :End of /WHOIS list.
                    self.Logs.debug(f"[!] TO HANDLE: {parsed_protocol}")

                case None:
                    self.Logs.debug(f"[!] TO HANDLE: {original_response}")

            if len(original_response) > 2:
                if original_response[2] != 'UID':
                    # Envoyer la commande aux classes dynamiquement chargées
                    for module in self.ModuleUtils.model_get_loaded_modules().copy():
                        module.class_instance.cmd(original_response)

        except IndexError as ie:
            self.Logs.error(f"IndexError: {ie}")
        except Exception as err:
            self.Logs.error(f"General Error: {err}", exc_info=True)

    def hcmds(self, user: str, channel: Union[str, None], cmd: list, fullcmd: list = []) -> None:
        """Create

        Args:
            user (str): The user who sent the query
            channel (Union[str, None]): If the command contain the channel
            cmd (list): The defender cmd
            fullcmd (list, optional): The full list of the cmd coming from PRIVMS. Defaults to [].

        Returns:
            None: Nothing to return
        """

        fromuser = self.User.get_nickname(user)                                   # Nickname qui a lancé la commande
        uid = self.User.get_uid(fromuser)                                         # Récuperer le uid de l'utilisateur

        RED = self.Config.COLORS.red
        GREEN = self.Config.COLORS.green
        NOGC = self.Config.COLORS.nogc

        # Defender information
        dnickname = self.Config.SERVICE_NICKNAME                                  # Defender nickname
        dchanlog = self.Config.SERVICE_CHANLOG                                    # Defender chan log

        if len(cmd) > 0:
            command = str(cmd[0]).lower()
        else:
            return False

        if not self.Commands.is_client_allowed_to_run_command(fromuser, command):
            command = 'notallowed'

        # Envoyer la commande aux classes dynamiquement chargées
        if command != 'notallowed':
            for module in self.ModuleUtils.DB_MODULES:
                module.class_instance.hcmds(user, channel, cmd, fullcmd)

        match command:

            case 'notallowed':
                try:
                    current_command = str(cmd[0])
                    self.Protocol.send_priv_msg(
                        msg=tr('[ %s%s%s ] - Access denied to %s', RED, current_command.upper(), NOGC, fromuser),
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=tr('Access denied!')
                        )

                except IndexError as ie:
                    self.Logs.error(f'{ie}')

            case 'deauth':

                current_command = str(cmd[0]).upper()
                uid_to_deauth = self.User.get_uid(fromuser)
                self.delete_db_admin(uid_to_deauth)

                self.Protocol.send_priv_msg(
                        msg=tr("[ %s%s%s ] - %s has been disconnected from %s", RED, current_command, NOGC, fromuser, dnickname),
                        nick_from=dnickname,
                        channel=dchanlog
                        )

            case 'firstauth':
                # firstauth OWNER_NICKNAME OWNER_PASSWORD
                current_nickname = self.User.get_nickname(fromuser)
                current_uid = self.User.get_uid(fromuser)
                current_command = str(cmd[0])

                query = f"SELECT count(id) as c FROM {self.Config.TABLE_ADMIN}"
                result = self.Base.db_execute_query(query)
                result_db = result.fetchone()

                if result_db[0] > 0:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=tr("You can't use this command anymore ! Please use [%sauth] instead", self.Config.SERVICE_PREFIX)
                        )
                    return False

                if current_nickname is None:
                    self.Logs.critical(f"This nickname [{fromuser}] don't exist")
                    return False

                # Credentials sent from the user
                cmd_owner = str(cmd[1])
                cmd_password = str(cmd[2])

                # Credentials coming from the Configuration
                config_owner    = self.Config.OWNER
                config_password = self.Config.PASSWORD

                if current_nickname != cmd_owner:
                    self.Logs.critical(f"The current nickname [{fromuser}] is different than the nickname sent [{cmd_owner}] !")
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"The current nickname [{fromuser}] is different than the nickname sent [{cmd_owner}] !"
                        )
                    return False

                if current_nickname != config_owner:
                    self.Logs.critical(f"The current nickname [{current_nickname}] is different than the configuration owner [{config_owner}] !")
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"The current nickname [{current_nickname}] is different than the configuration owner [{config_owner}] !"
                        )
                    return False

                if cmd_owner != config_owner:
                    self.Logs.critical(f"The nickname sent [{cmd_owner}] is different than the configuration owner [{config_owner}] !")
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"The nickname sent [{cmd_owner}] is different than the configuration owner [{config_owner}] !"
                        )
                    return False

                if cmd_owner == config_owner and cmd_password == config_password:
                    self.Base.db_create_first_admin()
                    self.insert_db_admin(current_uid, cmd_owner, 5)
                    self.Protocol.send_priv_msg(
                        msg=f"[ {self.Config.COLORS.green}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} est désormais connecté a {dnickname}",
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Connexion a {dnickname} réussie!"
                        )
                else:
                    self.Protocol.send_priv_msg(
                        msg=f"[ {self.Config.COLORS.red}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} a tapé un mauvais mot de pass",
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Mot de passe incorrecte"
                        )

            case 'auth':
                # Syntax. !auth nickname password
                if len(cmd) < 3:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} [nickname] [password]")
                    return None

                current_command = cmd[0]
                user_to_log = cmd[1]
                password = cmd[2]
                current_client = self.User.get_user(fromuser)
                admin_obj = self.Admin.get_admin(fromuser)

                if current_client is None:
                    # This case should never happen
                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                msg=f"[ {GREEN}{str(current_command).upper()}{NOGC} ] - Nickname {fromuser} is trying to connect to defender wrongly",
                                                channel=dchanlog)
                    return None
                
                if admin_obj:
                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                msg=f"[ {GREEN}{str(current_command).upper()}{NOGC} ] - You are already connected to {dnickname}",
                                                channel=dchanlog)
                    return None

                mes_donnees = {'user': user_to_log, 'password': self.Loader.Utils.hash_password(password)}
                query = f"SELECT id, user, level FROM {self.Config.TABLE_ADMIN} WHERE user = :user AND password = :password"
                result = self.Base.db_execute_query(query, mes_donnees)
                user_from_db = result.fetchone()

                if user_from_db:
                    account = user_from_db[1]
                    level = user_from_db[2]
                    self.insert_db_admin(current_client.uid, account, level)
                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                msg=f"[ {GREEN}{str(current_command).upper()}{NOGC} ] - {current_client.nickname} ({account}) est désormais connecté a {dnickname}",
                                                channel=dchanlog)
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Connexion a {dnickname} réussie!")
                    return None
                else:
                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                msg=f"[ {RED}{str(current_command).upper()}{NOGC} ] - {current_client.nickname} a tapé un mauvais mot de pass",
                                                channel=dchanlog)
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Mot de passe incorrecte")
                    return None

            case 'addaccess':
                try:
                    # .addaccess adator 5 password
                    if len(cmd) < 4:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Right command : /msg {dnickname} addaccess [nickname] [level] [password]")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"level: from 1 to 4")

                    newnickname = cmd[1]
                    newlevel = self.Base.int_if_possible(cmd[2])
                    password = cmd[3]

                    response = self.create_defender_user(newnickname, newlevel, password)

                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"{response}")
                    self.Logs.info(response)

                except IndexError as ie:
                    self.Logs.error(f'_hcmd addaccess: {ie}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} addaccess [nickname] [level] [password]")
                except TypeError as te:
                    self.Logs.error(f'_hcmd addaccess: out of index : {te}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} addaccess [nickname] [level] [password]")

            case 'editaccess':
                # .editaccess [USER] [PASSWORD] [LEVEL]
                try:
                    if len(cmd) < 3:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Right command : /msg {dnickname} editaccess [nickname] [NEWPASSWORD] [NEWLEVEL]")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"level: from 1 to 4")
                        return None

                    user_to_edit = cmd[1]
                    user_password = self.Loader.Utils.hash_password(cmd[2])

                    get_admin = self.Admin.get_admin(fromuser)
                    if get_admin is None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"This user {fromuser} has no Admin access")
                        return None

                    current_user = self.User.get_nickname(fromuser)
                    current_uid = self.User.get_uid(fromuser)
                    current_user_level = get_admin.level

                    user_new_level = int(cmd[3]) if len(cmd) == 4 else get_admin.level

                    if current_user == fromuser:
                        user_new_level = get_admin.level

                    if user_new_level > 5:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Maximum authorized level is 5")
                        return None

                    # Rechercher le user dans la base de données.
                    mes_donnees = {'user': user_to_edit}
                    query = f"SELECT user, level FROM {self.Config.TABLE_ADMIN} WHERE user = :user"
                    result = self.Base.db_execute_query(query, mes_donnees)

                    isUserExist = result.fetchone()
                    if not isUserExist is None:

                        if current_user_level < int(isUserExist[1]):
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You are not allowed to edit this access")
                            return None

                        if current_user_level == int(isUserExist[1]) and current_user != user_to_edit:
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" You can't edit access of a user with same level")
                            return None

                        # Le user existe dans la base de données
                        data_to_update = {'user': user_to_edit, 'password': user_password, 'level': user_new_level}
                        sql_update = f"UPDATE {self.Config.TABLE_ADMIN} SET level = :level, password = :password WHERE user = :user"
                        exec_query = self.Base.db_execute_query(sql_update, data_to_update)
                        if exec_query.rowcount > 0:
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" User {user_to_edit} has been modified with level {str(user_new_level)}")
                            self.Admin.update_level(user_to_edit, user_new_level)
                        else:
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Impossible de modifier l'utilisateur {str(user_new_level)}")

                except TypeError as te:
                    self.Logs.error(f"Type error : {te}")
                except ValueError as ve:
                    self.Logs.error(f"Value Error : {ve}")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" {self.Config.SERVICE_PREFIX}editaccess [USER] [NEWPASSWORD] [NEWLEVEL]")

            case 'delaccess':
                # .delaccess [USER] [CONFIRMUSER]
                user_to_del = cmd[1]
                user_confirmation = cmd[2]

                if user_to_del != user_confirmation:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer")
                    self.Logs.warning(f':{dnickname} NOTICE {fromuser} : Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer')
                    return None

                if len(cmd) < 3:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"{self.Config.SERVICE_PREFIX}delaccess [USER] [CONFIRMUSER]")
                    return None

                get_admin = self.Admin.get_admin(fromuser)

                if get_admin is None:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"This user {fromuser} has no admin access")
                    return None

                current_user = self.User.get_nickname(fromuser)
                current_uid = self.User.get_uid(fromuser)
                current_user_level = get_admin.level

                # Rechercher le user dans la base de données.
                mes_donnees = {'user': user_to_del}
                query = f"SELECT user, level FROM {self.Config.TABLE_ADMIN} WHERE user = :user"
                result = self.Base.db_execute_query(query, mes_donnees)
                info_user = result.fetchone()

                if not info_user is None:
                    level_user_to_del = info_user[1]
                    if current_user_level <= level_user_to_del:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You are not allowed to delete this access")
                        self.Logs.warning(f':{dnickname} NOTICE {fromuser} : You are not allowed to delete this access')
                        return None

                    data_to_delete = {'user': user_to_del}
                    sql_delete = f"DELETE FROM {self.Config.TABLE_ADMIN} WHERE user = :user"
                    exec_query = self.Base.db_execute_query(sql_delete, data_to_delete)
                    if exec_query.rowcount > 0:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"User {user_to_del} has been deleted !")
                        self.Admin.delete(user_to_del)
                    else:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Impossible de supprimer l'utilisateur.")
                        self.Logs.warning(f":{dnickname} NOTICE {fromuser} : Impossible de supprimer l'utilisateur.")

            case 'cert':
                # Syntax !cert
                try:
                    admin_obj = self.Admin.get_admin(fromuser)
                    if admin_obj:
                        query = f'UPDATE {self.Config.TABLE_ADMIN} SET fingerprint = :fingerprint WHERE user = :user'
                        r = self.Base.db_execute_query(query, {'fingerprint': admin_obj.fingerprint, 'user': admin_obj.account})
                        if r.rowcount > 0:
                            self.Protocol.send_notice(dnickname, fromuser, f'[ {GREEN}CERT{NOGC} ] Your new fingerprint has been attached to your account. {admin_obj.fingerprint}')
                        else:
                            self.Protocol.send_notice(dnickname, fromuser, f'[ {RED}CERT{NOGC} ] Impossible to add your fingerprint.{admin_obj.fingerprint}')

                except Exception as e:
                    self.Logs.error(e)

            case 'register':
                # Syntax. Register PASSWORD EMAIL
                try:

                    if len(cmd) < 3:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f'/msg {self.Config.SERVICE_NICKNAME} {command.upper()} <PASSWORD> <EMAIL>'
                        )
                        return None

                    password = cmd[1]
                    email = cmd[2]

                    if not self.Base.is_valid_email(email_to_control=email):
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg='The email is not valid. You must provide a valid email address (first.name@email.extension)'
                        )
                        return None

                    user_obj = self.User.get_user(fromuser)

                    if user_obj is None:
                        self.Logs.error(f"Nickname ({fromuser}) doesn't exist, it is impossible to register this nickname")
                        return None

                    # If the account already exist.
                    if self.Client.db_is_account_exist(fromuser):
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f"Your account already exist, please try to login instead /msg {self.Config.SERVICE_NICKNAME} IDENTIFY <account> <password>"
                        )
                        return None

                    # If the account doesn't exist then insert into database
                    data_to_record = {
                        'createdOn': self.Utils.get_sdatetime(), 'account': fromuser,
                        'nickname': user_obj.nickname, 'hostname': user_obj.hostname, 'vhost': user_obj.vhost, 'realname': user_obj.realname, 'email': email,
                        'password': self.Loader.Utils.hash_password(password=password), 'level': 0
                    }

                    insert_to_db = self.Base.db_execute_query(f"""
                                                            INSERT INTO {self.Config.TABLE_CLIENT} 
                                                            (createdOn, account, nickname, hostname, vhost, realname, email, password, level)
                                                            VALUES
                                                            (:createdOn, :account, :nickname, :hostname, :vhost, :realname, :email, :password, :level)
                                                            """, data_to_record)

                    if insert_to_db.rowcount > 0:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f"You have register your nickname successfully"
                        )

                    return None

                except ValueError as ve:
                    self.Logs.error(f"Value Error : {ve}")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" {self.Config.SERVICE_PREFIX}{command.upper()} <PASSWORD> <EMAIL>")

            case 'identify':
                # Identify ACCOUNT PASSWORD
                try:
                    if len(cmd) < 3:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f'/msg {self.Config.SERVICE_NICKNAME} {command.upper()} <ACCOUNT> <PASSWORD>'
                        )
                        return None

                    account = str(cmd[1]) # account
                    encrypted_password = self.Loader.Utils.hash_password(cmd[2])
                    user_obj = self.User.get_user(fromuser)
                    client_obj = self.Client.get_Client(user_obj.uid)

                    if client_obj is not None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You are already logged in")
                        return None

                    db_query = f"SELECT account FROM {self.Config.TABLE_CLIENT} WHERE account = :account AND password = :password"
                    db_param = {'account': account, 'password': encrypted_password}
                    exec_query = self.Base.db_execute_query(db_query, db_param)
                    result_query = exec_query.fetchone()
                    if result_query:
                        account = result_query[0]
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You are now logged in")
                        client = self.Loader.Definition.MClient(**user_obj.to_dict(), account=account)
                        self.Client.insert(client)
                        self.Protocol.send_svslogin(user_obj.uid, account)
                        self.Protocol.send_svs2mode(nickname=fromuser, user_mode='+r')
                    else:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Wrong password or account")

                    return None

                except ValueError as ve:
                    self.Logs.error(f"Value Error: {ve}")
                    self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f'/msg {self.Config.SERVICE_NICKNAME} {command.upper()} <ACCOUNT> <PASSWORD>'
                        )

                except Exception as err:
                    self.Logs.error(f"General Error: {err}")

            case 'logout':
                try:
                    # LOGOUT <account>
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} <account>")
                        return None

                    user_obj = self.User.get_user(fromuser)
                    if user_obj is None:
                        self.Logs.error(f"The User [{fromuser}] is not available in the database")
                        return None

                    client_obj = self.Client.get_Client(user_obj.uid)

                    if client_obj is None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Nothing to logout. please login first")
                        return None

                    self.Protocol.send_svslogout(client_obj)
                    # self.Protocol.send_svsmode(nickname=fromuser, user_mode='-r')
                    self.Client.delete(user_obj.uid)
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You have been logged out successfully")

                except ValueError as ve:
                    self.Logs.error(f"Value Error: {ve}")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} <account>")
                except Exception as err:
                    self.Logs.error(f"General Error: {err}")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} <account>")

            case 'help':
                # Syntax. !help [module_name]
                module_name = str(cmd[1]) if len(cmd) == 2 else None
                self.generate_help_menu(nickname=fromuser, module=module_name)
                return None
                
            case 'load':
                try:
                    # Load a module ex: .load mod_defender
                    mod_name = str(cmd[1])
                    self.ModuleUtils.load_one_module(self, mod_name, fromuser)
                    return None
                except KeyError as ke:
                    self.Logs.error(f"Key Error: {ke} - list recieved: {cmd}")
                except Exception as err:
                    self.Logs.error(f"General Error: {ke} - list recieved: {cmd}")

            case 'unload':
                # unload mod_defender
                try:
                    # The module name. exemple: mod_defender
                    module_name = str(cmd[1]).lower()
                    self.ModuleUtils.unload_one_module(self, module_name, False)
                    return None
                except Exception as err:
                    self.Logs.error(f"General Error: {err}")

            case 'reload':
                # reload mod_defender
                try:
                    # ==> mod_defender
                    module_name = str(cmd[1]).lower()
                    self.ModuleUtils.reload_one_module(self, module_name, fromuser)
                    return None
                except Exception as e:
                    self.Logs.error(f"Something went wrong with a module you want to reload: {e}")
                    self.Protocol.send_priv_msg(
                        nick_from=dnickname,
                        msg=f"Something went wrong with the module: {e}",
                        channel=dchanlog
                    )
                    self.ModuleUtils.db_delete_module(module_name)

            case 'quit':
                try:
                    final_reason = ' '.join(cmd[1:])
                    self.hb_active = False
                    self.Base.shutdown()
                    self.Base.execute_periodic_action()

                    for chan_name in self.Channel.UID_CHANNEL_DB:
                        self.Protocol.send_mode_chan(chan_name.name, '-l')
                    
                    for client in self.Client.CLIENT_DB:
                        self.Protocol.send_svslogout(client)

                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Arrêt du service {dnickname}"
                    )
                    self.Protocol.send_squit(server_id=self.Config.SERVEUR_ID, server_link=self.Config.SERVEUR_LINK, reason=final_reason)
                    self.Logs.info(f'Arrêt du server {dnickname}')
                    self.Config.DEFENDER_RESTART = 0
                    self.signal = False

                except IndexError as ie:
                    self.Logs.error(f'{ie}')

            case 'restart':
                final_reason = ' '.join(cmd[1:])
                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"{dnickname.capitalize()} is going to restart!")
                self.Config.DEFENDER_RESTART = 1                 # Set restart status to 1 saying that the service will restart
                self.Config.DEFENDER_INIT = 1                    # set init to 1 saying that the service will be re initiated

            case 'rehash':
                rehash.rehash_service(self.ircObject, fromuser)
                return None

            case 'show_modules':
                self.Logs.debug('List of modules: ' + ', '.join([module.module_name for module in self.ModuleUtils.model_get_loaded_modules()]))
                all_modules  = self.ModuleUtils.get_all_available_modules()
                loaded = False
                results = self.Base.db_execute_query(f'SELECT datetime, user, module_name FROM {self.Config.TABLE_MODULE}')
                results = results.fetchall()

                for module in all_modules:
                    for loaded_mod in results:
                        if module == loaded_mod[2]:
                            loaded_datetime = loaded_mod[0]
                            loaded_user = loaded_mod[1]
                            loaded = True

                    if loaded:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f"{module} - {GREEN}Loaded{NOGC} by {loaded_user} on {loaded_datetime}"
                        )
                        loaded = False
                    else:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f"{module} - {RED}Not Loaded{NOGC}"
                        )

            case 'show_timers':
                if self.Base.running_timers:
                    for the_timer in self.Base.running_timers:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f">> {the_timer.name} - {the_timer.is_alive()}"
                        )
                else:
                    self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg="There is no timers that are running!"
                        )
                return None

            case 'show_threads':
                for thread in self.Base.running_threads:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f">> {thread.name} ({thread.is_alive()})"
                    )
                return None

            case 'show_channels':
                for chan in self.Channel.UID_CHANNEL_DB:
                    list_nicknames: list = []
                    for uid in chan.uids:
                        pattern = fr'[:|@|%|\+|~|\*]*'
                        parsed_UID = re.sub(pattern, '', uid)
                        list_nicknames.append(self.User.get_nickname(parsed_UID))

                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Channel: {chan.name} - Users: {list_nicknames}"
                    )
                return None

            case 'show_users':
                count_users = len(self.User.UID_DB)
                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Total Connected Users: {count_users}")
                for db_user in self.User.UID_DB:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_user.uid} - isWebirc: {db_user.isWebirc} - isWebSocket: {db_user.isWebsocket} - Nickname: {db_user.nickname} - Connection: {db_user.connexion_datetime}"
                    )
                return None

            case 'show_clients':
                count_users = len(self.Client.CLIENT_DB)
                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Total Connected Clients: {count_users}")
                for db_client in self.Client.CLIENT_DB:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_client.uid} - isWebirc: {db_client.isWebirc} - isWebSocket: {db_client.isWebsocket} - Nickname: {db_client.nickname} - Account: {db_client.account} - Connection: {db_client.connexion_datetime}"
                    )
                return None

            case 'show_admins':
                for db_admin in self.Admin.UID_ADMIN_DB:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_admin.uid} - Nickname: {db_admin.nickname} - Account: {db_admin.account} - Level: {db_admin.level} - Connection: {db_admin.connexion_datetime}"
                    )
                return None

            case 'show_configuration':
                for key, value in self.Config.to_dict().items():
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f'{key} = {value}'
                        )
                return None

            case 'show_cache':
                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"The cache is currently contains {self.Settings.get_cache_size()} value(s).")
                for key, value in self.Settings.show_cache().items():
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Key : {key} - Value: {value}"
                    )
                return None
            
            case 'clear_cache':
                cache_size = self.Settings.get_cache_size()
                if cache_size > 0:
                    self.Settings.clear_cache()
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"{cache_size} value(s) has been cleared from the cache.")
                return None

            case 'uptime':
                uptime = self.get_defender_uptime()
                self.Protocol.send_notice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f"{uptime}"
                )
                return None

            case 'copyright':
                self.Protocol.send_notice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f">> Defender V.{self.Config.CURRENT_VERSION} Developped by adator®."
                )
                return None

            case 'checkversion':
                self.Base.create_thread(self.thread_check_for_new_version, (fromuser, ))
                return None

            case 'raw':
                raw_command = ' '.join(cmd[1:])
                self.Protocol.send_raw(raw_command)
                return None

            case _:
                pass
