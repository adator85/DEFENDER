import socket
import json
import time
import re
import psutil
import requests
from dataclasses import dataclass
from datetime import datetime
from typing import Union, TYPE_CHECKING
from core.classes import user
import core.definition as df

if TYPE_CHECKING:
    from core.irc import Irc


class Nickserv():

    @dataclass
    class ModConfModel:
        active: bool = False

    def __init__(self, ircInstance: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = ircInstance

        # Add Loader Object to the module (Mandatory)
        self.Loader = ircInstance.Loader

        # Add server protocol Object to the module (Mandatory)
        self.Protocol = ircInstance.Protocol

        # Add Global Configuration to the module (Mandatory)
        self.Config = ircInstance.Config

        # Add Base object to the module (Mandatory)
        self.Base = ircInstance.Base

        # Add logs object to the module (Mandatory)
        self.Logs = ircInstance.Base.logs

        # Add User object to the module (Mandatory)
        self.User = ircInstance.User

        # Add Client object to the module (Mandatory)
        self.Client = ircInstance.Client

        # Add Channel object to the module (Mandatory)
        self.Channel = ircInstance.Channel

        # Add Reputation object to the module (Optional)
        self.Reputation = ircInstance.Reputation

        # Check if NickServ already exist
        # for user_obj in self.User.UID_DB:
        #     if user_obj.nickname.lower() == 'nickserv':
        #         self.Logs.warning(f"The NickServ service already exist, impossible to load 2 NickServ services")
        #         return None

        # Create module commands (Mandatory)
        self.Irc.build_command(0, self.module_name, 'register', f'Register your nickname /msg NickServ REGISTER <password> <email>')
        self.Irc.build_command(0, self.module_name, 'identify', f'Identify yourself with your password /msg NickServ IDENTIFY <account> <password>')
        self.Irc.build_command(0, self.module_name, 'logout', 'Reverse the effect of the identify command')

        # Init the module (Mandatory)
        self.__init_module()

        # Log the module
        self.Logs.debug(f'-- Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Create you own tables if needed (Mandatory)
        self.__create_tables()

        # Load module configuration (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

        self.build_nickserv_information()

        return None

    def __create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """

        # table_autoop = '''CREATE TABLE IF NOT EXISTS defender_autoop (
        #     id INTEGER PRIMARY KEY AUTOINCREMENT,
        #     datetime TEXT,
        #     nickname TEXT,
        #     channel TEXT
        #     )
        # '''

        # self.Base.db_execute_query(table_autoop)
        # self.Base.db_execute_query(table_config)
        # self.Base.db_execute_query(table_trusted)
        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Variable qui va contenir les options de configuration du module Defender
            self.ModConfig = self.ModConfModel(active=True)

            # Sync the configuration with core configuration (Mandatory)
            self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def __update_configuration(self, param_key: str, param_value: str):

        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    def build_nickserv_information(self) -> None:

        self.NICKSERV_NICKNAME = 'NickServ'

        if self.User.is_exist(self.NICKSERV_NICKNAME):
            # If NickServ already exist just return None
            self.NICKSERV_UID = self.User.get_uid(self.NICKSERV_NICKNAME)
            self.Irc.Settings.NICKSERV_UID = self.NICKSERV_UID
            return None

        self.NICKSERV_UID = self.Config.SERVEUR_ID + self.Base.get_random(6)
        nickserv_uid = self.NICKSERV_UID
        self.Irc.Settings.NICKSERV_UID = self.NICKSERV_UID

        self.Protocol.send_uid(
            nickname=self.NICKSERV_NICKNAME, username='NickServ', hostname='nickserv.deb.biz.st', uid=nickserv_uid, umodes='+ioqBS', 
            vhost='nickserv.deb.biz.st', remote_ip='127.0.0.1', realname='Nick Service'
        )

        new_user_obj = self.Loader.Definition.MUser(uid=nickserv_uid, nickname=self.NICKSERV_NICKNAME, username='NickServ', realname='Nick Service',
                                                    hostname='nickserv.deb.biz.st', umodes='+ioqBS', vhost='nickserv.deb.biz.st', remote_ip='127.0.0.1')

        self.User.insert(new_user_obj)
        self.Protocol.send_sjoin(nickserv_uid, self.Config.SERVICE_CHANLOG)
        return None

    def timer_force_change_nickname(self, nickname: str) -> None:

        client_obj = self.Client.get_Client(nickname)

        if client_obj is None:
            self.Protocol.send_svs_nick(nickname, self.Base.get_random(8))

        return None

    def unload(self, reloading: bool = False) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """
        if reloading:
            pass
        else:
            # NickServ will be disconnected
            self.Protocol.send_quit(self.NICKSERV_UID, f'Stopping {self.module_name} module')

            del self.NICKSERV_NICKNAME
            del self.NICKSERV_UID

        return None

    def cmd(self, data: list[str]) -> None:
        try:
            service_id = self.Config.SERVICE_ID                 # Defender serveur id
            original_serv_response = list(data).copy()

            parsed_protocol = self.Protocol.parse_server_msg(data.copy())

            match parsed_protocol:

                case 'UID':
                    try:
                        # ['@...', ':001', 'UID', 'adator', '0', '1733865747', '...', '192.168.1.10', '00118YU01', '0', '+iotwxz', 'netadmin.irc.dev.local', '745A32E5.421A4718.F33AB65A.IP', 'wKgBCg==', ':...']
                        get_uid = str(original_serv_response[8])
                        user_obj = self.User.get_User(get_uid)
                        self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=user_obj.nickname,
                            msg='NickServ is here to protect your nickname'
                        )
                        self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=user_obj.nickname,
                            msg='To register a nickname tape /msg NickServ register password email'
                        )

                        if self.Client.db_is_account_exist(user_obj.nickname):
                            self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=user_obj.nickname, msg='The nickname is protected please login to keep it')
                            self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=user_obj.nickname, msg=f'/msg {self.NICKSERV_NICKNAME} IDENTIFY <ACCOUNT> <PASSWORD>')
                            self.Base.create_timer(60, self.timer_force_change_nickname, (user_obj.nickname, ))

                    except IndexError as ie:
                        self.Logs.error(f'cmd reputation: index error: {ie}')

                case None:
                    self.Logs.debug(f"** TO BE HANDLE {original_serv_response} {__name__}")

        except KeyError as ke:
            self.Logs.error(f"{ke} / {original_serv_response} / length {str(len(original_serv_response))}")
        except IndexError as ie:
            self.Logs.error(f"{ie} / {original_serv_response} / length {str(len(original_serv_response))}")
        except Exception as err:
            self.Logs.error(f"General Error: {err}")

    def hcmds(self, user: str, channel: str, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        fromuser = user
        fromchannel = channel if self.Channel.Is_Channel(channel) else None
        dnickname = self.Config.SERVICE_NICKNAME            # Defender nickname
        dchanlog = self.Config.SERVICE_CHANLOG              # Defender chan log
        dumodes = self.Config.SERVICE_UMODES                # Les modes de Defender
        service_id = self.Config.SERVICE_ID                 # Defender serveur id

        match command:

            case 'register':
                # Register PASSWORD EMAIL
                try:

                    if len(cmd) < 3:
                        self.Protocol.send_notice(
                            nick_from=self.NICKSERV_NICKNAME,
                            nick_to=fromuser,
                            msg=f'/msg {self.NICKSERV_NICKNAME} {command.upper()} <PASSWORD> <EMAIL>'
                        )
                        return None

                    password = cmd[1]
                    email = cmd[2]

                    if not self.Base.is_valid_email(email_to_control=email):
                        self.Protocol.send_notice(
                            nick_from=self.NICKSERV_NICKNAME,
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
                            nick_from=self.NICKSERV_NICKNAME,
                            nick_to=fromuser,
                            msg=f"Your account already exist, please try to login instead /msg {self.NICKSERV_NICKNAME} IDENTIFY <account> <password>"
                        )
                        return None

                    # If the account doesn't exist then insert into database
                    data_to_record = {
                        'createdOn': self.Base.get_datetime(), 'account': fromuser,
                        'nickname': user_obj.nickname, 'hostname': user_obj.hostname, 'vhost': user_obj.vhost, 'realname': user_obj.realname, 'email': email,
                        'password': self.Base.crypt_password(password=password), 'level': 0
                    }

                    insert_to_db = self.Base.db_execute_query(f"""
                                                            INSERT INTO {self.Config.TABLE_CLIENT} 
                                                            (createdOn, account, nickname, hostname, vhost, realname, email, password, level)
                                                            VALUES
                                                            (:createdOn, :account, :nickname, :hostname, :vhost, :realname, :email, :password, :level)
                                                            """, data_to_record)

                    if insert_to_db.rowcount > 0:
                        self.Protocol.send_notice(
                            nick_from=self.NICKSERV_NICKNAME,
                            nick_to=fromuser,
                            msg=f"You have register your nickname successfully"
                        )

                    return None

                except ValueError as ve:
                    self.Logs.error(f"Value Error : {ve}")
                    self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg=f" {self.Config.SERVICE_PREFIX}{command.upper()} <PASSWORD> <EMAIL>")

            case 'identify':
                try:
                    # IDENTIFY <ACCOUNT> <PASSWORD>
                    if len(cmd) < 3:
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f'/msg {self.NICKSERV_NICKNAME} {command.upper()} <ACCOUNT> <PASSWORD>'
                        )
                        return None

                    account = str(cmd[1]) # account
                    encrypted_password = self.Base.crypt_password(cmd[2])
                    user_obj = self.User.get_User(fromuser)
                    client_obj = self.Client.get_Client(user_obj.uid)

                    if client_obj is not None:
                        self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg=f"You are already logged in")
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
                        self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg=f"You are now logged in")
                        user_obj_dict = self.User.get_User_AsDict(fromuser)
                        client = self.Loader.Definition.MClient(
                            account=account,
                            **user_obj_dict
                        )
                        self.Client.insert(client)
                        self.Protocol.send_svs2mode(service_uid=self.NICKSERV_UID, nickname=fromuser, user_mode='+r')
                    else:
                        self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg=f"Wrong password or account")
                except TypeError as te:
                    self.Logs.error(f"Type Error -> {te}")
                except ValueError as ve:
                    self.Logs.error(f"Value Error -> {ve}")

            case 'logout':
                try:
                    # LOGOUT <account>
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg=f"/msg {self.NICKSERV_NICKNAME} {command.upper()} <ACCOUNT>")
                        return None

                    user_obj = self.User.get_User(fromuser)
                    if user_obj is None:
                        self.Logs.error(f"The User [{fromuser}] is not available in the database")
                        return None

                    client_obj = self.Client.get_Client(user_obj.uid)

                    if client_obj is None:
                        self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg="Nothing to logout. please login first")
                        return None

                    self.Protocol.send_svs2mode(service_uid=self.NICKSERV_UID, nickname=fromuser, user_mode='-r')
                    self.Client.delete(user_obj.uid)
                    self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg=f"You have been logged out successfully")

                except ValueError as ve:
                    self.Logs.error(f"Value Error: {ve}")
                    self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg=f"/msg {self.NICKSERV_NICKNAME} {command.upper()} <account>")
                except Exception as err:
                    self.Logs.error(f"General Error: {err}")
                    self.Protocol.send_notice(nick_from=self.NICKSERV_NICKNAME, nick_to=fromuser, msg=f"/msg {self.NICKSERV_NICKNAME} {command.upper()} <account>")
