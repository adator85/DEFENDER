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
from core.loadConf import Config
from core.base import Base
from core.Model import User, Admin, Channel, Clones

class Irc:

    def __init__(self) -> 'Irc':

        self.defender_connexion_datetime = datetime.now()   # Date et heure de la premiere connexion de Defender
        self.first_score: int = 100
        self.loaded_classes:dict[str, 'Irc'] = {}           # Definir la variable qui contiendra la liste modules chargés
        self.beat = 30                                      # Lancer toutes les 30 secondes des actions de nettoyages
        self.hb_active = True                               # Heartbeat active
        self.HSID = ''                                      # ID du serveur qui accueil le service ( Host Serveur Id )
        self.IrcSocket:Union[socket.socket, SSLSocket] = None

        self.INIT = 1                                       # Variable d'intialisation | 1 -> indique si le programme est en cours d'initialisation
        self.RESTART = 0                                    # Variable pour le redemarrage du bot | 0 -> indique que le programme n'es pas en cours de redemarrage
        self.CHARSET = ['utf-8', 'iso-8859-1']              # Charset utiliser pour décoder/encoder les messages
        """0: utf-8 | 1: iso-8859-1"""

        self.SSL_VERSION = None                             # Version SSL

        self.Config = Config().ConfigObject

        # Liste des commandes internes du bot
        self.commands_level = {
            0: ['help', 'auth', 'copyright', 'uptime', 'firstauth'],
            1: ['load','reload','unload', 'deauth', 'checkversion'],
            2: ['show_modules', 'show_timers', 'show_threads', 'show_channels', 'show_users', 'show_admins'],
            3: ['quit', 'restart','addaccess','editaccess', 'delaccess']
        }

        # l'ensemble des commandes.
        self.commands = []
        for level, commands in self.commands_level.items():
            for command in self.commands_level[level]:
                self.commands.append(command)

        self.Base = Base(self.Config)
        self.User = User(self.Base)
        self.Admin = Admin(self.Base)
        self.Channel = Channel(self.Base)
        self.Clones = Clones(self.Base)

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
                self.SSL_VERSION = self.IrcSocket.version()
                self.Base.logs.info(f"Connexion en mode SSL : Version = {self.SSL_VERSION}")
            else:
                soc.connect(connexion_information)
                self.IrcSocket:socket.socket = soc
                self.Base.logs.info("Connexion en mode normal")

            return None

        except ssl.SSLEOFError as soe:
            self.Base.logs.critical(f"SSLEOFError __create_socket: {soe} - {soc.fileno()}")
        except ssl.SSLError as se:
            self.Base.logs.critical(f"SSLError __create_socket: {se} - {soc.fileno()}")
        except OSError as oe:
            self.Base.logs.critical(f"OSError __create_socket: {oe} - {soc.fileno()}")
        except AttributeError as ae:
            self.Base.logs.critical(f"AttributeError __create_socket: {ae} - {soc.fileno()}")

    def __ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.Base.logs.debug(f'SSLContext initiated with verified mode {ctx.verify_mode}')

        return ctx

    def __connect_to_irc(self, ircInstance: 'Irc') -> None:
        try:
            self.ircObject = ircInstance                        # créer une copie de l'instance Irc
            self.__link(self.IrcSocket)                         # établir la connexion au serveur IRC
            self.signal = True                                  # Une variable pour initier la boucle infinie
            self.__join_saved_channels()                        # Join existing channels
            self.load_existing_modules()                        # Charger les modules existant dans la base de données

            while self.signal:
                try:
                    if self.RESTART == 1:
                        self.Base.logs.debug('Restarting Defender ...')
                        self.IrcSocket.shutdown(socket.SHUT_RDWR)
                        self.IrcSocket.close()

                        while self.IrcSocket.fileno() != -1:
                            time.sleep(0.5)
                            self.Base.logs.warning('--> Waiting for socket to close ...')

                        # Reload configuration
                        self.Base.logs.debug('Reloading configuration')
                        self.Config = Config().ConfigObject
                        self.Base = Base(self.Config)

                        self.__create_socket()
                        self.__link(self.IrcSocket)
                        self.__join_saved_channels()
                        self.load_existing_modules()
                        self.RESTART = 0

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

    def __link(self, writer:Union[socket.socket, SSLSocket]) -> None:
        """Créer le link et envoyer les informations nécessaires pour la 
        connexion au serveur.

        Args:
            writer (StreamWriter): permet l'envoi des informations au serveur.
        """
        try:
            nickname = self.Config.SERVICE_NICKNAME
            username = self.Config.SERVICE_USERNAME
            realname = self.Config.SERVICE_REALNAME
            chan = self.Config.SERVICE_CHANLOG
            info = self.Config.SERVICE_INFO
            smodes = self.Config.SERVICE_SMODES
            cmodes = self.Config.SERVICE_CMODES
            umodes = self.Config.SERVICE_UMODES
            host = self.Config.SERVICE_HOST
            service_name = self.Config.SERVICE_NAME

            password = self.Config.SERVEUR_PASSWORD
            link = self.Config.SERVEUR_LINK
            sid = self.Config.SERVEUR_ID
            service_id = self.Config.SERVICE_ID

            version = self.Config.current_version
            unixtime = self.Base.get_unixtime()
            charset = self.CHARSET[0]

            # Envoyer un message d'identification
            writer.send(f":{sid} PASS :{password}\r\n".encode(charset))
            writer.send(f":{sid} PROTOCTL SID NOQUIT NICKv2 SJOIN SJ3 NICKIP TKLEXT2 NEXTBANS CLK EXTSWHOIS MLOCK MTAGS\r\n".encode(charset))
            # writer.send(f":{sid} PROTOCTL NICKv2 VHP UMODE2 NICKIP SJOIN SJOIN2 SJ3 NOQUIT TKLEXT MLOCK SID MTAGS\r\n".encode(charset))
            writer.send(f":{sid} PROTOCTL EAUTH={link},,,{service_name}-v{version}\r\n".encode(charset))
            writer.send(f":{sid} PROTOCTL SID={sid}\r\n".encode(charset))
            writer.send(f":{sid} SERVER {link} 1 :{info}\r\n".encode(charset))
            writer.send(f":{sid} {nickname} :Reserved for services\r\n".encode(charset))
            #writer.send(f":{sid} UID {nickname} 1 {unixtime} {username} {host} {service_id} * {smodes} * * * :{realname}\r\n".encode(charset))
            writer.send(f":{sid} UID {nickname} 1 {unixtime} {username} {host} {service_id} * {smodes} * * fwAAAQ== :{realname}\r\n".encode(charset))
            writer.send(f":{sid} SJOIN {unixtime} {chan} + :{service_id}\r\n".encode(charset))
            writer.send(f":{sid} TKL + Q * {nickname} {host} 0 {unixtime} :Reserved for services\r\n".encode(charset))

            writer.send(f":{service_id} MODE {chan} +{cmodes}\r\n".encode(charset))
            writer.send(f":{service_id} MODE {chan} +{umodes} {service_id}\r\n".encode(charset))

            self.Base.logs.debug('>> Link information sent to the server')

            return None
        except AttributeError as ae:
            self.Base.logs.critical(f'{ae}')

    def __join_saved_channels(self) -> None:
        """## Joining saved channels"""
        core_table = self.Config.table_channel

        query = f'''SELECT distinct channel_name FROM {core_table}'''
        exec_query = self.Base.db_execute_query(query)
        result_query = exec_query.fetchall()

        if result_query:
            for chan_name in result_query:
                chan = chan_name[0]
                self.send2socket(f":{self.Config.SERVEUR_ID} SJOIN {self.Base.get_unixtime()} {chan} + :{self.Config.SERVICE_ID}")

    def send2socket(self, send_message:str) -> None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            string (Str): contient la commande à envoyer au serveur.
        """
        try:
            with self.Base.lock:
                self.IrcSocket.send(f"{send_message}\r\n".encode(self.CHARSET[0]))
                self.Base.logs.debug(f'{send_message}')

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

    def sendNotice(self, msg:str, nickname: str) -> None:
        """Sending NOTICE by batches

        Args:
            msg (str): The message to send to the server
            nickname (str): The reciever Nickname
        """
        batch_size = self.Config.BATCH_SIZE
        service_nickname = self.Config.SERVICE_NICKNAME

        for i in range(0, len(str(msg)), batch_size):
            batch = str(msg)[i:i+batch_size]
            self.send2socket(f":{service_nickname} NOTICE {nickname} :{batch}")

    def sendPrivMsg(self, msg: str, channel: str = None, nickname: str = None):
        """Sending PRIVMSG to a channel or to a nickname by batches
        could be either channel or nickname not both together
        Args:
            msg (str): The message to send
            channel (str, optional): The receiver channel. Defaults to None.
            nickname (str, optional): The reciever nickname. Defaults to None.
        """
        batch_size = self.Config.BATCH_SIZE
        service_nickname = self.Config.SERVICE_NICKNAME

        if not channel is None:
            for i in range(0, len(str(msg)), batch_size):
                batch = str(msg)[i:i+batch_size]
                self.send2socket(f":{service_nickname} PRIVMSG {channel} :{batch}")

        if not nickname is None:
            for i in range(0, len(str(msg)), batch_size):
                batch = str(msg)[i:i+batch_size]
                self.send2socket(f":{service_nickname} PRIVMSG {nickname} :{batch}")

    def send_response(self, responses:list[bytes]) -> None:
        try:
            # print(data)
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
        result = self.Base.db_execute_query(f"SELECT module_name FROM {self.Config.table_module}")
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
            # self.send2socket(f':{service_id} PING :{hsid}')
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
        self.send2socket(f':{service_id} PING :{hsid}')

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
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Le module {module_name} est déja chargé ! si vous souhaiter le recharge tapez {self.Config.SERVICE_PREFIX}reload {module_name}")
                    return False

                the_module = sys.modules['mods.' + module_name]
                importlib.reload(the_module)
                my_class = getattr(the_module, class_name, None)
                new_instance = my_class(self.ircObject)
                self.loaded_classes[class_name] = new_instance

                # Créer le module dans la base de données
                if not init:
                    self.Base.db_record_module(fromuser, module_name)

                self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} chargé")
                return False

            # Charger le module
            loaded_module = importlib.import_module(f"mods.{module_name}")

            my_class = getattr(loaded_module, class_name, None)                 # Récuperer le nom de classe
            create_instance_of_the_class = my_class(self.ircObject)             # Créer une nouvelle instance de la classe

            if not hasattr(create_instance_of_the_class, 'cmd'):
                self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} ne contient pas de méthode cmd")
                self.Base.logs.critical(f"The Module {module_name} has not been loaded because cmd method is not available")
                self.Base.db_delete_module(module_name)
                return False

            # Charger la nouvelle class dans la variable globale
            self.loaded_classes[class_name] = create_instance_of_the_class

            # Enregistrer le module dans la base de données
            if not init:
                self.Base.db_record_module(fromuser, module_name)
            self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} chargé")

            self.Base.logs.info(self.loaded_classes)
            return True

        except ModuleNotFoundError as moduleNotFound:
            self.Base.logs.error(f"MODULE_NOT_FOUND: {moduleNotFound}")
            self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :[ {self.Config.COLORS.red}MODULE_NOT_FOUND{self.Config.COLORS.black} ]: {moduleNotFound}")
            self.Base.db_delete_module(module_name)
        except Exception as e:
            self.Base.logs.error(f"Something went wrong with a module you want to load : {e}")
            self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :[ {self.Config.COLORS.red}ERROR{self.Config.COLORS.black} ]: {e}")

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

                self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} supprimé")
                return True

        except Exception as err:
            self.Base.logs.error(f"General Error: {err}")
            return False

    def insert_db_admin(self, uid:str, level:int) -> None:

        if self.User.get_User(uid) is None:
            return None
        
        getUser = self.User.get_User(uid)

        nickname = getUser.nickname
        username = getUser.username
        hostname = getUser.hostname
        umodes = getUser.umodes
        vhost = getUser.vhost
        level = int(level)

        self.Admin.insert(
            self.Admin.AdminModel(
                uid=uid,
                nickname=nickname,
                username=username,
                hostname=hostname,
                umodes=umodes,
                vhost=vhost,
                level=level,
                connexion_datetime=datetime.now()
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
        query_search_user = f"SELECT id FROM {self.Config.table_admin} WHERE user=:admin"
        r = self.Base.db_execute_query(query_search_user, mes_donnees)
        exist_user = r.fetchone()

        # On verifie si le user exist dans la base
        if not exist_user:
            mes_donnees = {'datetime': self.Base.get_datetime(), 'user': nickname, 'password': spassword, 'hostname': hostname, 'vhost': vhost, 'level': level}
            self.Base.db_execute_query(f'''INSERT INTO {self.Config.table_admin} 
                    (createdOn, user, password, hostname, vhost, level) VALUES
                    (:datetime, :user, :password, :hostname, :vhost, :level)
                    ''', mes_donnees)
            response = f"{nickname} ajouté en tant qu'administrateur de niveau {level}"
            self.send2socket(f':{self.Config.SERVICE_NICKNAME} NOTICE {nickname} : {response}')
            self.Base.logs.info(response)
            return response
        else:
            response = f'{nickname} Existe déjà dans les users enregistrés'
            self.send2socket(f':{self.Config.SERVICE_NICKNAME} NOTICE {nickname} : {response}')
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
            self.send2socket(f':{dnickname} NOTICE {fromuser} : New Version available : {self.Config.current_version} >>> {self.Config.latest_version}')
            self.send2socket(f':{dnickname} NOTICE {fromuser} : Please run (git pull origin main) in the current folder')
        else:
            self.send2socket(f':{dnickname} NOTICE {fromuser} : You have the latest version of defender')

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
                    self.Base.logs.debug(data_copy)
                else:
                    self.Base.logs.debug(original_response)
            else:
                self.Base.logs.debug(original_response)

            match original_response[0]:

                case 'PING':
                    # Sending PONG response to the serveur
                    pong = str(original_response[1]).replace(':','')
                    self.send2socket(f"PONG :{pong}")
                    return None

                case 'PROTOCTL':
                    #['PROTOCTL', 'CHANMODES=beI,fkL,lFH,cdimnprstzCDGKMNOPQRSTVZ', 'USERMODES=diopqrstwxzBDGHIRSTWZ', 'BOOTED=1702138935', 
                    # 'PREFIX=(qaohv)~&@%+', 'SID=001', 'MLOCK', 'TS=1703793941', 'EXTSWHOIS']

                    # GET SERVER ID HOST
                    if len(original_response) > 5:
                        if '=' in original_response[5]:
                            serveur_hosting_id = str(original_response[5]).split('=')
                            self.HSID = serveur_hosting_id[1]
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

                case 'SQUIT':
                    # ['@msgid=QOEolbRxdhpVW5c8qLkbAU;time=2024-09-21T17:33:16.547Z', 'SQUIT', 'defender.deb.biz.st', ':Connection', 'closed']
                    server_hostname = interm_response[1]
                    uid_to_delete = ''
                    for s_user in self.User.UID_DB:
                        if s_user.hostname == server_hostname and 'S' in s_user.umodes:
                            uid_to_delete = s_user.uid

                    self.User.delete(uid_to_delete)
                    self.Channel.delete_user_from_all_channel(uid_to_delete)

                case 'SJOIN':
                    # If Server Join channels
                    # [':11Z', 'SJOIN', '1726940687', '#welcome', '+', ':11ZAAAAAB']
                    channel_joined = original_response[3]
                    server_uid = self.Base.clean_uid(original_response[5])

                    self.Channel.insert(
                        self.Channel.ChannelModel(
                            name=channel_joined,
                            uids=[server_uid]
                        )
                    )

                case 'REPUTATION':
                    # :001 REPUTATION 91.168.141.239 118
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
                    if hsid == self.HSID:
                        if self.INIT == 1:
                            current_version = self.Config.current_version
                            latest_version = self.Config.latest_version
                            if self.Base.check_for_new_version(False):
                                version = f'{current_version} >>> {latest_version}'
                            else:
                                version = f'{current_version}'

                            print(f"################### DEFENDER ###################")
                            print(f"#               SERVICE CONNECTE                ")
                            print(f"# SERVEUR  :    {self.Config.SERVEUR_IP}        ")
                            print(f"# PORT     :    {self.Config.SERVEUR_PORT}      ")
                            print(f"# SSL      :    {self.Config.SERVEUR_SSL}       ")
                            print(f"# SSL VER  :    {self.SSL_VERSION}              ")
                            print(f"# NICKNAME :    {self.Config.SERVICE_NICKNAME}  ")
                            print(f"# CHANNEL  :    {self.Config.SERVICE_CHANLOG}   ")
                            print(f"# VERSION  :    {version}                       ")
                            print(f"################################################")

                            self.Base.logs.info(f"################### DEFENDER ###################")
                            self.Base.logs.info(f"#               SERVICE CONNECTE                ")
                            self.Base.logs.info(f"# SERVEUR  :    {self.Config.SERVEUR_IP}        ")
                            self.Base.logs.info(f"# PORT     :    {self.Config.SERVEUR_PORT}      ")
                            self.Base.logs.info(f"# SSL      :    {self.Config.SERVEUR_SSL}       ")
                            self.Base.logs.info(f"# SSL VER  :    {self.SSL_VERSION}              ")
                            self.Base.logs.info(f"# NICKNAME :    {self.Config.SERVICE_NICKNAME}  ")
                            self.Base.logs.info(f"# CHANNEL  :    {self.Config.SERVICE_CHANLOG}   ")
                            self.Base.logs.info(f"# VERSION  :    {version}                       ")
                            self.Base.logs.info(f"################################################")
                            
                            if self.Base.check_for_new_version(False):
                                self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} : New Version available {version}")

                        # Initialisation terminé aprés le premier PING
                        self.sendPrivMsg(msg=f'[{self.Config.COLORS.green}INFORMATION{self.Config.COLORS.nogc}] >> Defender is ready', channel=self.Config.SERVICE_CHANLOG)
                        self.INIT = 0

                case _:
                    pass

            if len(original_response) < 3:
                return False

            match original_response[2]:

                case 'QUIT':
                    # :001N1WD7L QUIT :Quit: free_znc_1

                    uid_who_quit = str(interm_response[0]).replace(':', '')
                    self.User.delete(uid_who_quit)
                    self.Channel.delete_user_from_all_channel(uid_who_quit)

                case 'PONG':
                    # ['@msgid=aTNJhp17kcPboF5diQqkUL;time=2023-12-28T20:35:58.411Z', ':irc.deb.biz.st', 'PONG', 'irc.deb.biz.st', ':Dev-PyDefender']
                    self.Base.execute_periodic_action()

                case 'NICK':
                    # ['@unrealircd.org/geoip=FR;unrealircd.org/', ':001OOU2H3', 'NICK', 'WebIrc', '1703795844']
                    # Changement de nickname

                    uid = str(interm_response[0]).replace(':','')
                    newnickname = interm_response[2]
                    self.User.update(uid, newnickname)

                case 'MODE':
                    #['@msgid=d0ySx56Yd0nc35oHts2SkC-/J9mVUA1hfM6+Z4494xWUg;time=2024-08-09T12:45:36.651Z', 
                    # ':001', 'MODE', '#a', '+nt', '1723207536']
                    pass

                case 'SJOIN':
                    # ['@msgid=5sTwGdj349D82L96p749SY;time=2024-08-15T09:50:23.528Z', ':001', 'SJOIN', '1721564574', '#welcome', ':001JD94QH']
                    # ['@msgid=bvceb6HthbLJapgGLXn1b0;time=2024-08-15T09:50:11.464Z', ':001', 'SJOIN', '1721564574', '#welcome', '+lnrt', '13', ':001CIVLQF', '+11ZAAAAAB', '001QGR10C', '*@0014UE10B', '001NL1O07', '001SWZR05', '001HB8G04', '@00BAAAAAJ', '0019M7101']
                    # ['@msgid=SKUeuVzOrTShRDduq8VerX;time=2024-08-23T19:37:04.266Z', ':001', 'SJOIN', '1723993047', '#welcome', '+lnrt', '13', 
                    # ':001T6VU3F', '001JGWB2K', '@11ZAAAAAB', 
                    # '001F16WGR', '001X9YMGQ', '*+001DYPFGP', '@00BAAAAAJ', '001AAGOG9', '001FMFVG8', '001DAEEG7', 
                    # '&~G:unknown-users', '"~G:websocket-users', '"~G:known-users', '"~G:webirc-users']

                    channel = str(interm_response[3]).lower()
                    len_cmd = len(interm_response)
                    list_users:list = []
                    occurence = 0
                    start_boucle = 0

                    # Trouver le premier user
                    for i in range(len_cmd):
                        s: list = re.findall(fr':', interm_response[i])
                        if s:
                            occurence += 1
                            if occurence == 2:
                                start_boucle = i

                    # Boucle qui va ajouter l'ensemble des users (UID)
                    for i in range(start_boucle, len(interm_response)):
                        parsed_UID = str(interm_response[i])
                        # pattern = fr'[:|@|%|\+|~|\*]*'
                        # pattern = fr':'
                        # parsed_UID = re.sub(pattern, '', parsed_UID)
                        clean_uid = self.Base.clean_uid(parsed_UID)
                        if len(clean_uid) == 9:
                            list_users.append(parsed_UID)

                    self.Channel.insert(
                        self.Channel.ChannelModel(
                            name=channel,
                            uids=list_users
                        )
                    )

                case 'PART':
                    # ['@unrealircd.org/geoip=FR;unrealircd.org/userhost=50d6492c@80.214.73.44;unrealircd.org/userip=50d6492c@80.214.73.44;msgid=YSIPB9q4PcRu0EVfC9ci7y-/mZT0+Gj5FLiDSZshH5NCw;time=2024-08-15T15:35:53.772Z', 
                    # ':001EPFBRD', 'PART', '#welcome', ':WEB', 'IRC', 'Paris']
                    try:
                        uid = str(interm_response[0]).replace(':','')
                        channel = str(interm_response[2]).lower()
                        self.Channel.delete_user_from_channel(channel, uid)

                    except IndexError as ie:
                        self.Base.logs.error(f'Index Error: {ie}')

                case 'UID':
                    try:
                        # ['@s2s-md/geoip=cc=GB|cd=United\\sKingdom|asn=16276|asname=OVH\\sSAS;s2s-md/tls_cipher=TLSv1.3-TLS_CHACHA20_POLY1305_SHA256;s2s-md/creationtime=1721564601', 
                        # ':001', 'UID', 'albatros', '0', '1721564597', 'albatros', 'vps-91b2f28b.vps.ovh.net', 
                        # '001HB8G04', '0', '+iwxz', 'Clk-A62F1D18.vps.ovh.net', 'Clk-A62F1D18.vps.ovh.net', 'MyZBwg==', ':...']

                        isWebirc = True if 'webirc' in original_response[0] else False
                        isWebsocket = True if 'websocket' in original_response[0] else False

                        uid = str(original_response[8])
                        nickname = str(original_response[3])
                        username = str(original_response[6])
                        hostname = str(original_response[7])
                        umodes = str(original_response[10])
                        vhost = str(original_response[11])

                        if not 'S' in umodes:
                            remote_ip = self.Base.decode_ip(str(original_response[13]))
                        else:
                            remote_ip = '127.0.0.1'

                        # extract realname
                        realname_list = []
                        for i in range(14, len(original_response)):
                            realname_list.append(original_response[i])

                        realname = ' '.join(realname_list)[1:]

                        # Extract Geoip information
                        pattern = r'^.*geoip=cc=(\S{2}).*$'
                        geoip_match = re.match(pattern, original_response[0])

                        if geoip_match:
                            geoip = geoip_match.group(1)
                        else:
                            geoip = None

                        score_connexion = self.first_score

                        self.User.insert(
                            self.User.UserModel(
                                uid=uid,
                                nickname=nickname,
                                username=username,
                                realname=realname,
                                hostname=hostname,
                                umodes=umodes,
                                vhost=vhost,
                                isWebirc=isWebirc,
                                isWebsocket=isWebsocket,
                                remote_ip=remote_ip,
                                geoip=geoip,
                                score_connexion=score_connexion,
                                connexion_datetime=datetime.now()
                            )
                        )

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
                                self.Base.logs.info(cmd_copy)
                            else:
                                self.Base.logs.info(cmd)
                        else:
                            self.Base.logs.info(f'{cmd}')

                        pattern = fr'(:\{self.Config.SERVICE_PREFIX})(.*)$'
                        hcmds = re.search(pattern, ' '.join(cmd)) # va matcher avec tout les caractéres aprés le .

                        if hcmds: # Commande qui commencent par le point
                            liste_des_commandes = list(hcmds.groups())
                            convert_to_string = ' '.join(liste_des_commandes)
                            arg = convert_to_string.split()
                            arg.remove(f':{self.Config.SERVICE_PREFIX}')
                            if not arg[0].lower() in self.commands:
                                self.Base.logs.debug(f"This command {arg[0]} is not available")
                                return False

                            cmd_to_send = convert_to_string.replace(':','')
                            self.Base.log_cmd(user_trigger, cmd_to_send)

                            fromchannel = str(cmd[2]).lower() if self.Base.Is_Channel(cmd[2]) else None
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
                                    self.send2socket(f':{dnickname} NOTICE {user_trigger} :\x01VERSION Service {self.Config.SERVICE_NICKNAME} V{self.Config.current_version}\x01')
                                    return False

                                # Réponse a un TIME
                                if arg[0] == '\x01TIME\x01':
                                    current_datetime = self.Base.get_datetime()
                                    self.send2socket(f':{dnickname} NOTICE {user_trigger} :\x01TIME {current_datetime}\x01')
                                    return False

                                # Réponse a un PING
                                if arg[0] == '\x01PING':
                                    recieved_unixtime = int(arg[1].replace('\x01',''))
                                    current_unixtime = self.Base.get_unixtime()
                                    ping_response = current_unixtime - recieved_unixtime

                                    self.send2socket(f'PONG :{recieved_unixtime}')
                                    self.send2socket(f':{dnickname} NOTICE {user_trigger} :\x01PING {recieved_unixtime} secs\x01')
                                    return False

                                if not arg[0].lower() in self.commands:
                                    self.Base.logs.debug(f"This command {arg[0]} sent by {user_trigger} is not available")
                                    return False

                                cmd_to_send = convert_to_string.replace(':','')
                                self.Base.log_cmd(user_trigger, cmd_to_send)

                                fromchannel = None
                                if len(arg) >= 2:
                                    fromchannel = str(arg[1]).lower() if self.Base.Is_Channel(arg[1]) else None

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
                    self.send2socket(f':{dnickname} PRIVMSG {dchanlog} :[ {self.Config.COLORS.red}{current_command}{self.Config.COLORS.black} ] - Accès Refusé à {self.User.get_nickname(fromuser)}')
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Accès Refusé')
                except IndexError as ie:
                    self.Base.logs.error(f'{ie}')

            case 'deauth':

                current_command = cmd[0]
                uid_to_deauth = self.User.get_uid(fromuser)
                self.delete_db_admin(uid_to_deauth)
                self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.COLORS.red}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} est désormais déconnecter de {dnickname}")

            case 'firstauth':
                # firstauth OWNER_NICKNAME OWNER_PASSWORD
                current_nickname = self.User.get_nickname(fromuser)
                current_uid = self.User.get_uid(fromuser)
                current_command = str(cmd[0])

                query = f"SELECT count(id) as c FROM {self.Config.table_admin}"
                result = self.Base.db_execute_query(query)
                result_db = result.fetchone()

                if result_db[0] > 0:
                    self.send2socket(f":{dnickname} NOTICE {fromuser} :You can't use this command anymore ! Please use [{self.Config.SERVICE_PREFIX}auth] instead")
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
                    self.send2socket(f":{dnickname} NOTICE {fromuser} :The current nickname [{fromuser}] is different than the nickname sent [{cmd_owner}] !")
                    return False

                if current_nickname != config_owner:
                    self.Base.logs.critical(f"The current nickname [{current_nickname}] is different than the configuration owner [{config_owner}] !")
                    self.send2socket(f":{dnickname} NOTICE {fromuser} :The current nickname [{current_nickname}] is different than the configuration owner [{config_owner}] !")
                    return False

                if cmd_owner != config_owner:
                    self.Base.logs.critical(f"The nickname sent [{cmd_owner}] is different than the configuration owner [{config_owner}] !")
                    self.send2socket(f":{dnickname} NOTICE {fromuser} :The nickname sent [{cmd_owner}] is different than the configuration owner [{config_owner}] !")
                    return False

                if cmd_owner == config_owner and cmd_password == config_password:
                    self.Base.db_create_first_admin()
                    self.insert_db_admin(current_uid, 5)
                    self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.COLORS.green}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} est désormais connecté a {dnickname}")
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} NOTICE {fromuser} :Connexion a {dnickname} réussie!")
                else:
                    self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.COLORS.red}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} a tapé un mauvais mot de pass")
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} NOTICE {fromuser} :Mot de passe incorrecte")

            case 'auth':
                # ['auth', 'adator', 'password']
                current_command = cmd[0]
                user_to_log = self.User.get_nickname(cmd[1])
                password = cmd[2]

                if fromuser != user_to_log:
                    # If the current nickname is different from the nickname you want to log in with
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} NOTICE {fromuser} :Your current nickname is different from the nickname you want to log in with")
                    return False

                if not user_to_log is None:
                    mes_donnees = {'user': user_to_log, 'password': self.Base.crypt_password(password)}
                    query = f"SELECT id, level FROM {self.Config.table_admin} WHERE user = :user AND password = :password"
                    result = self.Base.db_execute_query(query, mes_donnees)
                    user_from_db = result.fetchone()

                    if not user_from_db is None:
                        uid_user = self.User.get_uid(user_to_log)
                        self.insert_db_admin(uid_user, user_from_db[1])
                        self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.COLORS.green}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} est désormais connecté a {dnickname}")
                        self.send2socket(f":{self.Config.SERVICE_NICKNAME} NOTICE {fromuser} :Connexion a {dnickname} réussie!")
                    else:
                        self.send2socket(f":{dnickname} PRIVMSG {dchanlog} :[ {self.Config.COLORS.red}{str(current_command).upper()} ]{self.Config.COLORS.black} - {self.User.get_nickname(fromuser)} a tapé un mauvais mot de pass")
                        self.send2socket(f":{self.Config.SERVICE_NICKNAME} NOTICE {fromuser} :Mot de passe incorrecte")

                else:
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} NOTICE {fromuser} :L'utilisateur {user_to_log} n'existe pas")

            case 'addaccess':
                try:
                    # .addaccess adator 5 password
                    if len(cmd) < 4:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} addaccess [nickname] [level] [password]')
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : level: from 1 to 4')

                    newnickname = cmd[1]
                    newlevel = self.Base.int_if_possible(cmd[2])
                    password = cmd[3]

                    response = self.create_defender_user(newnickname, newlevel, password)
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : {response}')
                    self.Base.logs.info(response)

                except IndexError as ie:
                    self.Base.logs.error(f'_hcmd addaccess: {ie}')
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} addaccess [nickname] [level] [password]')
                except TypeError as te:
                    self.Base.logs.error(f'_hcmd addaccess: out of index : {te}')
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Right command : /msg {dnickname} addaccess [nickname] [level] [password]')

            case 'editaccess':
                # .editaccess [USER] [PASSWORD] [LEVEL]
                try:
                    user_to_edit = cmd[1]
                    user_new_level = int(cmd[3])
                    user_password = self.Base.crypt_password(cmd[2])

                    if len(cmd) < 4 or len(cmd) > 4:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : .editaccess [USER] [NEWPASSWORD] [NEWLEVEL]')
                        return None

                    get_admin = self.Admin.get_Admin(fromuser)
                    if get_admin is None:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : This user {fromuser} has no Admin access')
                        return None

                    current_user = self.User.get_nickname(fromuser)
                    current_uid = self.User.get_uid(fromuser)
                    current_user_level = get_admin.level

                    if user_new_level > 5:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : Maximum authorized level is 5')
                        return None

                    # Rechercher le user dans la base de données.
                    mes_donnees = {'user': user_to_edit}
                    query = f"SELECT user, level FROM {self.Config.table_admin} WHERE user = :user"
                    result = self.Base.db_execute_query(query, mes_donnees)

                    isUserExist = result.fetchone()
                    if not isUserExist is None:

                        if current_user_level < int(isUserExist[1]):
                            self.send2socket(f':{dnickname} NOTICE {fromuser} : You are not allowed to edit this access')
                            return None
                        
                        if current_user_level == int(isUserExist[1]) and current_user != user_to_edit:
                            self.send2socket(f":{dnickname} NOTICE {fromuser} : You can't edit access of a user with same level")
                            return None

                        # Le user existe dans la base de données
                        data_to_update = {'user': user_to_edit, 'password': user_password, 'level': user_new_level}
                        sql_update = f"UPDATE {self.Config.table_admin} SET level = :level, password = :password WHERE user = :user"
                        exec_query = self.Base.db_execute_query(sql_update, data_to_update)
                        if exec_query.rowcount > 0:
                            self.send2socket(f':{dnickname} NOTICE {fromuser} : User {user_to_edit} has been modified with level {str(user_new_level)}')
                        else:
                            self.send2socket(f":{dnickname} NOTICE {fromuser} : Impossible de modifier l'utilisateur {str(user_new_level)}")

                except TypeError as te:
                    self.Base.logs.error(f"Type error : {te}")
                except ValueError as ve:
                    self.Base.logs.error(f"Value Error : {ve}")
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : .editaccess [USER] [NEWPASSWORD] [NEWLEVEL]')

            case 'delaccess':
                # .delaccess [USER] [CONFIRMUSER]
                user_to_del = cmd[1]
                user_confirmation = cmd[2]

                if user_to_del != user_confirmation:
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer')
                    self.Base.logs.warning(f':{dnickname} NOTICE {fromuser} : Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer')
                    return None

                if len(cmd) < 3:
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : .delaccess [USER] [CONFIRMUSER]')
                    return None
                
                get_admin = self.Admin.get_Admin(fromuser)
                
                if get_admin is None:
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : This user {fromuser} has no admin access')
                    return None

                current_user = self.User.get_nickname(fromuser)
                current_uid = self.User.get_uid(fromuser)
                current_user_level = get_admin.level

                # Rechercher le user dans la base de données.
                mes_donnees = {'user': user_to_del}
                query = f"SELECT user, level FROM {self.Config.table_admin} WHERE user = :user"
                result = self.Base.db_execute_query(query, mes_donnees)
                info_user = result.fetchone()
                
                if not info_user is None:
                    level_user_to_del = info_user[1]
                    if current_user_level <= level_user_to_del:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : You are not allowed to delete this access')
                        self.Base.logs.warning(f':{dnickname} NOTICE {fromuser} : You are not allowed to delete this access')
                        return None

                    data_to_delete = {'user': user_to_del}
                    sql_delete = f"DELETE FROM {self.Config.table_admin} WHERE user = :user"
                    exec_query = self.Base.db_execute_query(sql_delete, data_to_delete)
                    if exec_query.rowcount > 0:
                        self.send2socket(f':{dnickname} NOTICE {fromuser} : User {user_to_del} has been deleted !')
                    else:
                        self.send2socket(f":{dnickname} NOTICE {fromuser} : Impossible de supprimer l'utilisateur.")
                        self.Base.logs.warning(f":{dnickname} NOTICE {fromuser} : Impossible de supprimer l'utilisateur.")

            case 'help':

                count_level_definition = 0
                get_admin = self.Admin.get_Admin(uid)
                if not get_admin is None:
                    user_level = get_admin.level
                else:
                    user_level = 0

                self.send2socket(f':{dnickname} NOTICE {fromuser} : ***************** LISTE DES COMMANDES *****************')
                self.send2socket(f':{dnickname} NOTICE {fromuser} : ')
                for levDef in self.commands_level:

                    if int(user_level) >= int(count_level_definition):

                        self.send2socket(f':{dnickname} NOTICE {fromuser} : ***************** {self.Config.COLORS.nogc}[ {self.Config.COLORS.green}LEVEL {str(levDef)} {self.Config.COLORS.nogc}] *****************')

                        batch = 7
                        for i in range(0, len(self.commands_level[count_level_definition]), batch):
                            groupe = self.commands_level[count_level_definition][i:i + batch]  # Extraire le groupe
                            batch_commands = ' | '.join(groupe)
                            self.send2socket(f':{dnickname} NOTICE {fromuser} : {batch_commands}')

                    count_level_definition += 1
                    self.send2socket(f':{dnickname} NOTICE {fromuser} : ')

                self.send2socket(f':{dnickname} NOTICE {fromuser} : ***************** FIN DES COMMANDES *****************')

            case 'load':

                self.load_module(fromuser, str(cmd[1]))

            case 'unload':
                # unload mod_defender
                try:
                    module_name = str(cmd[1]).lower()                              # Le nom du module. exemple: mod_defender
                    self.unload_module(module_name)
                except Exception as err:
                    self.Base.logs.error(f"General Error: {err}")

            case 'reload':
                # reload mod_dktmb
                try:
                    module_name = str(cmd[1]).lower()                                          # ==> mod_defender
                    class_name = module_name.split('_')[1].capitalize()                        # ==> Defender

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

                        self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} rechargé")
                        return False
                    else:
                        self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Module {module_name} n'est pas chargé !")

                except TypeError as te:
                    self.Base.logs.error(f"A TypeError raised: {te}")
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :A TypeError raised: {te}")
                    self.Base.db_delete_module(module_name)
                except AttributeError as ae:
                    self.Base.logs.error(f"Missing Attribute: {ae}")
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Missing Attribute: {ae}")
                    self.Base.db_delete_module(module_name)
                except KeyError as ke:
                    self.Base.logs.error(f"Key Error: {ke}")
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Key Error: {ke}")
                    self.Base.db_delete_module(module_name)
                except Exception as e:
                    self.Base.logs.error(f"Something went wrong with a module you want to reload: {e}")
                    self.send2socket(f":{self.Config.SERVICE_NICKNAME} PRIVMSG {self.Config.SERVICE_CHANLOG} :Something went wrong with the module: {e}")
                    self.Base.db_delete_module(module_name)

            case 'quit':
                try:
                    reason = []
                    for i in range(1, len(cmd)):
                        reason.append(cmd[i])
                    final_reason = ' '.join(reason)

                    self.hb_active = False
                    self.Base.shutdown()
                    self.Base.execute_periodic_action()

                    self.send2socket(f':{dnickname} NOTICE {fromuser} : Arrêt du service {dnickname}')
                    self.send2socket(f':{self.Config.SERVEUR_LINK} SQUIT {self.Config.SERVEUR_LINK} :{final_reason}')
                    self.Base.logs.info(f'Arrêt du server {dnickname}')
                    self.RESTART = 0
                    self.signal = False

                except IndexError as ie:
                    self.Base.logs.error(f'{ie}')

                self.send2socket(f"QUIT Good bye")

            case 'restart':
                reason = []
                for i in range(1, len(cmd)):
                    reason.append(cmd[i])
                final_reason = ' '.join(reason)

                self.User.UID_DB.clear()                # Clear User Object
                self.Channel.UID_CHANNEL_DB.clear()     # Clear Channel Object

                for class_name in self.loaded_classes:
                    self.loaded_classes[class_name].unload()

                self.send2socket(f':{dnickname} NOTICE {fromuser} : Redémarrage du service {dnickname}')
                self.send2socket(f':{self.Config.SERVEUR_LINK} SQUIT {self.Config.SERVEUR_LINK} :{final_reason}')
                self.Base.logs.info(f'Redémarrage du server {dnickname}')
                self.loaded_classes.clear()
                self.RESTART = 1                 # Set restart status to 1 saying that the service will restart
                self.INIT = 1                    # set init to 1 saying that the service will be re initiated

            case 'show_modules':

                self.Base.logs.debug(self.loaded_classes)
                all_modules  = self.Base.get_all_modules()

                results = self.Base.db_execute_query(f'SELECT module_name FROM {self.Config.table_module}')
                results = results.fetchall()

                found = False

                for module in all_modules:
                    for loaded_mod in results:
                        if module == loaded_mod[0]:
                            found = True

                    if found:
                        self.send2socket(f":{dnickname} NOTICE {fromuser} :{module} - {self.Config.COLORS.green}Loaded{self.Config.COLORS.nogc}")
                    else:
                        self.send2socket(f":{dnickname} NOTICE {fromuser} :{module} - {self.Config.COLORS.red}Not Loaded{self.Config.COLORS.nogc}")

                    found = False

            case 'show_timers':

                if self.Base.running_timers:
                    for the_timer in self.Base.running_timers:
                        self.send2socket(f":{dnickname} NOTICE {fromuser} :>> {the_timer.getName()} - {the_timer.is_alive()}")
                else:
                    self.send2socket(f":{dnickname} NOTICE {fromuser} :Aucun timers en cours d'execution")

            case 'show_threads':

                for thread in self.Base.running_threads:
                    self.send2socket(f":{dnickname} NOTICE {fromuser} :>> {thread.getName()} ({thread.is_alive()})")

            case 'show_channels':

                for chan in self.Channel.UID_CHANNEL_DB:
                    list_nicknames: list = []
                    for uid in chan.uids:
                        pattern = fr'[:|@|%|\+|~|\*]*'
                        parsed_UID = re.sub(pattern, '', uid)
                        list_nicknames.append(self.User.get_nickname(parsed_UID))

                    self.send2socket(f":{dnickname} NOTICE {fromuser} : Channel: {chan.name} - Users: {list_nicknames}")

            case 'show_users':
                for db_user in self.User.UID_DB:
                    self.send2socket(f":{dnickname} NOTICE {fromuser} :UID : {db_user.uid} - isWebirc: {db_user.isWebirc} - isWebSocket: {db_user.isWebsocket} - Nickname: {db_user.nickname} - Connection: {db_user.connexion_datetime}")

            case 'show_admins':
                for db_admin in self.Admin.UID_ADMIN_DB:
                    self.send2socket(f":{dnickname} NOTICE {fromuser} :UID : {db_admin.uid} - Nickname: {db_admin.nickname} - Level: {db_admin.level} - Connection: {db_admin.connexion_datetime}")

            case 'uptime':
                uptime = self.get_defender_uptime()
                self.send2socket(f':{dnickname} NOTICE {fromuser} : {uptime}')

            case 'copyright':
                self.send2socket(f':{dnickname} NOTICE {fromuser} : # Defender V.{self.Config.current_version} Developped by adator® #')

            case 'checkversion':

                self.Base.create_thread(
                    self.thread_check_for_new_version,
                    (fromuser, )
                )

            case _:
                pass
