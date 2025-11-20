import asyncio
import os
import re
import json
import time
import socket
import threading
import ipaddress
import ast
import requests
from dataclasses import fields
from typing import Any, Callable, Iterable, Optional, TYPE_CHECKING
from base64 import b64decode, b64encode
from sqlalchemy import create_engine, Engine, Connection, CursorResult
from sqlalchemy.sql import text

if TYPE_CHECKING:
    from core.loader import Loader

class Base:

    def __init__(self, loader: 'Loader') -> None:

        self.Loader = loader
        self.Config = loader.Config
        self.Settings = loader.Settings
        self.Utils = loader.Utils
        self.logs = loader.Logs

        # Check if new Defender version is available
        self.check_for_new_version(True)

        # Liste des timers en cours
        self.running_timers: list[threading.Timer] = self.Settings.RUNNING_TIMERS

        # Liste des threads en cours
        self.running_threads: list[threading.Thread] = self.Settings.RUNNING_THREADS

        # List of all async tasks
        self.running_asynctasks: list[asyncio.Task] = self.Settings.RUNNING_ASYNCTASKS

        # Les sockets ouvert
        self.running_sockets: list[socket.socket] = self.Settings.RUNNING_SOCKETS

        # Liste des fonctions en attentes
        self.periodic_func: dict[object] = self.Settings.PERIODIC_FUNC

        # Init install variable
        self.install: bool = False
        
        # Init database connection
        self.engine, self.cursor = self.db_init()
        
        # Create the database
        # self.__create_db()

    async def init(self) -> None:
        await self.__create_db()

    def __set_current_defender_version(self) -> None:
        """This will put the current version of Defender
        located in version.json
        """

        version_filename = f'.{os.sep}version.json'
        with open(version_filename, 'r') as version_data:
            current_version:dict[str, str] = json.load(version_data)

        self.Config.CURRENT_VERSION = current_version['version']

        return None

    def __get_latest_defender_version(self) -> None:
        try:
            self.logs.debug(f'-- Looking for a new version available on Github')
            token = ''
            json_url = f'https://raw.githubusercontent.com/adator85/DEFENDER/main/version.json'
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
            self.Config.LATEST_VERSION = json_response['version']

            return None
        except requests.HTTPError as err:
            self.logs.error(f'Github not available to fetch latest version: {err}')
        except:
            self.logs.warning(f'Github not available to fetch latest version')

    def check_for_new_version(self, online:bool) -> bool:
        """Check if there is a new version available

        Args:
            online (bool): True if you want to get the version from github (main branch)

        Returns:
            bool: True if there is a new version available
        """
        try:
            self.logs.debug(f'-- Checking for a new service version')

            # Assigner la version actuelle de Defender
            self.__set_current_defender_version()
            # Récuperer la dernier version disponible dans github
            if online:
                self.logs.debug(f'-- Retrieve the latest version from Github')
                self.__get_latest_defender_version()

            isNewVersion = False
            latest_version = self.Config.LATEST_VERSION
            current_version = self.Config.CURRENT_VERSION

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
        except AttributeError as atterr:
            self.logs.error(f'Attribute Error: {atterr}')
        except Exception as err:
            self.logs.error(f'General Error: {err}')

    async def create_log(self, log_message: str) -> None:
        """Enregiste les logs

        Args:
            log_message (str): Le message a enregistrer

        Returns:
            None: Aucun retour
        """
        sql_insert = f"INSERT INTO {self.Config.TABLE_LOG} (datetime, server_msg) VALUES (:datetime, :server_msg)"
        mes_donnees = {'datetime': str(self.Utils.get_sdatetime()),'server_msg': f'{log_message}'}
        await self.db_execute_query(sql_insert, mes_donnees)

        return None

    async def log_cmd(self, user_cmd: str, cmd: str) -> None:
        """Enregistre les commandes envoyées par les utilisateurs

        Args:
            user_cmd (str): The user who performed the command
            cmd (str): la commande a enregistrer
        """
        cmd_list = cmd.split()
        if len(cmd_list) == 3:
            if cmd_list[0].replace(self.Config.SERVICE_PREFIX, '') == 'auth':
                cmd_list[1] = '*******'
                cmd_list[2] = '*******'
                cmd = ' '.join(cmd_list)

        insert_cmd_query = f"INSERT INTO {self.Config.TABLE_COMMAND} (datetime, user, commande) VALUES (:datetime, :user, :commande)"
        mes_donnees = {'datetime': self.Utils.get_sdatetime(), 'user': user_cmd, 'commande': cmd}
        await self.db_execute_query(insert_cmd_query, mes_donnees)

        return None

    async def db_sync_core_config(self, module_name: str, dataclassObj: object) -> bool:
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
            current_date = self.Utils.get_sdatetime()
            core_table = self.Config.TABLE_CONFIG

            # Add local parameters to DB
            for field in fields(dataclassObj):
                param_key = field.name
                param_value = str(getattr(dataclassObj, field.name))

                param_to_search = {'module_name': module_name, 'param_key': param_key}

                search_query = f'''SELECT id FROM {core_table} WHERE module_name = :module_name AND param_key = :param_key'''
                excecute_search_query = await self.db_execute_query(search_query, param_to_search)
                result_search_query = excecute_search_query.fetchone()

                if result_search_query is None:
                    # If param and module_name doesn't exist create the record
                    param_to_insert = {'datetime': current_date,'module_name': module_name,
                                       'param_key': param_key,'param_value': param_value
                                    }

                    insert_query = f'''INSERT INTO {core_table} (datetime, module_name, param_key, param_value) 
                                        VALUES (:datetime, :module_name, :param_key, :param_value)
                                        '''
                    execution = await self.db_execute_query(insert_query, param_to_insert)

                    if execution.rowcount > 0:
                        self.logs.debug(f'New parameter added to the database: {param_key} --> {param_value}')

            # Delete from DB unused parameter
            query_select = f"SELECT module_name, param_key, param_value FROM {core_table} WHERE module_name = :module_name"
            parameter = {'module_name': module_name}
            execute_query_select = await self.db_execute_query(query_select, parameter)
            result_query_select = execute_query_select.fetchall()

            for result in result_query_select:
                db_mod_name, db_param_key, db_param_value = result
                if not hasattr(dataclassObj, db_param_key):
                    mes_donnees = {'param_key': db_param_key, 'module_name': db_mod_name}
                    execute_delete = await self.db_execute_query(f'DELETE FROM {core_table} WHERE module_name = :module_name and param_key = :param_key', mes_donnees)
                    row_affected = execute_delete.rowcount
                    if row_affected > 0:
                        self.logs.debug(f'A parameter has been deleted from the database: {db_param_key} --> {db_param_value} | Mod: {db_mod_name}')

            # Sync local variable with Database
            query = f"SELECT param_key, param_value FROM {core_table} WHERE module_name = :module_name"
            parameter = {'module_name': module_name}
            response = await self.db_execute_query(query, parameter)
            result = response.fetchall()

            for param, value in result:
                if isinstance(getattr(dataclassObj, param), list):
                    value = ast.literal_eval(value)

                setattr(dataclassObj, param, self.int_if_possible(value))

            return response

        except AttributeError as attrerr:
            self.logs.error(f'Attribute Error: {attrerr}')
        except Exception as err:
            self.logs.error(err)
            return False

    async def db_update_core_config(self, module_name:str, dataclass_obj: object, param_key:str, param_value: str) -> bool:

        core_table = self.Config.TABLE_CONFIG
        # Check if the param exist
        if not hasattr(dataclass_obj, param_key):
            self.logs.error(f"Le parametre {param_key} n'existe pas dans la variable global")
            return False

        mes_donnees = {'module_name': module_name, 'param_key': param_key, 'param_value': param_value}
        search_param_query = f"SELECT id FROM {core_table} WHERE module_name = :module_name AND param_key = :param_key"
        result = await self.db_execute_query(search_param_query, mes_donnees)
        is_param_exist = result.fetchone()

        if not is_param_exist is None:
            mes_donnees = {'datetime': self.Utils.get_sdatetime(),
                           'module_name': module_name,
                           'param_key': param_key,
                           'param_value': param_value
                           }
            query = f'''UPDATE {core_table} SET datetime = :datetime, param_value = :param_value WHERE module_name = :module_name AND param_key = :param_key'''
            update = await self.db_execute_query(query, mes_donnees)
            updated_rows = update.rowcount
            if updated_rows > 0:
                setattr(dataclass_obj, param_key, self.int_if_possible(param_value))
                self.logs.debug(f'Parameter updated : {param_key} - {param_value} | Module: {module_name}')
            else:
                self.logs.error(f'Parameter NOT updated : {param_key} - {param_value} | Module: {module_name}')
        else:
            self.logs.error(f'Parameter and Module do not exist: Param ({param_key}) - Value ({param_value}) | Module ({module_name})')

        self.logs.debug(dataclass_obj)

        return True

    async def db_create_first_admin(self) -> None:

        user = await self.db_execute_query(f"SELECT id FROM {self.Config.TABLE_ADMIN}")
        if not user.fetchall():
            admin = self.Config.OWNER
            password = self.Utils.hash_password(self.Config.PASSWORD)

            mes_donnees = {'createdOn': self.Utils.get_sdatetime(), 
                           'user': admin, 
                           'password': password, 
                           'hostname': '*', 
                           'vhost': '*', 
                           'language': 'EN',
                           'level': 5
                           }
            await self.db_execute_query(f"""
                                  INSERT INTO {self.Config.TABLE_ADMIN} 
                                  (createdOn, user, password, hostname, vhost, language, level) 
                                  VALUES 
                                  (:createdOn, :user, :password, :hostname, :vhost, :language, :level)"""
                                  , mes_donnees)

        return None

    def create_timer(self, time_to_wait: float, func: object, func_args: tuple = ()) -> None:

        try:
            t = threading.Timer(interval=time_to_wait, function=func, args=func_args)
            t.name = func.__name__
            t.start()

            self.running_timers.append(t)

            self.logs.debug(f"-- Timer ID : {str(t.ident)} | Running Threads : {len(threading.enumerate())}")

            return None

        except AssertionError as ae:
            self.logs.error(f'Assertion Error -> {ae}')
            return None

    def create_thread(self, func: object, func_args: tuple = (), run_once: bool = False, daemon: bool = True) -> None:
        """Create a new thread and store it into running_threads variable

        Args:
            func (object): The method/function you want to execute via this thread
            func_args (tuple, optional): Arguments of the function/method. Defaults to ().
            run_once (bool, optional): If you want to ensure that this method/function run once. Defaults to False.
        """
        try:
            # Clean unused threads first
            self.garbage_collector_thread()

            func_name = func.__name__

            if run_once:
                for thread in self.running_threads:
                    if thread.name == func_name:
                        return None

            th = threading.Thread(target=func, args=func_args, name=str(func_name), daemon=daemon)
            th.start()

            self.running_threads.append(th)
            self.logs.debug(f"-- Thread ID : {str(th.ident)} | Thread name : {th.name} | Running Threads : {len(threading.enumerate())}")

        except Exception as err:
            self.logs.error(err, exc_info=True)

    def create_asynctask(self, func: Any, *, async_name: str = None, run_once: bool = False) -> asyncio.Task:
        """Create a new asynchrone and store it into running_asynctasks variable

        Args:
            func (Callable): The function you want to call in asynchrone way
            async_name (str, optional): The task name. Defaults to None.
            run_once (bool, optional): If true the task will be run once. Defaults to False.

        Returns:
            asyncio.Task: The Task
        """
        name = func.__name__ if async_name is None else async_name

        if run_once:
            for task in asyncio.all_tasks():
                if task.get_name().lower() == async_name.lower():
                    return None

        task = asyncio.create_task(func, name=name)
        task.add_done_callback(self.asynctask_done)
        self.running_asynctasks.append(task)

        self.logs.debug(f"++ New asynchrone task created as: {task.get_name()}")
        return task

    def asynctask_done(self, task: asyncio.Task):
        """Log task when done

        Args:
            task (asyncio.Task): The Asyncio Task callback
        """
        try:
            if task.exception():
                self.logs.error(f"[ASYNCIO] Task {task.get_name()} failed with exception: {task.exception()}")
            else:
                self.logs.debug(f"[ASYNCIO] Task {task.get_name()} completed successfully.")
        except asyncio.CancelledError as ce:
            self.logs.debug(f"[ASYNCIO] Task {task.get_name()} terminated with cancelled error.")
        except asyncio.InvalidStateError as ie:
            self.logs.debug(f"[ASYNCIO] Task {task.get_name()} terminated with invalid state error.")

    def is_thread_alive(self, thread_name: str) -> bool:
        """Check if the thread is still running! using the is_alive method of Threads.

        Args:
            thread_name (str): The thread name

        Returns:
            bool: True if is alive
        """
        for thread in self.running_threads:
            if thread.name.lower() == thread_name.lower():
                if thread.is_alive():
                    return True
                else:
                    return False

        return False

    def is_thread_exist(self, thread_name: str) -> bool:
        """Check if the thread exist in the local var (running_threads)

        Args:
            thread_name (str): The thread name

        Returns:
            bool: True if the thread exist
        """
        for thread in self.running_threads:
            if thread.name.lower() == thread_name.lower():
                    return True

        return False

    def thread_count(self, thread_name: str) -> int:
        """This method return the number of existing threads 
        currently running or not running

        Args:
            thread_name (str): The name of the thread

        Returns:
            int: Number of threads
        """
        with self.Settings.LOCK:
            count = 0

            for thr in self.running_threads:
                if thread_name == thr.name:
                    count += 1

            return count

    def garbage_collector_timer(self) -> None:
        """Methode qui supprime les timers qui ont finis leurs job
        """
        try:
            for timer in self.running_timers:
                if not timer.is_alive():
                    timer.cancel()
                    self.running_timers.remove(timer)
                    self.logs.debug(f"-- Timer {str(timer)} removed")
                else:
                    self.logs.debug(f"--* Timer {str(timer)} Still running ...")

        except AssertionError as ae:
            self.logs.error(f'Assertion Error -> {ae}')

    def garbage_collector_thread(self) -> None:
        """Methode qui supprime les threads qui ont finis leurs job
        """
        try:
            for thread in self.running_threads:
                if thread.name != 'heartbeat':
                    if not thread.is_alive():
                        self.running_threads.remove(thread)
                        self.logs.debug(f"-- Thread {str(thread.name)} {str(thread.native_id)} has been removed!")

            # print(threading.enumerate())
        except Exception as err:
            self.logs.error(err, exc_info=True)

    def garbage_collector_sockets(self) -> None:

        for soc in self.running_sockets:
            while soc.fileno() != -1:
                self.logs.debug(soc.fileno())
                soc.close()

            soc.close()
            self.running_sockets.remove(soc)
            self.logs.debug(f"-- Socket ==> closed {str(soc.fileno())}")

    async def shutdown(self) -> None:
        """Methode qui va préparer l'arrêt complêt du service
        """
        # unload modules.
        self.logs.debug(f"=======> Unloading all modules!")
        for module in self.Loader.ModuleUtils.model_get_loaded_modules().copy():
            await self.Loader.ModuleUtils.unload_one_module(module.module_name)

        # Nettoyage des timers
        self.logs.debug(f"=======> Checking for Timers to stop")
        for timer in self.running_timers:
            while timer.is_alive():
                self.logs.debug(f"> waiting for {timer.name} to close")
                timer.cancel()
                time.sleep(0.2)
            self.running_timers.remove(timer)
            self.logs.debug(f"> Cancelling {timer.name} {timer.native_id}")

        self.logs.debug(f"=======> Checking for Threads to stop")
        for thread in self.running_threads:
            if thread.name == 'heartbeat' and thread.is_alive():
                self.execute_periodic_action()
                self.logs.debug(f"> Running the last periodic action")
            self.running_threads.remove(thread)
            self.logs.debug(f"> Cancelling {thread.name} {thread.native_id}")

        self.logs.debug(f"=======> Checking for Sockets to stop")
        for soc in self.running_sockets:
            soc.close()
            while soc.fileno() != -1:
                soc.close()

            self.running_sockets.remove(soc)
            self.logs.debug(f"> Socket ==> closed {str(soc.fileno())}")

        await self.Loader.RpcServer.stop_server()

        self.db_close()

        return None

    def db_init(self) -> tuple[Engine, Connection]:

        db_directory = self.Config.DB_PATH
        full_path_db = self.Config.DB_PATH + self.Config.DB_NAME

        if not os.path.exists(db_directory):
            self.install = True
            os.makedirs(db_directory)

        engine = create_engine(f'sqlite:///{full_path_db}.db', echo=False)
        cursor = engine.connect()
        self.logs.info("-- Database connexion has been initiated")
        return engine, cursor

    async def __create_db(self) -> None:

        table_core_log = f'''CREATE TABLE IF NOT EXISTS {self.Config.TABLE_LOG} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            ) 
        '''

        table_core_config = f'''CREATE TABLE IF NOT EXISTS {self.Config.TABLE_CONFIG} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            module_name TEXT,
            param_key TEXT,
            param_value TEXT
            )
        '''

        table_core_log_command = f'''CREATE TABLE IF NOT EXISTS {self.Config.TABLE_COMMAND} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            user TEXT,
            commande TEXT
            )
        '''

        table_core_module = f'''CREATE TABLE IF NOT EXISTS {self.Config.TABLE_MODULE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            user TEXT,
            module_name TEXT,
            isdefault INTEGER
            )
        '''
        
        table_core_channel = f'''CREATE TABLE IF NOT EXISTS {self.Config.TABLE_CHANNEL} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            module_name TEXT,
            channel_name TEXT
            )
        '''

        table_core_admin = f'''CREATE TABLE IF NOT EXISTS {self.Config.TABLE_ADMIN} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            createdOn TEXT,
            user TEXT,
            hostname TEXT,
            vhost TEXT,
            password TEXT,
            fingerprint TEXT,
            language TEXT,
            level INTEGER
            )
        '''

        table_core_client = f'''CREATE TABLE IF NOT EXISTS {self.Config.TABLE_CLIENT} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            createdOn TEXT,
            account TEXT,
            nickname TEXT,
            hostname TEXT,
            vhost TEXT,
            realname TEXT,
            email TEXT,
            password TEXT,
            level INTEGER
            )
        '''

        await self.db_execute_query(table_core_log)
        await self.db_execute_query(table_core_log_command)
        await self.db_execute_query(table_core_module)
        await self.db_execute_query(table_core_admin)
        await self.db_execute_query(table_core_client)
        await self.db_execute_query(table_core_channel)
        await self.db_execute_query(table_core_config)

        # Patch database
        await self.db_patch(self.Config.TABLE_ADMIN, "language", "TEXT")

        if self.install:
            await self.Loader.ModuleUtils.db_register_module('mod_command', 'sys', True)
            await self.Loader.ModuleUtils.db_register_module('mod_defender', 'sys', True)
            self.install = False

        return None

    async def db_execute_query(self, query:str, params:dict = {}) -> CursorResult:

        async with self.Loader.Settings.AILOCK:
            insert_query = text(query)
            if not params:
                response = self.cursor.execute(insert_query)
            else:
                response = self.cursor.execute(insert_query, params)

            self.cursor.commit()

            return response

    async def db_is_column_exist(self, table_name: str, column_name: str) -> bool:
        q = await self.db_execute_query(f"PRAGMA table_info({table_name})")
        existing_columns = [col[1] for col in q.fetchall()]

        if column_name in existing_columns:
            return True
        else:
            return False

    async def db_patch(self, table_name: str, column_name: str, column_type: str) -> bool:
        if not await self.db_is_column_exist(table_name, column_name):
            patch = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            update_row = f"UPDATE {table_name} SET language = 'EN' WHERE language is null"
            await self.db_execute_query(patch)
            await self.db_execute_query(update_row)
            self.logs.debug(f"The patch has been applied")
            self.logs.debug(f"Table name: {table_name}, Column name: {column_name}, Column type: {column_type}")
            return True
        else:
            return False

    def db_close(self) -> None:
        try:
            self.cursor.close()
            self.logs.debug("Database engine closed!")
        except AttributeError as ae:
            self.logs.error(f"Attribute Error : {ae}")

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

    def convert_to_int(self, value: Any) -> Optional[int]:
        """Convert a value to int

        Args:
            value (any): Value to convert to int if possible

        Returns:
            int: Return the int value or None if not possible
        """
        try:
            response = int(value)
            return response
        except ValueError:
            return None
        except TypeError:
            return None

    def is_valid_ip(self, ip_to_control: str) -> bool:

        try:
            if ip_to_control in self.Config.WHITELISTED_IP:
                return False

            ipaddress.ip_address(ip_to_control)
            return True
        except ValueError:
            return False

    def is_valid_email(self, email_to_control: str) -> bool:
        """Check if the email is valid

        Args:
            email_to_control (str): email to control

        Returns:
            bool: True is the email is correct
        """
        try:
            pattern = '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if re.match(pattern, email_to_control):
                return True
            else:
                return False

        except Exception as err:
            self.logs.error(f'General Error: {err}')
            return False

    def decode_ip(self, ip_b64encoded: str) -> Optional[str]:
        try:
            binary_ip = b64decode(ip_b64encoded)
            decoded_ip = ipaddress.ip_address(binary_ip)

            return decoded_ip.exploded
        except ValueError as ve:
            self.logs.critical(f'This remote ip ({ip_b64encoded}) is not valid : {ve}')
            return None

    def encode_ip(self, remote_ip_address: str) -> Optional[str]:

        binary_ip = socket.inet_aton(remote_ip_address)
        try:
            encoded_ip = b64encode(binary_ip).decode()

            return encoded_ip
        except ValueError as ve:
            self.logs.critical(f'This remote ip is not valid : {ve}')
            return None
        except Exception as err:
            self.logs.critical(f'General Error: {err}')
            return None

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

    def execute_dynamic_method(self, obj: object, method_name: str, params: list) -> None:
        """#### Ajouter les méthodes a éxecuter dans un dictionnaire
        Les methodes seront exécuter par heartbeat.

        Args:
            obj (object): Une instance de la classe qui va etre executer
            method_name (str): Le nom de la méthode a executer
            params (list): les parametres a faire passer

        Returns:
            None: aucun retour attendu
        """
        self.periodic_func[len(self.periodic_func) + 1] = {
            'object': obj,
            'method_name': method_name,
            'param': params
            }

        self.logs.debug(f'Method to execute : {str(self.periodic_func)}')
        return None
