import time, threading, os, random, socket, hashlib, ipaddress, logging, requests, json, re, ast
from dataclasses import fields
from typing import Union, Literal
from base64 import b64decode, b64encode
from datetime import datetime
from sqlalchemy import create_engine, Engine, Connection, CursorResult
from sqlalchemy.sql import text
from core.loadConf import ConfigDataModel

class Base:

    def __init__(self, Config: ConfigDataModel) -> None:

        self.Config = Config                                    # Assigner l'objet de configuration
        self.init_log_system()                                  # Demarrer le systeme de log
        self.check_for_new_version(True)                        # Verifier si une nouvelle version est disponible

        self.running_timers:list[threading.Timer] = []          # Liste des timers en cours
        self.running_threads:list[threading.Thread] = []        # Liste des threads en cours
        self.running_sockets: list[socket.socket] = []          # Les sockets ouvert
        self.periodic_func:dict[object] = {}                    # Liste des fonctions en attentes

        self.lock = threading.RLock()                           # Création du lock

        self.install: bool = False                              # Initialisation de la variable d'installation
        self.engine, self.cursor = self.db_init()               # Initialisation de la connexion a la base de données
        self.__create_db()                                      # Initialisation de la base de données

        self.db_create_first_admin()                            # Créer un nouvel admin si la base de données est vide

    def __set_current_defender_version(self) -> None:
        """This will put the current version of Defender
        located in version.json
        """

        version_filename = f'.{os.sep}version.json'
        with open(version_filename, 'r') as version_data:
            current_version:dict[str, str] = json.load(version_data)

        # self.DEFENDER_VERSION = current_version["version"]
        self.Config.current_version = current_version['version']

        return None

    def __get_latest_defender_version(self) -> None:
        try:
            self.logs.debug(f'Looking for a new version available on Github')
            # print(f'===> Looking for a new version available on Github')
            token = ''
            json_url = f'https://raw.githubusercontent.com/adator85/IRC_DEFENDER_MODULES/main/version.json'
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3.raw'  # Indique à GitHub que nous voulons le contenu brut du fichier
            }

            if token == '':
                response = requests.get(json_url, timeout=self.Config.API_TIMEOUT)
            else:
                response = requests.get(json_url, headers=headers, timeout=self.Config.API_TIMEOUT)

            response.raise_for_status()  # Vérifie si la requête a réussi
            json_response:dict = response.json()
            # self.LATEST_DEFENDER_VERSION = json_response["version"]
            self.Config.latest_version = json_response['version']

            return None
        except requests.HTTPError as err:
            self.logs.error(f'Github not available to fetch latest version: {err}')
        except:
            self.logs.warning(f'Github not available to fetch latest version')

    def check_for_new_version(self, online:bool) -> bool:
        try:
            self.logs.debug(f'Checking for a new service version')

            # Assigner la version actuelle de Defender
            self.__set_current_defender_version()
            # Récuperer la dernier version disponible dans github
            if online:
                self.logs.debug(f'Retrieve the latest version from Github')
                self.__get_latest_defender_version()

            isNewVersion = False
            latest_version = self.Config.latest_version
            current_version = self.Config.current_version

            curr_major , curr_minor, curr_patch = current_version.split('.')
            last_major, last_minor, last_patch = latest_version.split('.')

            if int(last_major) > int(curr_major):
                self.logs.info(f'New version available: {current_version} >>> {latest_version}')
                isNewVersion = True
            elif int(last_major) == int(curr_major) and int(last_minor) > int(curr_minor):
                self.logs.info(f'New version available: {current_version} >>> {latest_version}')
                isNewVersion = True
            elif int(last_major) == int(curr_major) and int(last_minor) == int(curr_minor) and int(last_patch) > int(curr_patch):
                self.logs.info(f'New version available: {current_version} >>> {latest_version}')
                isNewVersion = True
            else:
                isNewVersion = False

            return isNewVersion
        except ValueError as ve:
            self.logs.error(f'Impossible to convert in version number : {ve}')

    def get_unixtime(self) -> int:
        """
        Cette fonction retourne un UNIXTIME de type 12365456
        Return: Current time in seconds since the Epoch (int)
        """
        unixtime = int( time.time() )
        return unixtime

    def get_datetime(self) -> str:
        """
        Retourne une date au format string (24-12-2023 20:50:59)
        """
        currentdate = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        return currentdate

    def get_all_modules(self) -> list:

        all_files = os.listdir('mods/')
        all_modules: list = []
        for module in all_files:
            if module.endswith('.py') and not module == '__init__.py':
                all_modules.append(module.replace('.py', '').lower())

        return all_modules

    def create_log(self, log_message: str) -> None:
        """Enregiste les logs

        Args:
            string (str): Le message a enregistrer

        Returns:
            None: Aucun retour
        """
        sql_insert = f"INSERT INTO {self.Config.table_log} (datetime, server_msg) VALUES (:datetime, :server_msg)"
        mes_donnees = {'datetime': str(self.get_datetime()),'server_msg': f'{log_message}'}
        self.db_execute_query(sql_insert, mes_donnees)

        return None

    def init_log_system(self) -> None:
        # Create folder if not available
        logs_directory = f'logs{os.sep}'
        if not os.path.exists(f'{logs_directory}'):
            os.makedirs(logs_directory)

        # Init logs object
        self.logs = logging
        self.logs.basicConfig(level=self.Config.DEBUG_LEVEL,
                              filename='logs/defender.log',
                              encoding='UTF-8',
                              format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(funcName)s - %(message)s')

        self.logs.info('#################### STARTING DEFENDER ####################')

        return None

    def log_cmd(self, user_cmd:str, cmd:str) -> None:
        """Enregistre les commandes envoyées par les utilisateurs

        Args:
            cmd (str): la commande a enregistrer
        """
        cmd_list = cmd.split()
        if len(cmd_list) == 3:
            if cmd_list[0].replace('.', '') == 'auth':
                cmd_list[1] = '*******'
                cmd_list[2] = '*******'
                cmd = ' '.join(cmd_list)

        insert_cmd_query = f"INSERT INTO {self.Config.table_commande} (datetime, user, commande) VALUES (:datetime, :user, :commande)"
        mes_donnees = {'datetime': self.get_datetime(), 'user': user_cmd, 'commande': cmd}
        self.db_execute_query(insert_cmd_query, mes_donnees)

        return False

    def db_isModuleExist(self, module_name:str) -> bool:
        """Teste si un module existe déja dans la base de données

        Args:
            module_name (str): le non du module a chercher dans la base de données

        Returns:
            bool: True si le module existe déja dans la base de données sinon False
        """
        query = f"SELECT id FROM {self.Config.table_module} WHERE module_name = :module_name"
        mes_donnes = {'module_name': module_name}
        results = self.db_execute_query(query, mes_donnes)

        if results.fetchall():
            return True
        else:
            return False

    def db_record_module(self, user_cmd:str, module_name:str, isdefault:int = 0) -> None:
        """Enregistre les modules dans la base de données

        Args:
            cmd (str): le module a enregistrer
        """

        if not self.db_isModuleExist(module_name):
            self.logs.debug(f"Le module {module_name} n'existe pas alors ont le créer")
            insert_cmd_query = f"INSERT INTO {self.Config.table_module} (datetime, user, module_name, isdefault) VALUES (:datetime, :user, :module_name, :isdefault)"
            mes_donnees = {'datetime': self.get_datetime(), 'user': user_cmd, 'module_name': module_name, 'isdefault': isdefault}
            self.db_execute_query(insert_cmd_query, mes_donnees)
        else:
            self.logs.debug(f"Le module {module_name} existe déja dans la base de données")

        return False

    def db_delete_module(self, module_name:str) -> None:
        """Supprime les modules de la base de données

        Args:
            cmd (str): le module a supprimer
        """
        insert_cmd_query = f"DELETE FROM {self.Config.table_module} WHERE module_name = :module_name"
        mes_donnees = {'module_name': module_name}
        self.db_execute_query(insert_cmd_query, mes_donnees)

        return False

    def db_sync_core_config(self, module_name: str, dataclassObj: object) -> bool:
        """Sync module local parameters with the database
        if new module then local param will be stored in the database
        if old module then db param will be moved to the local dataclassObj
        if new local param it will be stored in the database
        if local param was removed then it will also be removed from the database

        Args:
            module_name (str): The module name ex. mod_defender
            dataclassObj (object): The Dataclass object

        Returns:
            bool: _description_
        """
        try:
            response = True
            current_date = self.get_datetime()
            core_table = self.Config.table_config

            # Add local parameters to DB
            for field in fields(dataclassObj):
                param_key = field.name
                param_value = str(getattr(dataclassObj, field.name))

                param_to_search = {'module_name': module_name, 'param_key': param_key}

                search_query = f'''SELECT id FROM {core_table} WHERE module_name = :module_name AND param_key = :param_key'''
                excecute_search_query = self.db_execute_query(search_query, param_to_search)
                result_search_query = excecute_search_query.fetchone()

                if result_search_query is None:
                    # If param and module_name doesn't exist create the record
                    param_to_insert = {'datetime': current_date,'module_name': module_name,
                                       'param_key': param_key,'param_value': param_value
                                    }

                    insert_query = f'''INSERT INTO {core_table} (datetime, module_name, param_key, param_value) 
                                        VALUES (:datetime, :module_name, :param_key, :param_value)
                                        '''
                    execution = self.db_execute_query(insert_query, param_to_insert)

                    if execution.rowcount > 0:
                        self.logs.debug(f'New parameter added to the database: {param_key} --> {param_value}')

            # Delete from DB unused parameter
            query_select = f"SELECT module_name, param_key, param_value FROM {core_table} WHERE module_name = :module_name"
            parameter = {'module_name': module_name}
            execute_query_select = self.db_execute_query(query_select, parameter)
            result_query_select = execute_query_select.fetchall()

            for result in result_query_select:
                db_mod_name, db_param_key, db_param_value = result
                if not hasattr(dataclassObj, db_param_key):
                    mes_donnees = {'param_key': db_param_key, 'module_name': db_mod_name}
                    execute_delete = self.db_execute_query(f'DELETE FROM {core_table} WHERE module_name = :module_name and param_key = :param_key', mes_donnees)
                    row_affected = execute_delete.rowcount
                    if row_affected > 0:
                        self.logs.debug(f'A parameter has been deleted from the database: {db_param_key} --> {db_param_value} | Mod: {db_mod_name}')

            # Sync local variable with Database
            query = f"SELECT param_key, param_value FROM {core_table} WHERE module_name = :module_name"
            parameter = {'module_name': module_name}
            response = self.db_execute_query(query, parameter)
            result = response.fetchall()

            for param, value in result:
                if type(getattr(dataclassObj, param)) == list:
                    value = ast.literal_eval(value)

                setattr(dataclassObj, param, self.int_if_possible(value))

            return response

        except AttributeError as attrerr:
            self.logs.error(f'Attribute Error: {attrerr}')
        except Exception as err:
            self.logs.error(err)
            return False

    def db_update_core_config(self, module_name:str, dataclassObj: object, param_key:str, param_value: str) -> bool:

        core_table = self.Config.table_config
        # Check if the param exist
        if not hasattr(dataclassObj, param_key):
            self.logs.error(f"Le parametre {param_key} n'existe pas dans la variable global")
            return False

        mes_donnees = {'module_name': module_name, 'param_key': param_key, 'param_value': param_value}
        search_param_query = f"SELECT id FROM {core_table} WHERE module_name = :module_name AND param_key = :param_key"
        result = self.db_execute_query(search_param_query, mes_donnees)
        isParamExist = result.fetchone()

        if not isParamExist is None:
            mes_donnees = {'datetime': self.get_datetime(),
                           'module_name': module_name,
                           'param_key': param_key,
                           'param_value': param_value
                           }
            query = f'''UPDATE {core_table} SET datetime = :datetime, param_value = :param_value WHERE module_name = :module_name AND param_key = :param_key'''
            update = self.db_execute_query(query, mes_donnees)
            updated_rows = update.rowcount
            if updated_rows > 0:
                setattr(dataclassObj, param_key, self.int_if_possible(param_value))
                self.logs.debug(f'Parameter updated : {param_key} - {param_value} | Module: {module_name}')
            else:
                self.logs.error(f'Parameter NOT updated : {param_key} - {param_value} | Module: {module_name}')
        else:
            self.logs.error(f'Parameter and Module do not exist: Param ({param_key}) - Value ({param_value}) | Module ({module_name})')

        self.logs.debug(dataclassObj)

        return True

    def db_query_channel(self, action: Literal['add','del'], module_name: str, channel_name: str) -> bool:
        """You can add a channel or delete a channel.

        Args:
            action (Literal[&#39;add&#39;,&#39;del&#39;]): Action on the database
            module_name (str): The module name (mod_test)
            channel_name (str): The channel name (With #)

        Returns:
            bool: True if action done
        """
        try:
            channel_name = channel_name.lower() if self.Is_Channel(channel_name) else None
            core_table = 'core_channel'

            if not channel_name:
                self.logs.warn(f'The channel [{channel_name}] is not correct')
                return False

            match action:

                case 'add':
                    mes_donnees = {'module_name': module_name, 'channel_name': channel_name}
                    response = self.db_execute_query(f"SELECT id FROM {core_table} WHERE module_name = :module_name AND channel_name = :channel_name", mes_donnees)
                    isChannelExist = response.fetchone()

                    if isChannelExist is None:
                        mes_donnees = {'datetime': self.get_datetime(), 'channel_name': channel_name, 'module_name': module_name}
                        insert = self.db_execute_query(f"INSERT INTO {core_table} (datetime, channel_name, module_name) VALUES (:datetime, :channel_name, :module_name)", mes_donnees)
                        if insert.rowcount:
                            self.logs.debug(f'New channel added: channel={channel_name} / module_name={module_name}')
                            return True
                    else:
                        return False
                    pass

                case 'del':
                    mes_donnes = {'channel_name': channel_name, 'module_name': module_name}
                    response = self.db_execute_query(f"DELETE FROM {core_table} WHERE channel_name = :channel_name AND module_name = :module_name", mes_donnes)

                    if response.rowcount > 0:
                        self.logs.debug(f'Channel deleted: channel={channel_name} / module: {module_name}')
                        return True
                    else:
                        
                        return False

                case _:
                    return False

        except Exception as err:
            self.logs.error(err)

    def db_create_first_admin(self) -> None:

        user = self.db_execute_query(f"SELECT id FROM {self.Config.table_admin}")
        if not user.fetchall():
            admin = self.Config.OWNER
            password = self.crypt_password(self.Config.PASSWORD)

            mes_donnees = {'createdOn': self.get_datetime(), 
                           'user': admin, 
                           'password': password, 
                           'hostname': '*', 
                           'vhost': '*', 
                           'level': 5
                           }
            self.db_execute_query(f"""
                                  INSERT INTO {self.Config.table_admin} 
                                  (createdOn, user, password, hostname, vhost, level) 
                                  VALUES 
                                  (:createdOn, :user, :password, :hostname, :vhost, :level)"""
                                  , mes_donnees)

        return None

    def create_timer(self, time_to_wait: float, func: object, func_args: tuple = ()) -> None:

        try:
            t = threading.Timer(interval=time_to_wait, function=func, args=func_args)
            t.setName(func.__name__)
            t.start()

            self.running_timers.append(t)

            self.logs.debug(f"Timer ID : {str(t.ident)} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.logs.error(f'Assertion Error -> {ae}')

    def create_thread(self, func:object, func_args: tuple = (), run_once:bool = False, daemon: bool = True) -> None:
        """Create a new thread and store it into running_threads variable

        Args:
            func (object): The method/function you want to execute via this thread
            func_args (tuple, optional): Arguments of the function/method. Defaults to ().
            run_once (bool, optional): If you want to ensure that this method/function run once. Defaults to False.
        """
        try:
            func_name = func.__name__

            if run_once:
                for thread in self.running_threads:
                    if thread.getName() == func_name:
                        return None

            th = threading.Thread(target=func, args=func_args, name=str(func_name), daemon=daemon)
            th.start()

            self.running_threads.append(th)
            self.logs.debug(f"Thread ID : {str(th.ident)} | Thread name : {th.getName()} | Running Threads : {len(threading.enumerate())}")

        except AssertionError as ae:
            self.logs.error(f'{ae}')

    def garbage_collector_timer(self) -> None:
        """Methode qui supprime les timers qui ont finis leurs job
        """
        try:

            for timer in self.running_timers:
                if not timer.is_alive():
                    timer.cancel()
                    self.running_timers.remove(timer)
                    self.logs.info(f"Timer {str(timer)} removed")
                else:
                    self.logs.debug(f"===> Timer {str(timer)} Still running ...")

        except AssertionError as ae:
            self.logs.error(f'Assertion Error -> {ae}')

    def garbage_collector_thread(self) -> None:
        """Methode qui supprime les threads qui ont finis leurs job
        """
        try:
            for thread in self.running_threads:
                if thread.getName() != 'heartbeat':
                    if not thread.is_alive():
                        self.running_threads.remove(thread)
                        self.logs.info(f"Thread {str(thread.getName())} {str(thread.native_id)} removed")

            # print(threading.enumerate())
        except AssertionError as ae:
            self.logs.error(f'Assertion Error -> {ae}')

    def garbage_collector_sockets(self) -> None:

        for soc in self.running_sockets:
            while soc.fileno() != -1:
                self.logs.debug(soc.fileno())
                soc.close()

            soc.close()
            self.running_sockets.remove(soc)
            self.logs.debug(f"Socket ==> closed {str(soc.fileno())}")

    def shutdown(self) -> None:
        """Methode qui va préparer l'arrêt complêt du service
        """
        # Nettoyage des timers
        self.logs.debug(f"=======> Checking for Timers to stop")
        for timer in self.running_timers:
            while timer.is_alive():
                self.logs.debug(f"> waiting for {timer.getName()} to close")
                timer.cancel()
                time.sleep(0.2)
            self.running_timers.remove(timer)
            self.logs.debug(f"> Cancelling {timer.getName()} {timer.native_id}")

        self.logs.debug(f"=======> Checking for Threads to stop")
        for thread in self.running_threads:
            if thread.getName() == 'heartbeat' and thread.is_alive():
                self.execute_periodic_action()
                self.logs.debug(f"> Running the last periodic action")
            self.running_threads.remove(thread)
            self.logs.debug(f"> Cancelling {thread.getName()} {thread.native_id}")

        self.logs.debug(f"=======> Checking for Sockets to stop")
        for soc in self.running_sockets:
            soc.close()
            while soc.fileno() != -1:
                soc.close()

            self.running_sockets.remove(soc)
            self.logs.debug(f"> Socket ==> closed {str(soc.fileno())}")

        return None

    def db_init(self) -> tuple[Engine, Connection]:

        db_directory = self.Config.db_path
        full_path_db = self.Config.db_path + self.Config.db_name

        if not os.path.exists(db_directory):
            self.install = True
            os.makedirs(db_directory)

        engine = create_engine(f'sqlite:///{full_path_db}.db', echo=False)
        cursor = engine.connect()
        self.logs.info("database connexion has been initiated")
        return engine, cursor

    def __create_db(self) -> None:

        table_core_log = f'''CREATE TABLE IF NOT EXISTS {self.Config.table_log} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            ) 
        '''

        table_core_config = f'''CREATE TABLE IF NOT EXISTS {self.Config.table_config} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            module_name TEXT,
            param_key TEXT,
            param_value TEXT
            )
        '''

        table_core_log_command = f'''CREATE TABLE IF NOT EXISTS {self.Config.table_commande} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            user TEXT,
            commande TEXT
            )
        '''

        table_core_module = f'''CREATE TABLE IF NOT EXISTS {self.Config.table_module} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            user TEXT,
            module_name TEXT,
            isdefault INTEGER
            )
        '''
        
        table_core_channel = '''CREATE TABLE IF NOT EXISTS core_channel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            module_name TEXT,
            channel_name TEXT
            )
        '''

        table_core_admin = f'''CREATE TABLE IF NOT EXISTS {self.Config.table_admin} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            createdOn TEXT,
            user TEXT,
            hostname TEXT,
            vhost TEXT,
            password TEXT,
            level INTEGER
            )
        '''

        self.db_execute_query(table_core_log)
        self.db_execute_query(table_core_log_command)
        self.db_execute_query(table_core_module)
        self.db_execute_query(table_core_admin)
        self.db_execute_query(table_core_channel)
        self.db_execute_query(table_core_config)

        if self.install:
            self.db_record_module('sys', 'mod_command', 1)
            self.db_record_module('sys', 'mod_defender', 1)
            self.install = False

        return None

    def db_execute_query(self, query:str, params:dict = {}) -> CursorResult:

        with self.lock:
            insert_query = text(query)
            if not params:
                response = self.cursor.execute(insert_query)
            else:
                response = self.cursor.execute(insert_query, params)

            self.cursor.commit()

            return response

    def db_close(self) -> None:

        try:
            self.cursor.close()
        except AttributeError as ae:
            self.logs.error(f"Attribute Error : {ae}")

    def crypt_password(self, password:str) -> str:
        """Retourne un mot de passe chiffré en MD5

        Args:
            password (str): Le password en clair

        Returns:
            str: Le password en MD5
        """
        md5_password = hashlib.md5(password.encode()).hexdigest()

        return md5_password

    def int_if_possible(self, value):
        """Convertit la valeur reçue en entier, si possible.
        Sinon elle retourne la valeur initiale.

        Args:
            value (any): la valeur à convertir

        Returns:
            any: Retour un entier, si possible. Sinon la valeur initiale.
        """
        try:
            response = int(value)
            return response
        except ValueError:
            return value
        except TypeError:
            return value

    def is_valid_ip(self, ip_to_control:str) -> bool:

        try:
            if ip_to_control in self.Config.WHITELISTED_IP:
                return False

            ipaddress.ip_address(ip_to_control)
            return True
        except ValueError:
            return False

    def decode_ip(self, ip_b64encoded: str) -> Union[str, None]:

        binary_ip = b64decode(ip_b64encoded)
        try:
            decoded_ip = ipaddress.ip_address(binary_ip)

            return decoded_ip.exploded
        except ValueError as ve:
            self.logs.critical(f'This remote ip is not valid : {ve}')
            return None

    # def encode_ip(self, remote_ip_address: str) -> Union[str, None]:

    #     binary_ip = b64encode()
    #     try:
    #         decoded_ip = ipaddress.ip_address(binary_ip)

    #         return decoded_ip.exploded
    #     except ValueError as ve:
    #         self.logs.critical(f'This remote ip is not valid : {ve}')
    #         return None

    def get_random(self, lenght:int) -> str:
        """
        Retourn une chaîne aléatoire en fonction de la longueur spécifiée.
        """
        caracteres = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        randomize = ''.join(random.choice(caracteres) for _ in range(lenght))

        return randomize

    def execute_periodic_action(self) -> None:

        if not self.periodic_func:
            # Run Garbage Collector Timer
            self.garbage_collector_timer()
            self.garbage_collector_thread()
            # self.garbage_collector_sockets()
            return None

        for key, value in self.periodic_func.items():
            obj = value['object']
            method_name = value['method_name']
            param = value['param']
            f = getattr(obj, method_name, None)
            f(*param)

        # Vider le dictionnaire de fonction
        self.periodic_func.clear()

    def clean_uid(self, uid:str) -> str:
        """Clean UID by removing @ / % / + / ~ / * / :

        Args:
            uid (str): The UID to clean

        Returns:
            str: Clean UID without any sign
        """

        pattern = fr'[:|@|%|\+|~|\*]*'
        parsed_UID = re.sub(pattern, '', uid)

        return parsed_UID

    def Is_Channel(self, channelToCheck: str) -> bool:
        """Check if the string has the # caractere and return True if this is a channel

        Args:
            channelToCheck (str): The string to test if it is a channel or not

        Returns:
            bool: True if the string is a channel / False if this is not a channel
        """
        try:
            
            if channelToCheck is None:
                return False

            pattern = fr'^#'
            isChannel = re.findall(pattern, channelToCheck)

            if not isChannel:
                return False
            else:
                return True
        except TypeError as te:
            self.logs.error(f'TypeError: [{channelToCheck}] - {te}')
        except Exception as err:
            self.logs.error(f'Error Not defined: {err}')
