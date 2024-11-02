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
from typing import Union
from core.loader import Loader
from core.classes.protocol import Protocol

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

        # Get Settings.
        self.Settings = self.Base.Settings

        # Use User Instance
        self.User = self.Loader.User

        # Use Admin Instance
        self.Admin = self.Loader.Admin

        # Use Channel Instance
        self.Channel = self.Loader.Channel

        # Use Clones Instance
        self.Clone = self.Loader.Clone

        # Use Reputation Instance
        self.Reputation = self.Loader.Reputation
        
        self.autolimit_started: bool = False
        """This variable is to make sure the thread is not running"""

        self.first_score: int = 100

        self.loaded_classes:dict[str, 'Irc'] = {}           # Definir la variable qui contiendra la liste modules chargés

        self.IrcSocket:Union[socket.socket, SSLSocket] = None

        # Liste des commandes internes du bot
        self.commands_level = {
            0: ['help', 'auth', 'copyright', 'uptime', 'firstauth'],
            1: ['load','reload','unload', 'deauth', 'checkversion'],
            2: ['show_modules', 'show_timers', 'show_threads', 'show_channels', 'show_users', 'show_admins', 'show_configuration'],
            3: ['quit', 'restart','addaccess','editaccess', 'delaccess'],
            4: ['rehash']
        }

        # l'ensemble des commandes.
        self.commands = []
        for level, commands in self.commands_level.items():
            for command in self.commands_level[level]:
                self.commands.append(command)

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
            self.__create_socket()
            self.__connect_to_irc(ircInstance)
        except AssertionError as ae:
            self.Base.logs.critical(f'Assertion error: {ae}')

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
                self.Base.logs.info(f"Connexion en mode SSL : Version = {self.Config.SSL_VERSION}")
            else:
                soc.connect(connexion_information)
                self.IrcSocket:socket.socket = soc
                self.Base.logs.info("Connexion en mode normal")

            return None

        except ssl.SSLEOFError as soe:
            self.Base.logs.critical(f"SSLEOFError: {soe} - {soc.fileno()}")
        except ssl.SSLError as se:
            self.Base.logs.critical(f"SSLError: {se} - {soc.fileno()}")
        except OSError as oe:
            self.Base.logs.critical(f"OSError: {oe} - {soc.fileno()}")
            if 'connection refused' in str(oe).lower():
                sys.exit(oe)
            if soc.fileno() == -1:
                sys.exit(soc.fileno())

        except AttributeError as ae:
            self.Base.logs.critical(f"AttributeError: {ae} - {soc.fileno()}")

    def __ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.Base.logs.debug(f'SSLContext initiated with verified mode {ctx.verify_mode}')

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
                        self.Base.logs.debug('Restarting Defender ...')
                        self.IrcSocket.shutdown(socket.SHUT_RDWR)
                        self.IrcSocket.close()

                        while self.IrcSocket.fileno() != -1:
                            time.sleep(0.5)
                            self.Base.logs.warning('--> Waiting for socket to close ...')

                        # Reload configuration
                        self.Base.logs.debug('Reloading configuration')
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
                    self.Base.logs.error(f"SSLEOFError __connect_to_irc: {soe} - {data}")
                except ssl.SSLError as se:
                    self.Base.logs.error(f"SSLError __connect_to_irc: {se} - {data}")
                except OSError as oe:
                    self.Base.logs.error(f"SSLError __connect_to_irc: {oe} - {data}")
                except (socket.error, ConnectionResetError):
                    print("Connexion reset")

            self.IrcSocket.shutdown(socket.SHUT_RDWR)
            self.IrcSocket.close()
            self.Base.logs.info("--> Fermeture de Defender ...")
            sys.exit(0)

        except AssertionError as ae:
            self.Base.logs.error(f'AssertionError: {ae}')
        except ValueError as ve:
            self.Base.logs.error(f'ValueError: {ve}')
        except ssl.SSLEOFError as soe:
            self.Base.logs.error(f"SSLEOFError: {soe}")
        except AttributeError as atte:
            self.Base.logs.critical(f"AttributeError: {atte}")
        except Exception as e:
            self.Base.logs.critical(f"General Error: {e}")
            self.Base.logs.critical(traceback.format_exc())

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

    def send2socket(self, send_message:str, print_log: bool = True) -> None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            string (Str): contient la commande à envoyer au serveur.
        """
        try:
            with self.Base.lock:
                self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[0]))
                if print_log:
                    self.Base.logs.debug(f'< {send_message}')

        except UnicodeDecodeError:
            self.Base.logs.error(f'Decode Error try iso-8859-1 - message: {send_message}')
            self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[0],'replace'))
        except UnicodeEncodeError:
            self.Base.logs.error(f'Encode Error try iso-8859-1 - message: {send_message}')
            self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[0],'replace'))
        except AssertionError as ae:
            self.Base.logs.warning(f'Assertion Error {ae} - message: {send_message}')
        except ssl.SSLEOFError as soe:
            self.Base.logs.error(f"SSLEOFError: {soe} - {send_message}")
        except ssl.SSLError as se:
            self.Base.logs.error(f"SSLError: {se} - {send_message}")
        except OSError as oe:
            self.Base.logs.error(f"OSError: {oe} - {send_message}")

    # def sendNotice(self, msg:str, nickname: str) -> None:
    #     """Sending NOTICE by batches

    #     Args:
    #         msg (str): The message to send to the server
    #         nickname (str): The reciever Nickname
    #     """
    #     batch_size = self.Config.BATCH_SIZE
    #     service_nickname = self.Config.SERVICE_NICKNAME

    #     for i in range(0, len(str(msg)), batch_size):
    #         batch = str(msg)[i:i+batch_size]
    #         # self.send2socket(f":{service_nickname} NOTICE {nickname} :{batch}")

    # def sendPrivMsg(self, msg: str, channel: str = None, nickname: str = None):
    #     """Sending PRIVMSG to a channel or to a nickname by batches
    #     could be either channel or nickname not both together
    #     Args:
    #         msg (str): The message to send
    #         channel (str, optional): The receiver channel. Defaults to None.
    #         nickname (str, optional): The reciever nickname. Defaults to None.
    #     """
    #     batch_size = self.Config.BATCH_SIZE
    #     service_nickname = self.Config.SERVICE_NICKNAME

    #     if not channel is None:
    #         for i in range(0, len(str(msg)), batch_size):
    #             batch = str(msg)[i:i+batch_size]
    #             # self.send2socket(f":{service_nickname} PRIVMSG {channel} :{batch}")

    #     if not nickname is None:
    #         for i in range(0, len(str(msg)), batch_size):
    #             batch = str(msg)[i:i+batch_size]
    #             # self.send2socket(f":{service_nickname} PRIVMSG {nickname} :{batch}")

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
            self.Base.logs.error(f'UnicodeEncodeError: {ue}')
            self.Base.logs.error(response)

        except UnicodeDecodeError as ud:
            for data in responses:
                response = data.decode(self.CHARSET[1],'replace').split()
                self.cmd(response)
            self.Base.logs.error(f'UnicodeDecodeError: {ud}')
            self.Base.logs.error(response)

        except AssertionError as ae:
            self.Base.logs.error(f"Assertion error : {ae}")

    def unload(self) -> None:
        # This is only to reference the method
        return None

    ##############################################
    #             FIN CONNEXION IRC              #
    ##############################################

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
                self.Base.logs.error(f"La class [{class_name} n'existe pas !!]")
                return False

            class_instance = self.loaded_classes[class_name]

            t = threading.Timer(interval=time_to_wait, function=self.__create_tasks, args=(class_instance, method_name, method_args))
            t.start()

            self.Base.running_timers.append(t)

            self.Base.logs.debug(f"Timer ID : {str(t.ident)} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.Base.logs.error(f'Assertion Error -> {ae}')
        except TypeError as te:
            self.Base.logs.error(f"Type error -> {te}")

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

        self.Base.logs.debug(f'Function to execute : {str(self.Base.periodic_func)}')
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
            class_name = module_name.split('_')[1].capitalize()         # ==> Voice

            # print(self.loaded_classes)

            # Si le module est déja chargé
            if 'mods.' + module_name in sys.modules:
                self.Base.logs.info("Module déja chargé ...")
                self.Base.logs.info('module name = ' + module_name)
                if class_name in self.loaded_classes:
                    # Si le module existe dans la variable globale retourne False
                    self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Le module {module_name} est déja chargé ! si vous souhaiter le recharge tapez {self.Config.SERVICE_PREFIX}reload {module_name}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                    return False

                the_module = sys.modules['mods.' + module_name]
                importlib.reload(the_module)
                my_class = getattr(the_module, class_name, None)
                new_instance = my_class(self.ircObject)
                self.loaded_classes[class_name] = new_instance

                # Créer le module dans la base de données
                if not init:
                    self.Base.db_record_module(fromuser, module_name)

                self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} chargé",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                return False

            # Charger le module
            loaded_module = importlib.import_module(f"mods.{module_name}")

            my_class = getattr(loaded_module, class_name, None)                 # Récuperer le nom de classe
            create_instance_of_the_class = my_class(self.ircObject)             # Créer une nouvelle instance de la classe

            if not hasattr(create_instance_of_the_class, 'cmd'):
                self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} ne contient pas de méthode cmd",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                self.Base.logs.critical(f"The Module {module_name} has not been loaded because cmd method is not available")
                self.Base.db_delete_module(module_name)
                return False

            # Charger la nouvelle class dans la variable globale
            self.loaded_classes[class_name] = create_instance_of_the_class

            # Enregistrer le module dans la base de données
            if not init:
                self.Base.db_record_module(fromuser, module_name)
            self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} chargé",
                        channel=self.Config.SERVICE_CHANLOG
                    )

            # self.Base.logs.info(self.loaded_classes)
            self.Base.logs.info(f"Module {class_name} has been loaded")
            return True

        except ModuleNotFoundError as moduleNotFound:
            self.Base.logs.error(f"MODULE_NOT_FOUND: {moduleNotFound}")
            self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"[ {self.Config.COLORS.red}MODULE_NOT_FOUND{self.Config.COLORS.black} ]: {moduleNotFound}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
        except Exception as e:
            self.Base.logs.error(f"Something went wrong with a module you want to load : {e}")
            self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"[ {self.Config.COLORS.red}ERROR{self.Config.COLORS.black} ]: {e}",
                        channel=self.Config.SERVICE_CHANLOG
                    )

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
                for level, command in self.loaded_classes[class_name].commands_level.items():
                    # Supprimer la commande de la variable commands
                    for c in self.loaded_classes[class_name].commands_level[level]:
                        self.commands.remove(c)
                        self.commands_level[level].remove(c)

                del self.loaded_classes[class_name]

                # Supprimer le module de la base de données
                self.Base.db_delete_module(module_name)

                self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} supprimé",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                return True

        except Exception as err:
            self.Base.logs.error(f"General Error: {err}")
            return False

    def reload_module(self, from_user: str, mod_name: str) -> bool:
        try:
            module_name = mod_name.lower()                       # ==> mod_defender
            class_name = module_name.split('_')[1].capitalize()  # ==> Defender

            if 'mods.' + module_name in sys.modules:
                self.Base.logs.info('Unload the module ...')
                self.loaded_classes[class_name].unload()
                self.Base.logs.info('Module Already Loaded ... reloading the module ...')
                the_module = sys.modules['mods.' + module_name]
                importlib.reload(the_module)

                # Supprimer la class déja instancier
                if class_name in self.loaded_classes:
                # Supprimer les commandes déclarer dans la classe
                    for level, command in self.loaded_classes[class_name].commands_level.items():
                        # Supprimer la commande de la variable commands
                        for c in self.loaded_classes[class_name].commands_level[level]:
                            self.commands.remove(c)
                            self.commands_level[level].remove(c)

                    del self.loaded_classes[class_name]

                my_class = getattr(the_module, class_name, None)
                new_instance = my_class(self.ircObject)
                self.loaded_classes[class_name] = new_instance

                self.Base.db_update_module(from_user, mod_name)
                self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} rechargé",
                        channel=self.Config.SERVICE_CHANLOG
                    )
                return False
            else:
                self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Module {module_name} n'est pas chargé !",
                        channel=self.Config.SERVICE_CHANLOG
                    )

        except TypeError as te:
            self.Base.logs.error(f"A TypeError raised: {te}")
            self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"A TypeError raised: {te}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
        except AttributeError as ae:
            self.Base.logs.error(f"Missing Attribute: {ae}")
            self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Missing Attribute: {ae}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
        except KeyError as ke:
            self.Base.logs.error(f"Key Error: {ke}")
            self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Key Error: {ke}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)
        except Exception as e:
            self.Base.logs.error(f"Something went wrong with a module you want to reload: {e}")
            self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f"Something went wrong with the module: {e}",
                        channel=self.Config.SERVICE_CHANLOG
                    )
            self.Base.db_delete_module(module_name)

    def insert_db_admin(self, uid:str, level:int) -> None:

        if self.User.get_User(uid) is None:
            return None

        getUser = self.User.get_User_AsDict(uid)

        level = int(level)

        self.Admin.insert(
            self.Loader.Definition.MAdmin(
                **getUser,
                level=level
            )
        )

        return None

    def delete_db_admin(self, uid:str) -> None:

        if self.Admin.get_Admin(uid) is None:
            return None

        if not self.Admin.delete(uid):
            self.Base.logs.critical(f'UID: {uid} was not deleted')

        return None

    def create_defender_user(self, nickname:str, level: int, password:str) -> str:

        get_user = self.User.get_User(nickname)
        if get_user is None:
            response = f'This nickname {nickname} does not exist, it is not possible to create this user'
            self.Base.logs.warning(response)
            return response

        nickname = get_user.nickname
        response = ''

        if level > 4:
            response = "Impossible d'ajouter un niveau > 4"
            self.Base.logs.warning(response)
            return response

        hostname = get_user.hostname
        vhost = get_user.vhost
        spassword = self.Base.crypt_password(password)

        mes_donnees = {'admin': nickname}
        query_search_user = f"SELECT id FROM {self.Config.TABLE_ADMIN} WHERE user=:admin"
        r = self.Base.db_execute_query(query_search_user, mes_donnees)
        exist_user = r.fetchone()

        # On verifie si le user exist dans la base
        if not exist_user:
            mes_donnees = {'datetime': self.Base.get_datetime(), 'user': nickname, 'password': spassword, 'hostname': hostname, 'vhost': vhost, 'level': level}
            self.Base.db_execute_query(f'''INSERT INTO {self.Config.TABLE_ADMIN} 
                    (createdOn, user, password, hostname, vhost, level) VALUES
                    (:datetime, :user, :password, :hostname, :vhost, :level)
                    ''', mes_donnees)
            response = f"{nickname} ajouté en tant qu'administrateur de niveau {level}"
            self.Protocol.sendNotice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=nickname, msg=response)
            self.Base.logs.info(response)
            return response
        else:
            response = f'{nickname} Existe déjà dans les users enregistrés'
            self.Protocol.sendNotice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=nickname, msg=response)
            self.Base.logs.info(response)
            return response

    def is_cmd_allowed(self, nickname:str, cmd:str) -> bool:

        # Vérifier si le user est identifié et si il a les droits
        is_command_allowed = False
        uid = self.User.get_uid(nickname)
        get_admin = self.Admin.get_Admin(uid)

        if not get_admin is None:
            admin_level = get_admin.level

            for ref_level, ref_commands in self.commands_level.items():
                # print(f"LevelNo: {ref_level} - {ref_commands} - {admin_level}")
                if ref_level <= int(admin_level):
                    # print(f"LevelNo: {ref_level} - {ref_commands}")
                    if cmd in ref_commands:
                        is_command_allowed = True
        else:
            for ref_level, ref_commands in self.commands_level.items():
                if ref_level == 0:
                    # print(f"LevelNo: {ref_level} - {ref_commands}")
                    if cmd in ref_commands:
                        is_command_allowed = True

        return is_command_allowed

    def debug(self, debug_msg:str) -> None:

        # if self.Config.DEBUG == 1:
        #     if type(debug_msg) == list:
        #         if debug_msg[0] != 'PING':
        #             print(f"[{self.Base.get_datetime()}] - {debug_msg}")
        #     else:
        #         
        print(f"[{self.Base.get_datetime()}] - {debug_msg}")

        return None

    def logs(self, log_msg:str) -> None:

        mes_donnees = {'datetime': self.Base.get_datetime(), 'server_msg': log_msg}
        self.Base.db_execute_query('INSERT INTO sys_logs (datetime, server_msg) VALUES (:datetime, :server_msg)', mes_donnees)

        return None

    def thread_check_for_new_version(self, fromuser: str) -> None:
        dnickname = self.Config.SERVICE_NICKNAME

        if self.Base.check_for_new_version(True):
            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" New Version available : {self.Config.CURRENT_VERSION} >>> {self.Config.LATEST_VERSION}")
            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=" Please run (git pull origin main) in the current folder")
        else:
            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=" You have the latest version of defender")

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
                self.Base.logs.warning(f'Size ({str(len(original_response))}) - {original_response}')
                return False

            if len(original_response) == 7:
                if original_response[2] == 'PRIVMSG' and original_response[4] == ':auth':
                    data_copy = original_response.copy()
                    data_copy[6] = '**********'
                    self.Base.logs.debug(f">> {data_copy}")
                else:
                    self.Base.logs.debug(f">> {original_response}")
            else:
                self.Base.logs.debug(f">> {original_response}")

            match original_response[0]:

                case 'PING':
                    # Sending PONG response to the serveur
                    self.Protocol.on_server_ping(original_response)
                    return None

                case 'PROTOCTL':
                    #['PROTOCTL', 'CHANMODES=beI,fkL,lFH,cdimnprstzCDGKMNOPQRSTVZ', 'USERMODES=diopqrstwxzBDGHIRSTWZ', 'BOOTED=1702138935', 
                    # 'PREFIX=(qaohv)~&@%+', 'SID=001', 'MLOCK', 'TS=1703793941', 'EXTSWHOIS']

                    # GET SERVER ID HOST
                    if len(original_response) > 5:
                        if '=' in original_response[5]:
                            serveur_hosting_id = str(original_response[5]).split('=')
                            self.HSID = serveur_hosting_id[1]
                            self.Config.HSID = serveur_hosting_id[1]
                            return False

                case _:
                    pass

            if len(original_response) < 2:
                return False

            match original_response[1]:

                case 'SLOG':
                    # self.Base.scan_ports(cmd[7])
                    # if self.Config.ABUSEIPDB == 1:
                    #     self.Base.create_thread(self.abuseipdb_scan, (cmd[7], ))
                    pass

                case 'UMODE2':
                    # [':adator_', 'UMODE2', '-i']
                    self.Protocol.on_umode2(serverMsg=original_response)

                case 'SQUIT':
                    # ['@msgid=QOEolbRxdhpVW5c8qLkbAU;time=2024-09-21T17:33:16.547Z', 'SQUIT', 'defender.deb.biz.st', ':Connection', 'closed']
                    server_hostname = interm_response[1]
                    uid_to_delete = ''
                    for s_user in self.User.UID_DB:
                        if s_user.hostname == server_hostname and 'S' in s_user.umodes:
                            uid_to_delete = s_user.uid

                    self.User.delete(uid_to_delete)
                    self.Channel.delete_user_from_all_channel(uid_to_delete)

                case 'REPUTATION':
                    # :001 REPUTATION 127.0.0.1 118
                    try:
                        self.first_connexion_ip = original_response[2]

                        self.first_score = 0
                        if str(original_response[3]).find('*') != -1:
                            # If * available, it means that an ircop changed the repurtation score
                            # means also that the user exist will try to update all users with same IP
                            self.first_score = int(str(original_response[3]).replace('*',''))
                            for user in self.User.UID_DB:
                                if user.remote_ip == self.first_connexion_ip:
                                    user.score_connexion = self.first_score
                        else:
                            self.first_score = int(original_response[3])

                        # Possibilité de déclancher les bans a ce niveau.
                    except IndexError as ie:
                        self.Base.logs.error(f'{ie}')
                    except ValueError as ve:
                        self.first_score = 0
                        self.Base.logs.error(f'Impossible to convert first_score: {ve}')

                case '320':
                    #:irc.deb.biz.st 320 PyDefender IRCParis07 :is in security-groups: known-users,webirc-users,tls-and-known-users,tls-users
                    pass

                case '318':
                    #:irc.deb.biz.st 318 PyDefender IRCParis93 :End of /WHOIS list.
                    pass

                case 'MD':
                    # [':001', 'MD', 'client', '001CG0TG7', 'webirc', ':2']
                    pass

                case 'EOS':

                    hsid = str(original_response[0]).replace(':','')
                    if hsid == self.Config.HSID:
                        if self.Config.DEFENDER_INIT == 1:
                            current_version = self.Config.CURRENT_VERSION
                            latest_version = self.Config.LATEST_VERSION
                            if self.Base.check_for_new_version(False):
                                version = f'{current_version} >>> {latest_version}'
                            else:
                                version = f'{current_version}'

                            print(f"################### DEFENDER ###################")
                            print(f"#               SERVICE CONNECTE                ")
                            print(f"# SERVEUR  :    {self.Config.SERVEUR_IP}        ")
                            print(f"# PORT     :    {self.Config.SERVEUR_PORT}      ")
                            print(f"# SSL      :    {self.Config.SERVEUR_SSL}       ")
                            print(f"# SSL VER  :    {self.Config.SSL_VERSION}       ")
                            print(f"# NICKNAME :    {self.Config.SERVICE_NICKNAME}  ")
                            print(f"# CHANNEL  :    {self.Config.SERVICE_CHANLOG}   ")
                            print(f"# VERSION  :    {version}                       ")
                            print(f"################################################")

                            self.Base.logs.info(f"################### DEFENDER ###################")
                            self.Base.logs.info(f"#               SERVICE CONNECTE                ")
                            self.Base.logs.info(f"# SERVEUR  :    {self.Config.SERVEUR_IP}        ")
                            self.Base.logs.info(f"# PORT     :    {self.Config.SERVEUR_PORT}      ")
                            self.Base.logs.info(f"# SSL      :    {self.Config.SERVEUR_SSL}       ")
                            self.Base.logs.info(f"# SSL VER  :    {self.Config.SSL_VERSION}       ")
                            self.Base.logs.info(f"# NICKNAME :    {self.Config.SERVICE_NICKNAME}  ")
                            self.Base.logs.info(f"# CHANNEL  :    {self.Config.SERVICE_CHANLOG}   ")
                            self.Base.logs.info(f"# VERSION  :    {version}                       ")
                            self.Base.logs.info(f"################################################")

                            if self.Base.check_for_new_version(False):
                                self.Protocol.sendPrivMsg(
                                    nick_from=self.Config.SERVICE_NICKNAME,
                                    msg=f" New Version available {version}",
                                    channel=self.Config.SERVICE_CHANLOG
                                )

                        # Initialisation terminé aprés le premier PING
                        self.Protocol.sendPrivMsg(
                            nick_from=self.Config.SERVICE_NICKNAME,
                            msg=f"[{self.Config.COLORS.green}INFORMATION{self.Config.COLORS.nogc}] >> Defender is ready",
                            channel=self.Config.SERVICE_CHANLOG
                        )
                        self.Config.DEFENDER_INIT = 0

                        # Send EOF to other modules
                        for classe_name, classe_object in self.loaded_classes.items():
                            classe_object.cmd(original_response)

                        # Stop here When EOS
                        return None

                case _:
                    pass

            if len(original_response) < 3:
                return False

            match original_response[2]:

                case 'VERSION':

                    self.Protocol.on_version_msg(original_response)

                case 'QUIT':

                    self.Protocol.on_quit(serverMsg=original_response)

                case 'PONG':
                    # ['@msgid=aTNJhp17kcPboF5diQqkUL;time=2023-12-28T20:35:58.411Z', ':irc.deb.biz.st', 'PONG', 'irc.deb.biz.st', ':Dev-PyDefender']
                    self.Base.execute_periodic_action()

                case 'NICK':

                    self.Protocol.on_nick(original_response)

                case 'MODE':
                    #['@msgid=d0ySx56Yd0nc35oHts2SkC-/J9mVUA1hfM6+Z4494xWUg;time=2024-08-09T12:45:36.651Z', 
                    # ':001', 'MODE', '#a', '+nt', '1723207536']
                    # [':adator_', 'UMODE2', '-i']
                    pass

                case 'SJOIN':

                    self.Protocol.on_sjoin(serverMsg=original_response)

                case 'PART':

                    self.Protocol.on_part(serverMsg=original_response)
 
                case 'UID':
                    try:
                        self.Protocol.on_uid(serverMsg=original_response)

                        for classe_name, classe_object in self.loaded_classes.items():
                            classe_object.cmd(original_response)

                    except Exception as err:
                        self.Base.logs.error(f'General Error: {err}')

                case 'PRIVMSG':
                    try:
                        # Supprimer la premiere valeur
                        cmd = interm_response.copy()

                        get_uid_or_nickname = str(cmd[0].replace(':',''))
                        user_trigger = self.User.get_nickname(get_uid_or_nickname)
                        dnickname = self.Config.SERVICE_NICKNAME

                        if len(cmd) == 6:
                            if cmd[1] == 'PRIVMSG' and str(cmd[3]).replace(self.Config.SERVICE_PREFIX,'') == ':auth':
                                cmd_copy = cmd.copy()
                                cmd_copy[5] = '**********'
                                self.Base.logs.info(f'>> {cmd_copy}')
                            else:
                                self.Base.logs.info(f'>> {cmd}')
                        else:
                            self.Base.logs.info(f'>> {cmd}')

                        pattern = fr'(:\{self.Config.SERVICE_PREFIX})(.*)$'
                        hcmds = re.search(pattern, ' '.join(cmd)) # va matcher avec tout les caractéres aprés le .

                        if hcmds: # Commande qui commencent par le point
                            liste_des_commandes = list(hcmds.groups())
                            convert_to_string = ' '.join(liste_des_commandes)
                            arg = convert_to_string.split()
                            arg.remove(f':{self.Config.SERVICE_PREFIX}')
                            if not arg[0].lower() in self.commands:
                                self.Base.logs.debug(f"This command {arg[0]} is not available")
                                self.Protocol.sendNotice(
                                    nick_from=self.Config.SERVICE_NICKNAME,
                                    nick_to=user_trigger,
                                    msg=f"This command [{self.Config.COLORS.bold}{arg[0]}{self.Config.COLORS.bold}] is not available"
                                )
                                return None

                            cmd_to_send = convert_to_string.replace(':','')
                            self.Base.log_cmd(user_trigger, cmd_to_send)

                            fromchannel = str(cmd[2]).lower() if self.Channel.Is_Channel(cmd[2]) else None
                            self._hcmds(user_trigger, fromchannel, arg, cmd)

                        if cmd[2] == self.Config.SERVICE_ID:
                            pattern = fr'^:.*?:(.*)$'

                            hcmds = re.search(pattern, ' '.join(cmd))

                            if hcmds: # par /msg defender [commande]
                                liste_des_commandes = list(hcmds.groups())
                                convert_to_string = ' '.join(liste_des_commandes)
                                arg = convert_to_string.split()

                                # Réponse a un CTCP VERSION
                                if arg[0] == '\x01VERSION\x01':
                                    self.Protocol.on_version(original_response)
                                    return False

                                # Réponse a un TIME
                                if arg[0] == '\x01TIME\x01':
                                    self.Protocol.on_time(original_response)
                                    return False

                                # Réponse a un PING
                                if arg[0] == '\x01PING':
                                    self.Protocol.on_ping(original_response)
                                    return False

                                if not arg[0].lower() in self.commands:
                                    self.Base.logs.debug(f"This command {arg[0]} sent by {user_trigger} is not available")
                                    return False

                                cmd_to_send = convert_to_string.replace(':','')
                                self.Base.log_cmd(user_trigger, cmd_to_send)

                                fromchannel = None
                                if len(arg) >= 2:
                                    fromchannel = str(arg[1]).lower() if self.Channel.Is_Channel(arg[1]) else None

                                self._hcmds(user_trigger, fromchannel, arg, cmd)

                    except IndexError as io:
                        self.Base.logs.error(f'{io}')

                case _:
                    pass

            if original_response[2] != 'UID':
                # Envoyer la commande aux classes dynamiquement chargées
                for classe_name, classe_object in self.loaded_classes.items():
                    classe_object.cmd(original_response)

        except IndexError as ie:
            self.Base.logs.error(f"{ie} / {original_response} / length {str(len(original_response))}")
        except Exception as err:
            self.Base.logs.error(f"General Error: {err}")
            self.Base.logs.error(f"General Error: {traceback.format_exc()}")

    def _hcmds(self, user: str, channel: Union[str, None], cmd: list, fullcmd: list = []) -> None:
        """_summary_

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
                classe_object._hcmds(user, channel, cmd, fullcmd)

        match command:

            case 'notallowed':
                try:
                    current_command = cmd[0]
                    self.Protocol.sendPrivMsg(
                        msg=f'[ {self.Config.COLORS.red}{current_command}{self.Config.COLORS.black} ] - Accès Refusé à {self.User.get_nickname(fromuser)}',
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f'Accès Refusé'
                        )

                except IndexError as ie:
                    self.Base.logs.error(f'{ie}')

            case 'deauth':

                current_command = cmd[0]
                uid_to_deauth = self.User.get_uid(fromuser)
                self.delete_db_admin(uid_to_deauth)

                self.Protocol.sendPrivMsg(
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
                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"You can't use this command anymore ! Please use [{self.Config.SERVICE_PREFIX}auth] instead"
                        )
                    return False

                if current_nickname is None:
                    self.Base.logs.critical(f"This nickname [{fromuser}] don't exist")
                    return False

                # Credentials sent from the user
                cmd_owner = str(cmd[1])
                cmd_password = str(cmd[2])

                # Credentials coming from the Configuration
                config_owner    = self.Config.OWNER
                config_password = self.Config.PASSWORD

                if current_nickname != cmd_owner:
                    self.Base.logs.critical(f"The current nickname [{fromuser}] is different than the nickname sent [{cmd_owner}] !")
                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"The current nickname [{fromuser}] is different than the nickname sent [{cmd_owner}] !"
                        )
                    return False

                if current_nickname != config_owner:
                    self.Base.logs.critical(f"The current nickname [{current_nickname}] is different than the configuration owner [{config_owner}] !")
                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"The current nickname [{current_nickname}] is different than the configuration owner [{config_owner}] !"
                        )
                    return False

                if cmd_owner != config_owner:
                    self.Base.logs.critical(f"The nickname sent [{cmd_owner}] is different than the configuration owner [{config_owner}] !")
                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"The nickname sent [{cmd_owner}] is different than the configuration owner [{config_owner}] !"
                        )
                    return False

                if cmd_owner == config_owner and cmd_password == config_password:
                    self.Base.db_create_first_admin()
                    self.insert_db_admin(current_uid, 5)
                    self.Protocol.sendPrivMsg(
                        msg=f"[ {self.Config.COLORS.green}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} est désormais connecté a {dnickname}",
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Connexion a {dnickname} réussie!"
                        )
                else:
                    self.Protocol.sendPrivMsg(
                        msg=f"[ {self.Config.COLORS.red}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} a tapé un mauvais mot de pass",
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Mot de passe incorrecte"
                        )

            case 'auth':
                # ['auth', 'adator', 'password']
                current_command = cmd[0]
                user_to_log = self.User.get_nickname(cmd[1])
                password = cmd[2]

                if fromuser != user_to_log:
                    # If the current nickname is different from the nickname you want to log in with
                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"Your current nickname is different from the nickname you want to log in with")
                    return False

                if not user_to_log is None:
                    mes_donnees = {'user': user_to_log, 'password': self.Base.crypt_password(password)}
                    query = f"SELECT id, level FROM {self.Config.TABLE_ADMIN} WHERE user = :user AND password = :password"
                    result = self.Base.db_execute_query(query, mes_donnees)
                    user_from_db = result.fetchone()

                    if not user_from_db is None:
                        uid_user = self.User.get_uid(user_to_log)
                        self.insert_db_admin(uid_user, user_from_db[1])
                        self.Protocol.sendPrivMsg(nick_from=dnickname, 
                                                  msg=f"[ {self.Config.COLORS.green}{str(current_command).upper()} ]{self.Config.COLORS.nogc} - {self.User.get_nickname(fromuser)} est désormais connecté a {dnickname}",
                                                  channel=dchanlog)
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"Connexion a {dnickname} réussie!")
                    else:
                        self.Protocol.sendPrivMsg(nick_from=dnickname, 
                                                  msg=f"[ {self.Config.COLORS.red}{str(current_command).upper()} ]{self.Config.COLORS.nogc} - {self.User.get_nickname(fromuser)} a tapé un mauvais mot de pass",
                                                  channel=dchanlog)
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"Mot de passe incorrecte")

                else:
                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"L'utilisateur {user_to_log} n'existe pas")

            case 'addaccess':
                try:
                    # .addaccess adator 5 password
                    if len(cmd) < 4:
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"Right command : /msg {dnickname} addaccess [nickname] [level] [password]")
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"level: from 1 to 4")

                    newnickname = cmd[1]
                    newlevel = self.Base.int_if_possible(cmd[2])
                    password = cmd[3]

                    response = self.create_defender_user(newnickname, newlevel, password)

                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"{response}")
                    self.Base.logs.info(response)

                except IndexError as ie:
                    self.Base.logs.error(f'_hcmd addaccess: {ie}')
                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} addaccess [nickname] [level] [password]")
                except TypeError as te:
                    self.Base.logs.error(f'_hcmd addaccess: out of index : {te}')
                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} addaccess [nickname] [level] [password]")

            case 'editaccess':
                # .editaccess [USER] [PASSWORD] [LEVEL]
                try:
                    user_to_edit = cmd[1]
                    user_new_level = int(cmd[3])
                    user_password = self.Base.crypt_password(cmd[2])

                    if len(cmd) < 4 or len(cmd) > 4:
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"{self.Config.SERVICE_PREFIX}editaccess [USER] [NEWPASSWORD] [NEWLEVEL]")
                        return None

                    get_admin = self.Admin.get_Admin(fromuser)
                    if get_admin is None:
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" This user {fromuser} has no Admin access")
                        return None

                    current_user = self.User.get_nickname(fromuser)
                    current_uid = self.User.get_uid(fromuser)
                    current_user_level = get_admin.level

                    if user_new_level > 5:
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" Maximum authorized level is 5")
                        return None

                    # Rechercher le user dans la base de données.
                    mes_donnees = {'user': user_to_edit}
                    query = f"SELECT user, level FROM {self.Config.TABLE_ADMIN} WHERE user = :user"
                    result = self.Base.db_execute_query(query, mes_donnees)

                    isUserExist = result.fetchone()
                    if not isUserExist is None:

                        if current_user_level < int(isUserExist[1]):
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" You are not allowed to edit this access")
                            return None
                        
                        if current_user_level == int(isUserExist[1]) and current_user != user_to_edit:
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" You can't edit access of a user with same level")
                            return None

                        # Le user existe dans la base de données
                        data_to_update = {'user': user_to_edit, 'password': user_password, 'level': user_new_level}
                        sql_update = f"UPDATE {self.Config.TABLE_ADMIN} SET level = :level, password = :password WHERE user = :user"
                        exec_query = self.Base.db_execute_query(sql_update, data_to_update)
                        if exec_query.rowcount > 0:
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" User {user_to_edit} has been modified with level {str(user_new_level)}")
                            self.Admin.update_level(user_to_edit, user_new_level)
                        else:
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" Impossible de modifier l'utilisateur {str(user_new_level)}")

                except TypeError as te:
                    self.Base.logs.error(f"Type error : {te}")
                except ValueError as ve:
                    self.Base.logs.error(f"Value Error : {ve}")
                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" {self.Config.SERVICE_PREFIX}editaccess [USER] [NEWPASSWORD] [NEWLEVEL]")

            case 'delaccess':
                # .delaccess [USER] [CONFIRMUSER]
                user_to_del = cmd[1]
                user_confirmation = cmd[2]

                if user_to_del != user_confirmation:
                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer")
                    self.Base.logs.warning(f':{dnickname} NOTICE {fromuser} : Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer')
                    return None

                if len(cmd) < 3:
                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"{self.Config.SERVICE_PREFIX}delaccess [USER] [CONFIRMUSER]")
                    return None

                get_admin = self.Admin.get_Admin(fromuser)

                if get_admin is None:
                    self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"This user {fromuser} has no admin access")
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
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"You are not allowed to delete this access")
                        self.Base.logs.warning(f':{dnickname} NOTICE {fromuser} : You are not allowed to delete this access')
                        return None

                    data_to_delete = {'user': user_to_del}
                    sql_delete = f"DELETE FROM {self.Config.TABLE_ADMIN} WHERE user = :user"
                    exec_query = self.Base.db_execute_query(sql_delete, data_to_delete)
                    if exec_query.rowcount > 0:
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"User {user_to_del} has been deleted !")
                        self.Admin.delete(user_to_del)
                    else:
                        self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"Impossible de supprimer l'utilisateur.")
                        self.Base.logs.warning(f":{dnickname} NOTICE {fromuser} : Impossible de supprimer l'utilisateur.")

            case 'help':

                count_level_definition = 0
                get_admin = self.Admin.get_Admin(uid)
                if not get_admin is None:
                    user_level = get_admin.level
                else:
                    user_level = 0

                self.Protocol.sendNotice(nick_from=dnickname,nick_to=fromuser,msg=f" ***************** LISTE DES COMMANDES *****************")
                self.Protocol.sendNotice(nick_from=dnickname,nick_to=fromuser,msg=f" ")
                for levDef in self.commands_level:

                    if int(user_level) >= int(count_level_definition):

                        self.Protocol.sendNotice(nick_from=dnickname,nick_to=fromuser,
                                                 msg=f" ***************** {self.Config.COLORS.nogc}[ {self.Config.COLORS.green}LEVEL {str(levDef)} {self.Config.COLORS.nogc}] *****************"
                                                 )

                        batch = 7
                        for i in range(0, len(self.commands_level[count_level_definition]), batch):
                            groupe = self.commands_level[count_level_definition][i:i + batch]  # Extraire le groupe
                            batch_commands = ' | '.join(groupe)
                            self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f" {batch_commands}")

                        self.Protocol.sendNotice(nick_from=dnickname,nick_to=fromuser,msg=f" ")

                    count_level_definition += 1

                self.Protocol.sendNotice(nick_from=dnickname,nick_to=fromuser,msg=f" ***************** FIN DES COMMANDES *****************")

            case 'load':
                try:
                    # Load a module ex: .load mod_defender
                    mod_name = str(cmd[1])
                    self.load_module(fromuser, mod_name)
                except KeyError as ke:
                    self.Base.logs.error(f"Key Error: {ke} - list recieved: {cmd}")
                except Exception as err:
                    self.Base.logs.error(f"General Error: {ke} - list recieved: {cmd}")

            case 'unload':
                # unload mod_defender
                try:
                    module_name = str(cmd[1]).lower()                              # Le nom du module. exemple: mod_defender
                    self.unload_module(module_name)
                except Exception as err:
                    self.Base.logs.error(f"General Error: {err}")

            case 'reload':
                # reload mod_defender
                try:
                    module_name = str(cmd[1]).lower()   # ==> mod_defender
                    self.reload_module(from_user=fromuser, mod_name=module_name)
                except Exception as e:
                    self.Base.logs.error(f"Something went wrong with a module you want to reload: {e}")
                    self.Protocol.sendPrivMsg(
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

                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Arrêt du service {dnickname}"
                    )
                    self.Protocol.squit(server_id=self.Config.SERVEUR_ID, server_link=self.Config.SERVEUR_LINK, reason=final_reason)
                    self.Base.logs.info(f'Arrêt du server {dnickname}')
                    self.Config.DEFENDER_RESTART = 0
                    self.signal = False

                except IndexError as ie:
                    self.Base.logs.error(f'{ie}')

            case 'restart':
                reason = []
                for i in range(1, len(cmd)):
                    reason.append(cmd[i])
                final_reason = ' '.join(reason)

                self.Protocol.sendNotice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f"Redémarrage du service {dnickname}"
                )

                for class_name in self.loaded_classes:
                    self.loaded_classes[class_name].unload()

                self.User.UID_DB.clear()                # Clear User Object
                self.Channel.UID_CHANNEL_DB.clear()     # Clear Channel Object

                self.Protocol.squit(server_id=self.Config.SERVEUR_ID, server_link=self.Config.SERVEUR_LINK, reason=final_reason)
                self.Base.logs.info(f'Redémarrage du server {dnickname}')
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

                mods = ["core.config", "core.base", "core.classes.protocols.unreal6", "core.classes.protocol"]

                mod_unreal6 = sys.modules['core.classes.protocols.unreal6']
                mod_protocol = sys.modules['core.classes.protocol']
                mod_base = sys.modules['core.base']
                mod_config = sys.modules['core.classes.config']

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
                    if config_dict[key] != value:
                        self.Protocol.sendPrivMsg(
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
                    self.Protocol.sendPrivMsg(nick_from=self.Config.SERVICE_NICKNAME, msg='You need to restart defender !', channel=self.Config.SERVICE_CHANLOG)

                self.Base = self.Loader.BaseModule.Base(self.Config, self.Settings)

                importlib.reload(mod_unreal6)
                importlib.reload(mod_protocol)

                self.Protocol = Protocol(self.Config.SERVEUR_PROTOCOL, self.ircObject).Protocol

                for mod in mods:
                    self.Protocol.sendPrivMsg(
                        nick_from=self.Config.SERVICE_NICKNAME,
                        msg=f'> Module [{mod}] reloaded', 
                        channel=self.Config.SERVICE_CHANLOG
                        )

                self.reload_module(fromuser, 'mod_command')

            case 'show_modules':

                self.Base.logs.debug(self.loaded_classes)
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
                        self.Protocol.sendNotice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f"{module} - {self.Config.COLORS.green}Loaded{self.Config.COLORS.nogc} by {loaded_user} on {loaded_datetime}"
                        )
                        loaded = False
                    else:
                        self.Protocol.sendNotice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f"{module} - {self.Config.COLORS.red}Not Loaded{self.Config.COLORS.nogc}"
                        )

            case 'show_timers':

                if self.Base.running_timers:
                    for the_timer in self.Base.running_timers:
                        self.Protocol.sendNotice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f">> {the_timer.getName()} - {the_timer.is_alive()}"
                        )
                else:
                    self.Protocol.sendNotice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg="Aucun timers en cours d'execution"
                        )

            case 'show_threads':

                for thread in self.Base.running_threads:
                    self.Protocol.sendNotice(
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

                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Channel: {chan.name} - Users: {list_nicknames}"
                    )

            case 'show_users':
                count_users = len(self.User.UID_DB)
                self.Protocol.sendNotice(nick_from=dnickname, nick_to=fromuser, msg=f"Total Connected Users: {count_users}")
                for db_user in self.User.UID_DB:
                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_user.uid} - isWebirc: {db_user.isWebirc} - isWebSocket: {db_user.isWebsocket} - Nickname: {db_user.nickname} - Connection: {db_user.connexion_datetime}"
                    )

            case 'show_admins':

                for db_admin in self.Admin.UID_ADMIN_DB:
                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_admin.uid} - Nickname: {db_admin.nickname} - Level: {db_admin.level} - Connection: {db_admin.connexion_datetime}"
                    )

            case 'show_configuration':

                config_dict = self.Config.__dict__

                for key, value in config_dict.items():
                    self.Protocol.sendNotice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f'{key} > {value}'
                        )

            case 'uptime':
                uptime = self.get_defender_uptime()
                self.Protocol.sendNotice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f"{uptime}"
                )

            case 'copyright':
                self.Protocol.sendNotice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f"# Defender V.{self.Config.CURRENT_VERSION} Developped by adator® #"
                )

            case 'checkversion':

                self.Base.create_thread(
                    self.thread_check_for_new_version,
                    (fromuser, )
                )

            case _:
                pass
