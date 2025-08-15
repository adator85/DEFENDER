import sys
import socket
import threading
import ssl
import re
import importlib
import time
import traceback
from ssl import SSLSocket
from datetime import datetime, timedelta
from typing import Optional, Union
from core.loader import Loader
from core.classes.protocol import Protocol
from core.classes.commands import Command

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
        self.Logs = self.Loader.Base.logs

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

        self.autolimit_started: bool = False
        """This variable is to make sure the thread is not running"""

        # define first reputation score to 0
        self.first_score: int = 0

        # Define first IP connexion
        self.first_connexion_ip: str = None

        # Define the dict that will contain all loaded modules
        self.loaded_classes:dict[str, 'Irc'] = {}

        # Load Commands Utils
        self.Commands = self.Loader.Commands
        """Command utils"""

        # Global full module commands that contains level, module name, commands and description
        self.module_commands: dict[int, dict[str, dict[str, str]]] = {}

        # Global command list contains only the commands
        self.module_commands_list: list[str] = []

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
        self.build_command(3, 'core', 'quit', 'Disconnect the bot or user from the server.')
        self.build_command(3, 'core', 'restart', 'Restart the bot or service.')
        self.build_command(3, 'core', 'addaccess', 'Add a user or entity to an access list with specific permissions.')
        self.build_command(3, 'core', 'editaccess', 'Modify permissions for an existing user or entity in the access list.')
        self.build_command(3, 'core', 'delaccess', 'Remove a user or entity from the access list.')
        self.build_command(4, 'core', 'rehash', 'Reload the configuration file without restarting')
        self.build_command(4, 'core', 'raw', 'Send a raw command directly to the IRC server')


        # Define the IrcSocket object
        self.IrcSocket:Union[socket.socket, SSLSocket] = None

        self.__create_table()
        self.Base.create_thread(func=self.heartbeat, func_args=(self.beat, ))

    ##############################################
    #               CONNEXION IRC                #
    ##############################################
    def init_irc(self, ircInstance:'Irc') -> None:
        """Create a socket and connect to irc server

        Args:
            ircInstance (Irc): Instance of Irc object.
        """
        try:
            self.init_service_user()
            self.__create_socket()
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

    def __create_socket(self) -> None:
        """Create a socket to connect SSL or Normal connection
        """
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM or socket.SOCK_NONBLOCK)
            connexion_information = (self.Config.SERVEUR_IP, self.Config.SERVEUR_PORT)

            if self.Config.SERVEUR_SSL:
                # Créer un object ssl
                ssl_context = self.__ssl_context()
                ssl_connexion = ssl_context.wrap_socket(soc, server_hostname=self.Config.SERVEUR_HOSTNAME)
                ssl_connexion.connect(connexion_information)
                self.IrcSocket:SSLSocket = ssl_connexion
                self.Config.SSL_VERSION = self.IrcSocket.version()
                self.Logs.info(f"-- Connexion en mode SSL : Version = {self.Config.SSL_VERSION}")
            else:
                soc.connect(connexion_information)
                self.IrcSocket:socket.socket = soc
                self.Logs.info("-- Connexion en mode normal")

            return None

        except ssl.SSLEOFError as soe:
            self.Logs.critical(f"SSLEOFError: {soe} - {soc.fileno()}")
        except ssl.SSLError as se:
            self.Logs.critical(f"SSLError: {se} - {soc.fileno()}")
        except OSError as oe:
            self.Logs.critical(f"OSError: {oe} - {soc.fileno()}")
            if 'connection refused' in str(oe).lower():
                sys.exit(oe)
            if soc.fileno() == -1:
                sys.exit(soc.fileno())

        except AttributeError as ae:
            self.Logs.critical(f"AttributeError: {ae} - {soc.fileno()}")

    def __ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.Logs.debug(f'-- SSLContext initiated with verified mode {ctx.verify_mode}')

        return ctx

    def __connect_to_irc(self, ircInstance: 'Irc') -> None:
        try:

            self.init_service_user()
            self.ircObject = ircInstance                        # créer une copie de l'instance Irc
            self.Protocol = Protocol(
                protocol=self.Config.SERVEUR_PROTOCOL,
                ircInstance=self.ircObject
                ).Protocol
            self.Protocol.link()                                # Etablir le link en fonction du protocol choisi
            self.signal = True                                  # Une variable pour initier la boucle infinie
            self.__join_saved_channels()                        # Join existing channels
            self.load_existing_modules()                        # Charger les modules existant dans la base de données

            while self.signal:
                try:
                    if self.Config.DEFENDER_RESTART == 1:
                        self.Logs.debug('Restarting Defender ...')
                        self.IrcSocket.shutdown(socket.SHUT_RDWR)
                        self.IrcSocket.close()

                        while self.IrcSocket.fileno() != -1:
                            time.sleep(0.5)
                            self.Logs.warning('--* Waiting for socket to close ...')

                        # Reload configuration
                        self.Logs.debug('Reloading configuration')
                        self.Config = self.Loader.ConfModule.Configuration().ConfigObject
                        self.Base = self.Loader.BaseModule.Base(self.Config, self.Settings)
                        self.Protocol = Protocol(self.Config.SERVEUR_PROTOCOL, ircInstance).Protocol

                        self.init_service_user()
                        self.__create_socket()
                        self.Protocol.link()
                        self.__join_saved_channels()
                        self.load_existing_modules()
                        self.Config.DEFENDER_RESTART = 0

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
                    print("Connexion reset")

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
            self.Logs.critical(f"General Error: {e}")
            self.Logs.critical(traceback.format_exc())

    def __join_saved_channels(self) -> None:
        """## Joining saved channels"""
        core_table = self.Config.TABLE_CHANNEL

        query = f'''SELECT distinct channel_name FROM {core_table}'''
        exec_query = self.Base.db_execute_query(query)
        result_query = exec_query.fetchall()

        if result_query:
            for chan_name in result_query:
                chan = chan_name[0]
                self.Protocol.sjoin(channel=chan)

    def send_response(self, responses:list[bytes]) -> None:
        try:
            # print(responses)
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
        self.module_commands.setdefault(level, {}).setdefault(module_name, {}).update({command_name: command_description})
        self.module_commands_list.append(command_name)

        # Build Model.
        self.Commands.build(self.Loader.Definition.MCommand(module_name, command_name, command_description, level))

        return None

    def generate_help_menu(self, nickname: str, module: Optional[str] = None) -> None:

        # Check if the nickname is an admin
        p = self.Protocol
        admin_obj = self.Admin.get_admin(nickname)
        dnickname = self.Config.SERVICE_NICKNAME
        color_bold = self.Config.COLORS.bold
        color_nogc = self.Config.COLORS.nogc
        color_blue = self.Config.COLORS.blue
        color_black = self.Config.COLORS.black
        color_underline = self.Config.COLORS.underline
        current_level = 0
        count = 0
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
        
        return

        for level, modules in self.module_commands.items():
            if level > current_level:
                break

            if count > 0:
                p.send_notice(nick_from=dnickname, nick_to=nickname, msg=" ")

            p.send_notice(
                nick_from=dnickname, 
                nick_to=nickname, 
                msg=f"{color_blue}{color_bold}Level {level}:{color_nogc}"
                )

            for module_name, commands in modules.items():
                if module is None or module.lower() == module_name.lower():
                    p.send_notice(
                        nick_from=dnickname, 
                        nick_to=nickname, 
                        msg=f"{color_black}  {color_underline}Module: {module_name}{color_nogc}"
                        )
                    for command, description in commands.items():
                        p.send_notice(nick_from=dnickname, nick_to=nickname, msg=f"    {command:<20}: {description}")

            count += 1

        p.send_notice(nick_from=dnickname,nick_to=nickname,msg=f" ***************** FIN DES COMMANDES *****************")
        return None

    def generate_help_menu_bakcup(self, nickname: str) -> None:

        # Check if the nickname is an admin
        admin_obj = self.Admin.get_admin(nickname)
        dnickname = self.Config.SERVICE_NICKNAME
        color_bold = self.Config.COLORS.bold
        color_nogc = self.Config.COLORS.nogc
        color_blue = self.Config.COLORS.blue
        color_black = self.Config.COLORS.black
        color_underline = self.Config.COLORS.underline
        current_level = 0
        count = 0
        if admin_obj is not None:
            current_level = admin_obj.level

        self.Protocol.send_notice(nick_from=dnickname,nick_to=nickname, msg=f" ***************** LISTE DES COMMANDES *****************")

        for level, modules in self.module_commands.items():
            if level > current_level:
                break

            if count > 0:
                self.Protocol.send_notice(nick_from=dnickname, nick_to=nickname, msg=" ")

            self.Protocol.send_notice(nick_from=dnickname, nick_to=nickname, msg=f"{color_blue}{color_bold}Level {level}:{color_nogc}")
            for module_name, commands in modules.items():
                self.Protocol.send_notice(nick_from=dnickname, nick_to=nickname, msg=f"{color_black}  {color_underline}Module: {module_name}{color_nogc}")
                for command, description in commands.items():
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=nickname, msg=f"    {command:<20}: {description}")

            count += 1

        self.Protocol.send_notice(nick_from=dnickname,nick_to=nickname,msg=f" ***************** FIN DES COMMANDES *****************")
        return None

    def is_cmd_allowed(self, nickname: str, command_name: str) -> bool:

        admin_obj = self.Admin.get_admin(nickname)
        current_level = 0

        if admin_obj is not None:
            current_level = admin_obj.level

        for level, modules in self.module_commands.items():
            for module_name, commands in modules.items():
                for command, description in commands.items():
                    if command.lower() == command_name.lower() and level <= current_level:
                        return True

        return False

    def __create_table(self):
        """## Create core tables
        """
        pass

    def load_existing_modules(self) -> None:
        """Charge les modules qui existe déja dans la base de données

        Returns:
            None: Aucun retour requis, elle charge puis c'est tout
        """
        result = self.Base.db_execute_query(f"SELECT module_name FROM {self.Config.TABLE_MODULE}")
        for r in result.fetchall():
            self.load_module('sys', r[0], True)

        return None

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
            service_id = self.Config.SERVICE_ID
            hsid = self.HSID
            self.Base.execute_periodic_action()

    def create_ping_timer(self, time_to_wait:float, class_name:str, method_name: str, method_args: list=[]) -> None:
        # 1. Timer créer
        #   1.1 Créer la fonction a executer
        #   1.2 Envoyer le ping une fois le timer terminer
        # 2. Executer la fonction
        try:
            if not class_name in self.loaded_classes:
                self.Logs.error(f"La class [{class_name} n'existe pas !!]")
                return False

            class_instance = self.loaded_classes[class_name]

            t = threading.Timer(interval=time_to_wait, function=self.__create_tasks, args=(class_instance, method_name, method_args))
            t.start()

            self.Base.running_timers.append(t)

            self.Logs.debug(f"Timer ID : {str(t.ident)} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.Logs.error(f'Assertion Error -> {ae}')
        except TypeError as te:
            self.Logs.error(f"Type error -> {te}")

    def __create_tasks(self, obj: object, method_name: str, param:list) -> None:
        """#### Ajouter les méthodes a éxecuter dans un dictionnaire

        Args:
            obj (object): Une instance de la classe qui va etre executer
            method_name (str): Le nom de la méthode a executer
            param (list): les parametres a faire passer

        Returns:
            None: aucun retour attendu
        """
        self.Base.periodic_func[len(self.Base.periodic_func) + 1] = {
            'object': obj,
            'method_name': method_name,
            'param': param
            }

        self.Logs.debug(f'Function to execute : {str(self.Base.periodic_func)}')
        self.send_ping_to_sereur()
        return None

    def send_ping_to_sereur(self) -> None:
        """### Envoyer un PING au serveur   
        """
        service_id = self.Config.SERVICE_ID
        hsid = self.HSID
        self.Protocol.send2socket(f':{service_id} PING :{hsid}')

        return None

    def load_module(self, fromuser:str, module_name:str, init:bool = False) -> bool:
        try:
            # module_name : mod_voice
            module_name = module_name.lower()
            module_folder = module_name.split('_')[1].lower() # ==> voice
            class_name = module_name.split('_')[1].capitalize() # ==> Voice

            # print(self.loaded_classes)

            # Si le module est déja chargé
            if 'mods.' + module_name in sys.modules:
                self.Logs.info("Module déja chargé ...")
                self.Logs.info('module name = ' + module_name)
                if class_name in self.loaded_classes:
                    # Si le module existe dans la variable globale retourne False
                    self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Le module {module_name} est déja chargé ! si vous souhaiter le recharge tapez {self.Config.SERVICE_PREFIX}reload {module_name}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                    return False

                the_module = sys.modules[f'mods.{module_folder}.{module_name}']
                importlib.reload(the_module)
                my_class = getattr(the_module, class_name, None)
                new_instance = my_class(self.ircObject)
                self.loaded_classes[class_name] = new_instance

                # Créer le module dans la base de données
                if not init:
                    self.Base.db_record_module(fromuser, module_name)

                self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} chargé",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                return False

            # Charger le module
            loaded_module = importlib.import_module(f'mods.{module_folder}.{module_name}')

            my_class = getattr(loaded_module, class_name, None)                 # Récuperer le nom de classe
            create_instance_of_the_class = my_class(self.ircObject)             # Créer une nouvelle instance de la classe

            if not hasattr(create_instance_of_the_class, 'cmd'):
                self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} ne contient pas de méthode cmd",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                self.Logs.critical(f"The Module {module_name} has not been loaded because cmd method is not available")
                self.Base.db_delete_module(module_name)
                return False

            # Charger la nouvelle class dans la variable globale
            self.loaded_classes[class_name] = create_instance_of_the_class

            # Enregistrer le module dans la base de données
            if not init:
                self.Base.db_record_module(fromuser, module_name)

            self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} chargé",
                        channel=self.Config.SERVICE_CHANLOG
                    )

            self.Logs.info(f"Module {class_name} has been loaded")

            return True

        except ModuleNotFoundError as moduleNotFound:
            self.Logs.error(f"MODULE_NOT_FOUND: {moduleNotFound}")
            self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"[ {self.Config.COLORS.red}MODULE_NOT_FOUND{self.Config.COLORS.black} ]: {moduleNotFound}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
        except Exception as err:
            self.Logs.error(f"Something went wrong with a module you want to load : {err}")
            self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"[ {self.Config.COLORS.red}ERROR{self.Config.COLORS.black} ]: {err}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
            traceback.print_exc()

    def unload_module(self, mod_name: str) -> bool:
        """Unload a module

        Args:
            mod_name (str): Module name ex mod_defender

        Returns:
            bool: True if success
        """
        try:
            module_name = mod_name.lower()                              # Le nom du module. exemple: mod_defender
            class_name = module_name.split('_')[1].capitalize()            # Nom de la class. exemple: Defender

            if class_name in self.loaded_classes:
                self.loaded_classes[class_name].unload()
                del self.loaded_classes[class_name]

                # Supprimer le module de la base de données
                self.Base.db_delete_module(module_name)

                self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} supprimé",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                return True

        except Exception as err:
            self.Logs.error(f"General Error: {err}")
            return False

    def reload_module(self, from_user: str, mod_name: str) -> bool:
        try:
            module_name = mod_name.lower()                       # ==> mod_defender
            module_folder = module_name.split('_')[1].lower()    # ==> defender
            class_name = module_name.split('_')[1].capitalize()  # ==> Defender

            if f'mods.{module_folder}.{module_name}' in sys.modules:
                self.Logs.info('Unload the module ...')
                self.loaded_classes[class_name].unload()
                self.Logs.info('Module Already Loaded ... reloading the module ...')

                # Load dependencies
                self.Base.reload_modules_with_dependencies(f'mods.{module_folder}')
                the_module = sys.modules[f'mods.{module_folder}.{module_name}']
                importlib.reload(the_module)

                # Supprimer la class déja instancier
                if class_name in self.loaded_classes:
                    del self.loaded_classes[class_name]

                my_class = getattr(the_module, class_name, None)
                new_instance = my_class(self.ircObject)
                self.loaded_classes[class_name] = new_instance

                self.Base.db_update_module(from_user, mod_name)
                self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} rechargé",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                return False
            else:
                self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} n'est pas chargé !",
                        channel=self.Config.SERVICE_CHANLOG
                    )

        except TypeError as te:
            self.Logs.error(f"A TypeError raised: {te}")
            self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"A TypeError raised: {te}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
        except AttributeError as ae:
            self.Logs.error(f"Missing Attribute: {ae}")
            self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Missing Attribute: {ae}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
        except KeyError as ke:
            self.Logs.error(f"Key Error: {ke}")
            self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Key Error: {ke}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
        except Exception as e:
            self.Logs.error(f"Something went wrong with a module you want to reload: {e}")
            self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Something went wrong with the module: {e}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)

    def insert_db_admin(self, uid:str, level:int) -> None:

        if self.User.get_User(uid) is None:
            return None

        getUser = self.User.get_user_asdict(uid)

        level = int(level)

        self.Admin.insert(
            self.Loader.Definition.MAdmin(
                **getUser,
                level=level
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

        get_user = self.User.get_User(nickname)
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

    def logs(self, log_msg:str) -> None:
        """Log to database if you want

        Args:
            log_msg (str): the message to log
        """
        try:
            mes_donnees = {'datetime': self.Utils.get_sdatetime(), 'server_msg': log_msg}
            self.Base.db_execute_query(f'INSERT INTO {self.Config.TABLE_LOG} (datetime, server_msg) VALUES (:datetime, :server_msg)', mes_donnees)

            return None
        except Exception as err:
            self.Logs.error(f"General Error: {err}")

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
            interm_response: list[str] = data.copy()
            """This the original without first value"""
            interm_response.pop(0)

            if len(original_response) == 0 or len(original_response) == 1:
                self.Logs.warning(f'Size ({str(len(original_response))}) - {original_response}')
                return False

            if len(original_response) == 7:
                if original_response[2] == 'PRIVMSG' and original_response[4] == ':auth':
                    data_copy = original_response.copy()
                    data_copy[6] = '**********'
                    self.Logs.debug(f">> {data_copy}")
                else:
                    self.Logs.debug(f">> {original_response}")
            else:
                self.Logs.debug(f">> {original_response}")

            parsed_protocol = self.Protocol.parse_server_msg(original_response.copy())

            match parsed_protocol:

                case 'PING':
                    self.Protocol.on_server_ping(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")
                    return None

                case 'SJOIN':
                    self.Protocol.on_sjoin(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'EOS':
                    self.Protocol.on_eos(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'UID':
                    try:
                        self.Protocol.on_uid(serverMsg=original_response)

                        for classe_name, classe_object in self.loaded_classes.items():
                            classe_object.cmd(original_response)

                        self.Logs.debug(f"** handle {parsed_protocol}")

                    except Exception as err:
                        self.Logs.error(f'General Error: {err}')

                case 'QUIT':
                    self.Protocol.on_quit(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'PROTOCTL':
                    self.Protocol.on_protoctl(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'SVS2MODE':
                    # >> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']
                    self.Protocol.on_svs2mode(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'SQUIT':
                    self.Protocol.on_squit(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'PART':
                    self.Protocol.on_part(serverMsg=parsed_protocol)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'VERSION':
                    self.Protocol.on_version_msg(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'UMODE2':
                    # [':adator_', 'UMODE2', '-i']
                    self.Protocol.on_umode2(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'NICK':
                    self.Protocol.on_nick(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'REPUTATION':
                    self.Protocol.on_reputation(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'SLOG': # TODO
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'MD': # TODO
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'PRIVMSG':
                    self.Protocol.on_privmsg(serverMsg=original_response)
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'PONG': # TODO
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case 'MODE': # TODO
                    #['@msgid=d0ySx56Yd0nc35oHts2SkC-/J9mVUA1hfM6...', ':001', 'MODE', '#a', '+nt', '1723207536']
                    #['@unrealircd.org/userhost=adator@localhost;...', ':001LQ0L0C', 'MODE', '#services', '-l']
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case '320': # TODO
                    #:irc.deb.biz.st 320 PyDefender IRCParis07 :is in security-groups: known-users,webirc-users,tls-and-known-users,tls-users
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case '318': # TODO
                    #:irc.deb.biz.st 318 PyDefender IRCParis93 :End of /WHOIS list.
                    self.Logs.debug(f"** handle {parsed_protocol}")

                case None:
                    self.Logs.debug(f"** TO BE HANDLE {original_response}")

            if len(original_response) > 2:
                if original_response[2] != 'UID':
                    # Envoyer la commande aux classes dynamiquement chargées
                    for classe_name, classe_object in self.loaded_classes.items():
                        classe_object.cmd(original_response)

        except IndexError as ie:
            self.Logs.error(f"{ie} / {original_response} / length {str(len(original_response))}")
        except Exception as err:
            self.Logs.error(f"General Error: {err}")
            self.Logs.error(f"General Error: {traceback.format_exc()}")

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

        # Defender information
        dnickname = self.Config.SERVICE_NICKNAME                                  # Defender nickname
        dchanlog = self.Config.SERVICE_CHANLOG                                    # Defender chan log

        if len(cmd) > 0:
            command = str(cmd[0]).lower()
        else:
            return False

        is_command_allowed = self.is_cmd_allowed(fromuser, command)
        if not is_command_allowed:
            command = 'notallowed'

        # Envoyer la commande aux classes dynamiquement chargées
        if command != 'notallowed':
            for classe_name, classe_object in self.loaded_classes.items():
                classe_object.hcmds(user, channel, cmd, fullcmd)

        match command:

            case 'notallowed':
                try:
                    current_command = cmd[0]
                    self.Protocol.send_priv_msg(
                        msg=f'[ {self.Config.COLORS.red}{current_command}{self.Config.COLORS.black} ] - Accès Refusé à {self.User.get_nickname(fromuser)}',
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f'Accès Refusé'
                        )

                except IndexError as ie:
                    self.Logs.error(f'{ie}')

            case 'deauth':

                current_command = cmd[0]
                uid_to_deauth = self.User.get_uid(fromuser)
                self.delete_db_admin(uid_to_deauth)

                self.Protocol.send_priv_msg(
                        msg=f"[ {self.Config.COLORS.red}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} est désormais déconnecter de {dnickname}",
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
                        msg=f"You can't use this command anymore ! Please use [{self.Config.SERVICE_PREFIX}auth] instead"
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
                    self.insert_db_admin(current_uid, 5)
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
                # ['auth', 'adator', 'password']
                if len(cmd) != 3:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} [nickname] [password]")
                    return None

                current_command = cmd[0]
                user_to_log = self.User.get_nickname(cmd[1])
                password = cmd[2]

                if fromuser != user_to_log:
                    # If the current nickname is different from the nickname you want to log in with
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Your current nickname is different from the nickname you want to log in with")
                    return False

                if not user_to_log is None:
                    mes_donnees = {'user': user_to_log, 'password': self.Loader.Utils.hash_password(password)}
                    query = f"SELECT id, level FROM {self.Config.TABLE_ADMIN} WHERE user = :user AND password = :password"
                    result = self.Base.db_execute_query(query, mes_donnees)
                    user_from_db = result.fetchone()

                    if not user_from_db is None:
                        uid_user = self.User.get_uid(user_to_log)
                        self.insert_db_admin(uid_user, user_from_db[1])
                        self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                  msg=f"[ {self.Config.COLORS.green}{str(current_command).upper()} ]{self.Config.COLORS.nogc} - {self.User.get_nickname(fromuser)} est désormais connecté a {dnickname}",
                                                  channel=dchanlog)
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Connexion a {dnickname} réussie!")
                    else:
                        self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                  msg=f"[ {self.Config.COLORS.red}{str(current_command).upper()} ]{self.Config.COLORS.nogc} - {self.User.get_nickname(fromuser)} a tapé un mauvais mot de pass",
                                                  channel=dchanlog)
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Mot de passe incorrecte")

                else:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"L'utilisateur {user_to_log} n'existe pas")

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

            case 'register':
                # Register PASSWORD EMAIL
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

                    user_obj = self.User.get_User(fromuser)

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
                    user_obj = self.User.get_User(fromuser)
                    client_obj = self.Client.get_Client(user_obj.uid)

                    if client_obj is not None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You are already logged in")
                        return None

                    db_query = f"SELECT account FROM {self.Config.TABLE_CLIENT} WHERE account = :account AND password = :password"
                    db_param = {'account': account, 'password': encrypted_password}
                    exec_query = self.Base.db_execute_query(
                        db_query,
                        db_param
                    )
                    result_query = exec_query.fetchone()
                    if result_query:
                        account = result_query[0]
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You are now logged in")
                        client = self.Loader.Definition.MClient(
                            uid=user_obj.uid, account=account, nickname=fromuser,
                            username=user_obj.username, realname=user_obj.realname, hostname=user_obj.hostname, umodes=user_obj.umodes, vhost=user_obj.vhost,
                            isWebirc=user_obj.isWebirc, isWebsocket=user_obj.isWebsocket, remote_ip=user_obj.remote_ip, score_connexion=user_obj.score_connexion,
                            geoip=user_obj.geoip, connexion_datetime=user_obj.connexion_datetime
                        )
                        self.Client.insert(client)
                        self.Protocol.send_svs_mode(nickname=fromuser, user_mode='+r')
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

                    user_obj = self.User.get_User(fromuser)
                    if user_obj is None:
                        self.Logs.error(f"The User [{fromuser}] is not available in the database")
                        return None

                    client_obj = self.Client.get_Client(user_obj.uid)

                    if client_obj is None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Nothing to logout. please login first")
                        return None

                    self.Protocol.send_svs_mode(nickname=fromuser, user_mode='-r')
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
                
                for com in self.Commands.get_ordered_commands():
                    print(com)

            case 'load':
                try:
                    # Load a module ex: .load mod_defender
                    mod_name = str(cmd[1])
                    self.load_module(fromuser, mod_name)
                except KeyError as ke:
                    self.Logs.error(f"Key Error: {ke} - list recieved: {cmd}")
                except Exception as err:
                    self.Logs.error(f"General Error: {ke} - list recieved: {cmd}")

            case 'unload':
                # unload mod_defender
                try:
                    module_name = str(cmd[1]).lower()                              # Le nom du module. exemple: mod_defender
                    self.unload_module(module_name)
                except Exception as err:
                    self.Logs.error(f"General Error: {err}")

            case 'reload':
                # reload mod_defender
                try:
                    module_name = str(cmd[1]).lower()   # ==> mod_defender
                    self.reload_module(from_user=fromuser, mod_name=module_name)
                except Exception as e:
                    self.Logs.error(f"Something went wrong with a module you want to reload: {e}")
                    self.Protocol.send_priv_msg(
                        nick_from=dnickname,
                        msg=f"Something went wrong with the module: {e}",
                        channel=dchanlog
                    )
                    self.Base.db_delete_module(module_name)

            case 'quit':
                try:

                    final_reason = ' '.join(cmd[1:])

                    self.hb_active = False
                    self.Base.shutdown()
                    self.Base.execute_periodic_action()

                    for chan_name in self.Channel.UID_CHANNEL_DB:
                        self.Protocol.send_mode_chan(chan_name.name, '-l')

                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Arrêt du service {dnickname}"
                    )
                    self.Protocol.squit(server_id=self.Config.SERVEUR_ID, server_link=self.Config.SERVEUR_LINK, reason=final_reason)
                    self.Logs.info(f'Arrêt du server {dnickname}')
                    self.Config.DEFENDER_RESTART = 0
                    self.signal = False

                except IndexError as ie:
                    self.Logs.error(f'{ie}')

            case 'restart':
                reason = []
                for i in range(1, len(cmd)):
                    reason.append(cmd[i])
                final_reason = ' '.join(reason)

                self.Protocol.send_notice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f"Redémarrage du service {dnickname}"
                )

                for class_name in self.loaded_classes:
                    self.loaded_classes[class_name].unload()

                self.User.UID_DB.clear()                # Clear User Object
                self.Channel.UID_CHANNEL_DB.clear()     # Clear Channel Object
                self.Base.delete_logger(self.Config.LOGGING_NAME)

                self.Protocol.squit(server_id=self.Config.SERVEUR_ID, server_link=self.Config.SERVEUR_LINK, reason=final_reason)
                self.Logs.info(f'Redémarrage du server {dnickname}')
                self.loaded_classes.clear()
                self.Config.DEFENDER_RESTART = 1                 # Set restart status to 1 saying that the service will restart
                self.Config.DEFENDER_INIT = 1                    # set init to 1 saying that the service will be re initiated

            case 'rehash':
                need_a_restart = ["SERVEUR_ID"]
                restart_flag = False
                Config_bakcup = self.Config.__dict__.copy()
                serveur_id = self.Config.SERVEUR_ID
                service_nickname = self.Config.SERVICE_NICKNAME
                hsid = self.Config.HSID
                ssl_version = self.Config.SSL_VERSION
                defender_init = self.Config.DEFENDER_INIT
                defender_restart = self.Config.DEFENDER_RESTART
                current_version = self.Config.CURRENT_VERSION
                latest_version = self.Config.LATEST_VERSION

                mods = ["core.definition", "core.config", "core.base", "core.classes.protocols.unreal6", "core.classes.protocol"]

                mod_unreal6 = sys.modules['core.classes.protocols.unreal6']
                mod_protocol = sys.modules['core.classes.protocol']
                mod_base = sys.modules['core.base']
                mod_config = sys.modules['core.classes.config']
                mod_definition = sys.modules['core.definition']

                importlib.reload(mod_definition)
                importlib.reload(mod_config)
                self.Config = self.Loader.ConfModule.Configuration().ConfigObject
                self.Config.HSID = hsid
                self.Config.DEFENDER_INIT = defender_init
                self.Config.DEFENDER_RESTART = defender_restart
                self.Config.SSL_VERSION = ssl_version
                self.Config.CURRENT_VERSION = current_version
                self.Config.LATEST_VERSION = latest_version
                importlib.reload(mod_base)

                conf_bkp_dict: dict = Config_bakcup
                config_dict: dict = self.Config.__dict__

                for key, value in conf_bkp_dict.items():
                    if config_dict[key] != value and key != 'COLORS':
                        self.Protocol.send_priv_msg(
                            nick_from=self.Config.SERVICE_NICKNAME,
                            msg=f'[{key}]: {value} ==> {config_dict[key]}', 
                            channel=self.Config.SERVICE_CHANLOG
                            )
                        if key in need_a_restart:
                            restart_flag = True

                if service_nickname != self.Config.SERVICE_NICKNAME:
                    self.Protocol.set_nick(self.Config.SERVICE_NICKNAME)

                if restart_flag:
                    self.Config.SERVEUR_ID = serveur_id
                    self.Protocol.send_priv_msg(nick_from=self.Config.SERVICE_NICKNAME, msg='You need to restart defender !', channel=self.Config.SERVICE_CHANLOG)

                self.Base.delete_logger(self.Config.LOGGING_NAME)
                self.Base = self.Loader.BaseModule.Base(self.Config, self.Settings)

                importlib.reload(mod_unreal6)
                importlib.reload(mod_protocol)

                self.Protocol = Protocol(self.Config.SERVEUR_PROTOCOL, self.ircObject).Protocol

                for mod in mods:
                    self.Protocol.send_priv_msg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f'> Module [{mod}] reloaded', 
                        channel=self.Config.SERVICE_CHANLOG
                        )
                for mod in self.Base.get_all_modules():
                    self.reload_module(fromuser, mod)

            case 'show_modules':

                self.Logs.debug(self.loaded_classes)
                all_modules  = self.Base.get_all_modules()
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
                            msg=f"{module} - {self.Config.COLORS.green}Loaded{self.Config.COLORS.nogc} by {loaded_user} on {loaded_datetime}"
                        )
                        loaded = False
                    else:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f"{module} - {self.Config.COLORS.red}Not Loaded{self.Config.COLORS.nogc}"
                        )

            case 'show_timers':

                if self.Base.running_timers:
                    for the_timer in self.Base.running_timers:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f">> {the_timer.getName()} - {the_timer.is_alive()}"
                        )
                else:
                    self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg="Aucun timers en cours d'execution"
                        )

            case 'show_threads':

                for thread in self.Base.running_threads:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f">> {thread.getName()} ({thread.is_alive()})"
                    )

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

            case 'show_users':
                count_users = len(self.User.UID_DB)
                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Total Connected Users: {count_users}")
                for db_user in self.User.UID_DB:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_user.uid} - isWebirc: {db_user.isWebirc} - isWebSocket: {db_user.isWebsocket} - Nickname: {db_user.nickname} - Connection: {db_user.connexion_datetime}"
                    )

            case 'show_clients':
                count_users = len(self.Client.CLIENT_DB)
                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Total Connected Clients: {count_users}")
                for db_client in self.Client.CLIENT_DB:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_client.uid} - isWebirc: {db_client.isWebirc} - isWebSocket: {db_client.isWebsocket} - Nickname: {db_client.nickname} - Account: {db_client.account} - Connection: {db_client.connexion_datetime}"
                    )

            case 'show_admins':

                for db_admin in self.Admin.UID_ADMIN_DB:
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_admin.uid} - Nickname: {db_admin.nickname} - Level: {db_admin.level} - Connection: {db_admin.connexion_datetime}"
                    )

            case 'show_configuration':

                config_dict = self.Config.__dict__

                for key, value in config_dict.items():
                    self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f'{key} = {value}'
                        )

            case 'uptime':
                uptime = self.get_defender_uptime()
                self.Protocol.send_notice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f"{uptime}"
                )

            case 'copyright':
                self.Protocol.send_notice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f"# Defender V.{self.Config.CURRENT_VERSION} Developped by adator® #"
                )

            case 'checkversion':

                self.Base.create_thread(
                    self.thread_check_for_new_version,
                    (fromuser, )
                )

            case 'raw':
                raw_command = ' '.join(cmd[1:])
                self.Protocol.send_raw(raw_command)

            case _:
                pass
