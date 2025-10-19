from base64 import b64decode
from re import match, findall, search
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from ssl import SSLEOFError, SSLError

from core.classes.protocols.command_handler import CommandHandler
from core.classes.protocols.interface import IProtocol
from core.utils import tr

if TYPE_CHECKING:
    from core.irc import Irc
    from core.classes.sasl import Sasl
    from core.definition import MClient, MSasl

class Unrealircd6(IProtocol):

    def  __init__(self, ircInstance: 'Irc'):
        self.name = 'UnrealIRCD-6'
        self.protocol_version = 6100

        self.__Irc = ircInstance
        self.__Config = ircInstance.Config
        self.__Base = ircInstance.Base
        self.__Settings = ircInstance.Base.Settings
        self.__Utils = ircInstance.Loader.Utils
        self.__Logs = ircInstance.Loader.Logs

        self.known_protocol: set[str] = {'SJOIN', 'UID', 'MD', 'QUIT', 'SQUIT',
                               'EOS', 'PRIVMSG', 'MODE', 'UMODE2', 
                               'VERSION', 'REPUTATION', 'SVS2MODE', 
                               'SLOG', 'NICK', 'PART', 'PONG', 'SASL', 'PING',
                               'PROTOCTL', 'SERVER', 'SMOD', 'TKL', 'NETINFO',
                               '006', '007', '018'}

        self.Handler = CommandHandler(ircInstance.Loader)

        self.__Logs.info(f"[PROTOCOL] Protocol [{__name__}] loaded!")

    def get_ircd_protocol_poisition(self, cmd: list[str], log: bool = False) -> tuple[int, Optional[str]]:
        """Get the position of known commands

        Args:
            cmd (list[str]): The server response
            log (bool): If true it will log in the logger

        Returns:
            tuple[int, Optional[str]]: The position and the command.
        """
        for index, token in enumerate(cmd):
            if token.upper() in self.known_protocol:
                return index, token.upper()
        
        if log:
            self.__Logs.debug(f"[IRCD LOGS] You need to handle this response: {cmd}")

        return (-1, None)

    def register_command(self) -> None:
        m = self.__Irc.Loader.Definition.MIrcdCommand
        self.Handler.register(m(command_name="PING", func=self.on_server_ping))
        self.Handler.register(m(command_name="UID", func=self.on_uid))
        self.Handler.register(m(command_name="QUIT", func=self.on_quit))
        self.Handler.register(m(command_name="SERVER", func=self.on_server))
        self.Handler.register(m(command_name="SJOIN", func=self.on_sjoin))
        self.Handler.register(m(command_name="EOS", func=self.on_eos))
        self.Handler.register(m(command_name="PROTOCTL", func=self.on_protoctl))
        self.Handler.register(m(command_name="SVS2MODE", func=self.on_svs2mode))
        self.Handler.register(m(command_name="SQUIT", func=self.on_squit))
        self.Handler.register(m(command_name="PART", func=self.on_part))
        self.Handler.register(m(command_name="VERSION", func=self.on_version_msg))
        self.Handler.register(m(command_name="UMODE2", func=self.on_umode2))
        self.Handler.register(m(command_name="NICK", func=self.on_nick))
        self.Handler.register(m(command_name="REPUTATION", func=self.on_reputation))
        self.Handler.register(m(command_name="SMOD", func=self.on_smod))
        self.Handler.register(m(command_name="SASL", func=self.on_sasl))
        self.Handler.register(m(command_name="MD", func=self.on_md))
        self.Handler.register(m(command_name="PRIVMSG", func=self.on_privmsg))

        return None

    def parse_server_msg(self, server_msg: list[str]) -> Optional[str]:
        """Parse the server message and return the command

        Args:
            server_msg (list[str]): The Original server message >>

        Returns:
            Union[str, None]: Return the command protocol name
        """
        protocol_exception = ['PING', 'SERVER', 'PROTOCTL']
        increment = 0
        server_msg_copy = server_msg.copy()
        first_index = 0
        second_index = 0
        for index, element in enumerate(server_msg_copy):
            # Handle the protocol exceptions ex. ping, server ....
            if element in protocol_exception and index == 0:
                return element

            if element.startswith(':'):
                increment += 1
                first_index = index + 1 if increment == 1 else first_index
                second_index = index if increment == 2 else second_index

        second_index = len(server_msg_copy) if second_index == 0 else second_index

        parsed_msg = server_msg_copy[first_index:second_index]

        for cmd in parsed_msg:
            if cmd in self.known_protocol:
                return cmd

        return None

    def send2socket(self, message: str, print_log: bool = True) -> None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            string (Str): contient la commande à envoyer au serveur.
        """
        try:
            with self.__Base.lock:
                self.__Irc.IrcSocket.send(f"{message}\r\n".encode(self.__Config.SERVEUR_CHARSET[0]))
                if print_log:
                    self.__Logs.debug(f'<< {message}')

        except UnicodeDecodeError as ude:
            self.__Logs.error(f'Decode Error try iso-8859-1 - {ude} - {message}')
            self.__Irc.IrcSocket.send(f"{message}\r\n".encode(self.__Config.SERVEUR_CHARSET[1],'replace'))
        except UnicodeEncodeError as uee:
            self.__Logs.error(f'Encode Error try iso-8859-1 - {uee} - {message}')
            self.__Irc.IrcSocket.send(f"{message}\r\n".encode(self.__Config.SERVEUR_CHARSET[1],'replace'))
        except AssertionError as ae:
            self.__Logs.warning(f'Assertion Error {ae} - message: {message}')
        except SSLEOFError as soe:
            self.__Logs.error(f"SSLEOFError: {soe} - {message}")
        except SSLError as se:
            self.__Logs.error(f"SSLError: {se} - {message}")
        except OSError as oe:
            self.__Logs.error(f"OSError: {oe} - {message}")
        except AttributeError as ae:
            self.__Logs.critical(f"Attribute Error: {ae}")

    def send_priv_msg(self, nick_from: str, msg: str, channel: str = None, nick_to: str = None):
        """Sending PRIVMSG to a channel or to a nickname by batches
        could be either channel or nickname not both together
        Args:
            msg (str): The message to send
            nick_from (str): The sender nickname
            channel (str, optional): The receiver channel. Defaults to None.
            nick_to (str, optional): The reciever nickname. Defaults to None.
        """
        try:
            batch_size      = self.__Config.BATCH_SIZE
            User_from       = self.__Irc.User.get_user(nick_from)
            User_to         = self.__Irc.User.get_user(nick_to) if not nick_to is None else None

            if User_from is None:
                self.__Logs.error(f"The sender nickname [{nick_from}] do not exist")
                return None

            if not channel is None:
                for i in range(0, len(str(msg)), batch_size):
                    batch = str(msg)[i:i+batch_size]
                    self.send2socket(f":{User_from.uid} PRIVMSG {channel} :{batch}")

            if not nick_to is None:
                for i in range(0, len(str(msg)), batch_size):
                    batch = str(msg)[i:i+batch_size]
                    self.send2socket(f":{nick_from} PRIVMSG {User_to.uid} :{batch}")

        except Exception as err:
            self.__Logs.error(f"General Error: {err}")
            self.__Logs.error(f"General Error: {nick_from} - {channel} - {nick_to}")

    def send_notice(self, nick_from: str, nick_to: str, msg: str) -> None:
        """Sending NOTICE by batches

        Args:
            msg (str): The message to send to the server
            nick_from (str): The sender Nickname
            nick_to (str): The reciever nickname
        """
        try:
            batch_size  = self.__Config.BATCH_SIZE
            User_from   = self.__Irc.User.get_user(nick_from)
            User_to     = self.__Irc.User.get_user(nick_to)

            if User_from is None or User_to is None:
                self.__Logs.error(f"The sender [{nick_from}] or the Reciever [{nick_to}] do not exist")
                return None

            for i in range(0, len(str(msg)), batch_size):
                batch = str(msg)[i:i+batch_size]
                self.send2socket(f":{User_from.uid} NOTICE {User_to.uid} :{batch}")

        except Exception as err:
            self.__Logs.error(f"General Error: {err}")

    def send_link(self):
        """Créer le link et envoyer les informations nécessaires pour la 
        connexion au serveur.
        """
        service_id = self.__Config.SERVICE_ID
        service_nickname = self.__Config.SERVICE_NICKNAME
        service_username = self.__Config.SERVICE_USERNAME
        service_realname = self.__Config.SERVICE_REALNAME
        service_channel_log = self.__Config.SERVICE_CHANLOG
        service_info = self.__Config.SERVICE_INFO
        service_smodes = self.__Config.SERVICE_SMODES
        service_cmodes = self.__Config.SERVICE_CMODES
        service_umodes = self.__Config.SERVICE_UMODES
        service_hostname = self.__Config.SERVICE_HOST
        service_name = self.__Config.SERVICE_NAME
        protocolversion = self.protocol_version

        server_password = self.__Config.SERVEUR_PASSWORD
        server_link = self.__Config.SERVEUR_LINK
        server_id = self.__Config.SERVEUR_ID

        version = self.__Config.CURRENT_VERSION
        unixtime = self.__Utils.get_unixtime()

        self.send2socket(f":{server_id} PASS :{server_password}", print_log=False)
        self.send2socket(f":{server_id} PROTOCTL SID NOQUIT NICKv2 SJOIN SJ3 NICKIP TKLEXT2 NEXTBANS CLK EXTSWHOIS MLOCK MTAGS")
        self.send2socket(f":{server_id} PROTOCTL EAUTH={server_link},{protocolversion},,{service_name}-v{version}")
        self.send2socket(f":{server_id} PROTOCTL SID={server_id}")
        self.send2socket(f":{server_id} PROTOCTL BOOTED={unixtime}")
        self.send2socket(f":{server_id} SERVER {server_link} 1 :{service_info}")
        self.send2socket("EOS")
        self.send2socket(f":{server_id} {service_nickname} :Reserved for services")
        self.send2socket(f":{server_id} UID {service_nickname} 1 {unixtime} {service_username} {service_hostname} {service_id} * {service_smodes} * * fwAAAQ== :{service_realname}")
        self.send_sjoin(service_channel_log)
        self.send2socket(f":{server_id} TKL + Q * {service_nickname} {service_hostname} 0 {unixtime} :Reserved for services")
        self.send2socket(f":{service_id} MODE {service_channel_log} {service_cmodes}")

        self.__Logs.debug(f'>> {__name__} Link information sent to the server')

    def send_gline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        """Send a gline command to the server

        Args:
            nickname (str): The nickname of the client.
            hostname (str): The hostname of the client.
            set_by (str): The nickname who send the gline
            expire_timestamp (int): Expire timestamp
            set_at_timestamp (int): Set at timestamp
            reason (str): The reason of the gline.
        """
        # TKL + G user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL + G {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def send_set_nick(self, newnickname: str) -> None:
        """Change nickname of the server
        \n This method will also update the User object
        Args:
            newnickname (str): New nickname of the server
        """
        self.send2socket(f":{self.__Config.SERVICE_NICKNAME} NICK {newnickname}")

        userObj = self.__Irc.User.get_user(self.__Config.SERVICE_NICKNAME)
        self.__Irc.User.update_nickname(userObj.uid, newnickname)
        return None

    def send_set_mode(self, modes: str, *, nickname: Optional[str] = None, channel_name: Optional[str] = None, params: Optional[str] = None) -> None:
        """Set a mode to channel or to a nickname or for a user in a channel

        Args:
            modes (str): The selected mode
            nickname (Optional[str]): The nickname
            channel_name (Optional[str]): The channel name
            params (Optional[str]): Parameters like password.
        """
        service_id = self.__Config.SERVICE_ID

        if modes[0] not in ['+', '-']:
            self.__Logs.error(f"[MODE ERROR] The mode you have provided is missing the sign: {modes}")
            return None

        if nickname and channel_name:
            # :98KAAAAAB MODE #services +o defenderdev
            if not self.__Irc.Channel.is_valid_channel(channel_name):
                self.__Logs.error(f"[MODE ERROR] The channel is not valid: {channel_name}")
                return None
            self.send2socket(f":{service_id} MODE {channel_name} {modes} {nickname}")
            return None
        
        if nickname and channel_name is None:
            self.send2socket(f":{service_id} MODE {nickname} {modes}")
            return None
        
        if nickname is None and channel_name:
            if not self.__Irc.Channel.is_valid_channel(channel_name):
                self.__Logs.error(f"[MODE ERROR] The channel is not valid: {channel_name}")
                return None
            self.send2socket(f":{service_id} MODE {channel_name} {modes} {params}")
            return None
        
        return None

    def send_squit(self, server_id: str, server_link: str, reason: str) -> None:

        if not reason:
            reason = 'Service Shutdown'

        self.send2socket(f":{server_id} SQUIT {server_link} :{reason}")
        return None

    def send_ungline(self, nickname:str, hostname: str) -> None:

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL - G {nickname} {hostname} {self.__Config.SERVICE_NICKNAME}")

        return None

    def send_kline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + k user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL + k {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def send_unkline(self, nickname:str, hostname: str) -> None:

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL - K {nickname} {hostname} {self.__Config.SERVICE_NICKNAME}")

        return None

    def send_sjoin(self, channel: str) -> None:
        """Server will join a channel with pre defined umodes

        Args:
            channel (str): Channel to join
        """
        if not self.__Irc.Channel.is_valid_channel(channel):
            self.__Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{self.__Config.SERVEUR_ID} SJOIN {self.__Utils.get_unixtime()} {channel} {self.__Config.SERVICE_UMODES} :{self.__Config.SERVICE_ID}")
        self.send2socket(f":{self.__Config.SERVICE_ID} MODE {channel} {self.__Config.SERVICE_UMODES} {self.__Config.SERVICE_ID}")

        # Add defender to the channel uids list
        self.__Irc.Channel.insert(self.__Irc.Loader.Definition.MChannel(name=channel, uids=[self.__Config.SERVICE_ID]))
        return None

    def send_sapart(self, nick_to_sapart: str, channel_name: str) -> None:
        """_summary_

        Args:
            from_nick (str): _description_
            nick_to (str): _description_
            channel_name (str): _description_
        """
        try:

            userObj = self.__Irc.User.get_user(uidornickname=nick_to_sapart)
            chanObj = self.__Irc.Channel.get_channel(channel_name)
            service_uid = self.__Config.SERVICE_ID

            if userObj is None or chanObj is None:
                return None

            self.send2socket(f":{service_uid} SAPART {userObj.nickname} {chanObj.name}")
            self.__Irc.Channel.delete_user_from_channel(chanObj.name, userObj.uid)

            return None

        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def send_sajoin(self, nick_to_sajoin: str, channel_name: str) -> None:
        """_summary_

        Args:
            nick_to_sajoin (str): _description_
            channel_name (str): _description_
        """
        try:

            userObj = self.__Irc.User.get_user(uidornickname=nick_to_sajoin)
            chanObj = self.__Irc.Channel.get_channel(channel_name)
            service_uid = self.__Config.SERVICE_ID

            if userObj is None:
                # User not exist: leave
                return None

            if chanObj is None:
                # Channel not exist
                if not self.__Irc.Channel.is_valid_channel(channel_name):
                    # Incorrect channel: leave
                    return None

                # Create the new channel with the uid
                newChanObj = self.__Irc.Loader.Definition.MChannel(name=channel_name, uids=[userObj.uid])
                self.__Irc.Channel.insert(newChanObj)
                self.send2socket(f":{service_uid} SAJOIN {userObj.nickname} {newChanObj.name}")

            else:
                self.__Irc.Channel.add_user_to_a_channel(channel_name=channel_name, uid=userObj.uid)
                self.send2socket(f":{service_uid} SAJOIN {userObj.nickname} {chanObj.name}")

            return None

        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def send_svspart(self, nick_to_part: str, channels: list[str], reason: str) -> None:
        user_obj = self.__Irc.User.get_user(nick_to_part)

        if user_obj is None:
            self.__Logs.debug(f"[SVSPART] The nickname {nick_to_part} do not exist!")
            return None

        channels_list = ','.join([channel for channel in channels if self.__Irc.Channel.is_valid_channel(channel)])
        service_id = self.__Config.SERVICE_ID
        self.send2socket(f':{service_id} SVSPART {user_obj.nickname} {channels_list} {reason}')
        return None

    def send_svsjoin(self, nick_to_part: str, channels: list[str], keys: list[str]) -> None:
        user_obj = self.__Irc.User.get_user(nick_to_part)

        if user_obj is None:
            self.__Logs.debug(f"[SVSJOIN] The nickname {nick_to_part} do not exist!")
            return None

        channels_list = ','.join([channel for channel in channels if self.__Irc.Channel.is_valid_channel(channel)])
        keys_list = ','.join([key for key in keys])
        service_id = self.__Config.SERVICE_ID
        self.send2socket(f':{service_id} SVSJOIN {user_obj.nickname} {channels_list} {keys_list}')
        return None

    def send_svsmode(self, nickname: str, user_mode: str) -> None:
        try:
            user_obj = self.__Irc.User.get_user(uidornickname=nickname)
            service_uid = self.__Config.SERVICE_ID

            if user_obj is None:
                return None

            self.send2socket(f':{service_uid} SVSMODE {nickname} {user_mode}')

            # Update new mode
            self.__Irc.User.update_mode(user_obj.uid, user_mode)

            return None
        except Exception as err:
                self.__Logs.error(f"{__name__} - General Error: {err}")

    def send_svs2mode(self, nickname: str, user_mode: str) -> None:
        try:
            user_obj = self.__Irc.User.get_user(uidornickname=nickname)
            service_uid = self.__Config.SERVICE_ID

            if user_obj is None:
                return None

            self.send2socket(f':{service_uid} SVS2MODE {nickname} {user_mode}')

            # Update new mode
            self.__Irc.User.update_mode(user_obj.uid, user_mode)

            return None
        except Exception as err:
                self.__Logs.error(f"{__name__} - General Error: {err}")

    def send_svslogin(self, client_uid: str, user_account: str) -> None:
        """Log a client into his account.

        Args:
            client_uid (str): Client UID
            user_account (str): The account of the user
        """
        try:
            self.send2socket(f":{self.__Irc.Config.SERVEUR_LINK} SVSLOGIN {self.__Settings.MAIN_SERVER_HOSTNAME} {client_uid} {user_account}")
        except Exception as err:
            self.__Logs.error(f'General Error: {err}')

    def send_svslogout(self, client_obj: 'MClient') -> None:
        """Logout a client from his account

        Args:
            client_uid (str): The Client UID
        """
        try:
            c_uid = client_obj.uid
            c_nickname = client_obj.nickname
            self.send2socket(f":{self.__Irc.Config.SERVEUR_LINK} SVSLOGIN {self.__Settings.MAIN_SERVER_HOSTNAME} {c_uid} 0")
            self.send_svs2mode(c_nickname, '-r')

        except Exception as err:
            self.__Logs.error(f'General Error: {err}')

    def send_quit(self, uid: str, reason: str, print_log: True) -> None:
        """Send quit message
        - Delete uid from User object
        - Delete uid from Reputation object

        Args:
            uidornickname (str): The UID or the Nickname
            reason (str): The reason for the quit
        """
        user_obj = self.__Irc.User.get_user(uidornickname=uid)
        reputationObj = self.__Irc.Reputation.get_reputation(uidornickname=uid)

        if not user_obj is None:
            self.send2socket(f":{user_obj.uid} QUIT :{reason}", print_log=print_log)
            self.__Irc.User.delete(user_obj.uid)

        if not reputationObj is None:
            self.__Irc.Reputation.delete(reputationObj.uid)

        if not self.__Irc.Channel.delete_user_from_all_channel(uid):
            self.__Logs.error(f"The UID [{uid}] has not been deleted from all channels")

        return None

    def send_uid(self, nickname:str, username: str, hostname: str, uid:str, umodes: str, vhost: str, remote_ip: str, realname: str, print_log: bool = True) -> None:
        """Send UID to the server
        - Insert User to User Object
        Args:
            nickname (str): Nickname of the client
            username (str): Username of the client
            hostname (str): Hostname of the client you want to create
            uid (str): UID of the client you want to create
            umodes (str): umodes of the client you want to create
            vhost (str): vhost of the client you want to create
            remote_ip (str): remote_ip of the client you want to create
            realname (str): realname of the client you want to create
            print_log (bool, optional): print logs if true. Defaults to True.
        """
        # {self.Config.SERVEUR_ID} UID 
        # {clone.nickname} 1 {self.__Utils.get_unixtime()} {clone.username} {clone.hostname} {clone.uid} * {clone.umodes}  {clone.vhost} * {self.Base.encode_ip(clone.remote_ip)} :{clone.realname}
        try:
            unixtime = self.__Utils.get_unixtime()
            encoded_ip = self.__Base.encode_ip(remote_ip)

            # Create the user
            self.__Irc.User.insert(
                self.__Irc.Loader.Definition.MUser(
                            uid=uid, nickname=nickname, username=username, 
                            realname=realname,hostname=hostname, umodes=umodes,
                            vhost=vhost, remote_ip=remote_ip
                        )
                    )

            uid_msg = f":{self.__Config.SERVEUR_ID} UID {nickname} 1 {unixtime} {username} {hostname} {uid} * {umodes} {vhost} * {encoded_ip} :{realname}"

            self.send2socket(uid_msg, print_log=print_log)

            return None

        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def send_join_chan(self, uidornickname: str, channel: str, password: str = None, print_log: bool = True) -> None:
        """Joining a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            password (str, optional): The password of the channel to join. Default to None
            print_log (bool, optional): Write logs. Defaults to True.
        """

        userObj = self.__Irc.User.get_user(uidornickname)
        passwordChannel = password if not password is None else ''

        if userObj is None:
            return None

        if not self.__Irc.Channel.is_valid_channel(channel):
            self.__Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{userObj.uid} JOIN {channel} {passwordChannel}", print_log=print_log)

        if uidornickname == self.__Config.SERVICE_NICKNAME or uidornickname == self.__Config.SERVICE_ID:
            self.send2socket(f":{self.__Config.SERVICE_ID} MODE {channel} {self.__Config.SERVICE_UMODES} {self.__Config.SERVICE_ID}")

        # Add defender to the channel uids list
        self.__Irc.Channel.insert(self.__Irc.Loader.Definition.MChannel(name=channel, uids=[userObj.uid]))

        # Set the automode to the user
        if 'r' not in userObj.umodes and 'o' not in userObj.umodes:
            return None

        db_data: dict[str, str] = {"nickname": userObj.nickname, "channel": channel}
        db_query = self.__Base.db_execute_query("SELECT id, mode FROM command_automode WHERE nickname = :nickname AND channel = :channel", db_data)
        db_result = db_query.fetchone()
        if db_result is not None:
            id, mode = db_result
            self.send2socket(f":{self.__Config.SERVICE_ID} MODE {channel} {mode} {userObj.nickname}")

        return None

    def send_part_chan(self, uidornickname:str, channel: str, print_log: bool = True) -> None:
        """Part from a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            print_log (bool, optional): Write logs. Defaults to True.
        """

        userObj = self.__Irc.User.get_user(uidornickname)

        if userObj is None:
            self.__Logs.error(f"The user [{uidornickname}] is not valid")
            return None

        if not self.__Irc.Channel.is_valid_channel(channel):
            self.__Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{userObj.uid} PART {channel}", print_log=print_log)

        # Add defender to the channel uids list
        self.__Irc.Channel.delete_user_from_channel(channel, userObj.uid)
        return None

    def send_mode_chan(self, channel_name: str, channel_mode: str) -> None:

        channel = self.__Irc.Channel.is_valid_channel(channel_name)
        if not channel:
            self.__Logs.error(f'The channel [{channel_name}] is not correct')
            return None

        self.send2socket(f":{self.__Config.SERVICE_NICKNAME} MODE {channel_name} {channel_mode}")
        return None

    def send_raw(self, raw_command: str) -> None:

        self.send2socket(f":{self.__Config.SERVICE_NICKNAME} {raw_command}")

        return None

    # ------------------------------------------------------------------------
    #                           COMMON IRC PARSER
    # ------------------------------------------------------------------------

    def parse_uid(self, serverMsg: list[str]) -> dict[str, str]:
        """Parse UID and return dictionary.
        >>> ['@s2s-md/geoip=cc=GBtag...', ':001', 'UID', 'albatros', '0', '1721564597', 'albatros', 'hostname...', '001HB8G04', '0', '+iwxz', 'hostname-vhost', 'hostname-vhost', 'MyZBwg==', ':...']
        Args:
            serverMsg (list[str]): The UID ircd response
        """
        umodes = str(serverMsg[10])
        remote_ip = self.__Base.decode_ip(str(serverMsg[13])) if 'S' not in umodes else '127.0.0.1'

        # Extract Geoip information
        pattern = r'^.*geoip=cc=(\S{2}).*$'
        geoip_match = match(pattern, serverMsg[0])
        geoip = geoip_match.group(1) if geoip_match else None

        response = {
            'uid': str(serverMsg[8]),
            'nickname': str(serverMsg[3]),
            'username': str(serverMsg[6]),
            'hostname': str(serverMsg[7]),
            'umodes': umodes,
            'vhost': str(serverMsg[11]),
            'ip': remote_ip,
            'realname': ' '.join(serverMsg[12:]).lstrip(':'),
            'geoip': geoip,
            'reputation_score': 0,
            'iswebirc': True if 'webirc' in serverMsg[0] else False,
            'iswebsocket': True if 'websocket' in serverMsg[0] else False
        }
        return response

    def parse_quit(self, serverMsg: list[str]) -> dict[str, str]:
        """Parse quit and return dictionary.
        >>> # ['@unrealtag...', ':001JKNY0N', 'QUIT', ':Quit:', '....']
        Args:
            serverMsg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The dictionary.
        """
        scopy = serverMsg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)

        response = {
            "uid": scopy[0].replace(':', ''),
            "reason": " ".join(scopy[3:])
        }
        return response

    def parse_nick(self, serverMsg: list[str]) -> dict[str, str]:
        """Parse nick changes and return dictionary.
        >>> ['@unrealircd.org/geoip=FR;unrealircd.org/', ':001OOU2H3', 'NICK', 'WebIrc', '1703795844']

        Args:
            serverMsg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The response as dictionary.
        """
        scopy = serverMsg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)

        response = {
            "uid": scopy[0].replace(':', ''),
            "newnickname": scopy[2],
            "timestamp": scopy[3]
        }
        return response

    def parse_privmsg(self, serverMsg: list[str]) -> dict[str, str]:
        """Parse PRIVMSG message.
        >>> ['@....', ':97KAAAAAE', 'PRIVMSG', '#welcome', ':This', 'is', 'my', 'public', 'message']
        >>> [':97KAAAAAF', 'PRIVMSG', '98KAAAAAB', ':sasa']

        Args:
            serverMsg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The response as dictionary.
        """
        scopy = serverMsg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)

        response = {
            "uid_sender": scopy[0].replace(':', ''),
            "uid_reciever": self.__Irc.User.get_uid(scopy[2]),
            "channel": scopy[2] if self.__Irc.Channel.is_valid_channel(scopy[2]) else None,
            "message": " ".join(scopy[3:])
        }
        return response

    #####################
    #   HANDLE EVENTS   #
    #####################

    def on_svs2mode(self, serverMsg: list[str]) -> None:
        """Handle svs2mode coming from a server
        >>> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # >> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']

            uid_user_to_edit = serverMsg[2]
            umode = serverMsg[3]

            userObj = self.__Irc.User.get_user(uid_user_to_edit)

            if userObj is None:
                return None

            if self.__Irc.User.update_mode(userObj.uid, umode):
                return None

            return None
        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_mode(self, serverMsg: list[str]) -> None:
        """Handle mode coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        #['@msgid=d0ySx56Yd0nc35oHts2SkC-/J9mVUA1hfM6...', ':001', 'MODE', '#a', '+nt', '1723207536']
        #['@unrealircd.org/userhost=adator@localhost;...', ':001LQ0L0C', 'MODE', '#services', '-l']

        return None

    def on_umode2(self, serverMsg: list[str]) -> None:
        """Handle umode2 coming from a server
        >>> [':adator_', 'UMODE2', '-i']

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # [':adator_', 'UMODE2', '-iwx']

            userObj  = self.__Irc.User.get_user(str(serverMsg[0]).lstrip(':'))
            userMode = serverMsg[2]

            if userObj is None: # If user is not created
                return None

            # save previous user modes
            old_umodes = userObj.umodes

            # TODO : User object should be able to update user modes
            if self.__Irc.User.update_mode(userObj.uid, userMode):
                return None
                # self.__Logs.debug(f"Updating user mode for [{userObj.nickname}] [{old_umodes}] => [{userObj.umodes}]")

            return None

        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_quit(self, serverMsg: list[str]) -> None:
        """Handle quit coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # ['@unrealircd.org/userhost=...@192.168.1.10;unrealircd.org/userip=...@192.168.1.10;msgid=CssUrV08BzekYuq7BfvPHn;time=2024-11-02T15:03:33.182Z', ':001JKNY0N', 'QUIT', ':Quit:', '....']

            uid_who_quit = str(serverMsg[1]).lstrip(':')

            self.__Irc.Channel.delete_user_from_all_channel(uid_who_quit)
            self.__Irc.User.delete(uid_who_quit)
            self.__Irc.Client.delete(uid_who_quit)
            self.__Irc.Reputation.delete(uid_who_quit)
            self.__Irc.Admin.delete(uid_who_quit)

            return None

        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_squit(self, serverMsg: list[str]) -> None:
        """Handle squit coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        # ['@msgid=QOEolbRxdhpVW5c8qLkbAU;time=2024-09-21T17:33:16.547Z', 'SQUIT', 'defender.deb.biz.st', ':Connection', 'closed']

        server_hostname = serverMsg[2]
        uid_to_delete = None
        for s_user in self.__Irc.User.UID_DB:
            if s_user.hostname == server_hostname and 'S' in s_user.umodes:
                uid_to_delete = s_user.uid

        if uid_to_delete is None:
            return None

        self.__Irc.User.delete(uid_to_delete)
        self.__Irc.Channel.delete_user_from_all_channel(uid_to_delete)

        return None

    def on_protoctl(self, serverMsg: list[str]) -> None:
        """Handle protoctl coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        # ['PROTOCTL', 'CHANMODES=beI,fkL,lFH,cdimnprstzCDGKMNOPQRSTVZ', 'USERMODES=diopqrstwxzBDGHIRSTWZ', 'BOOTED=1728815798', 'PREFIX=(qaohv)~&@%+', 'SID=001', 'MLOCK', 'TS=1730662755', 'EXTSWHOIS']
        user_modes: str = None
        prefix: str = None
        host_server_id: str = None

        for msg in serverMsg:
            pattern = None
            if msg.startswith('PREFIX='):
                pattern = r'^PREFIX=\((.*)\).*$'
                find_match = match(pattern, msg)
                prefix = find_match.group(1) if find_match else None
                if find_match:
                    prefix = find_match.group(1)

            elif msg.startswith('USERMODES='):
                pattern = r'^USERMODES=(.*)$'
                find_match = match(pattern, msg)
                user_modes = find_match.group(1) if find_match else None
            elif msg.startswith('SID='):
                host_server_id = msg.split('=')[1]

        if user_modes is None or prefix is None or host_server_id is None:
            return None

        self.__Config.HSID = host_server_id
        self.__Settings.PROTOCTL_USER_MODES = list(user_modes)
        self.__Settings.PROTOCTL_PREFIX = list(prefix)

        return None

    def on_nick(self, serverMsg: list[str]) -> None:
        """Handle nick coming from a server
        new nickname

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # ['@unrealircd.org/geoip=FR;unrealircd.org/', ':001OOU2H3', 'NICK', 'WebIrc', '1703795844']
            # Changement de nickname

            uid = str(serverMsg[1]).lstrip(':')
            newnickname = serverMsg[3]
            self.__Irc.User.update_nickname(uid, newnickname)
            self.__Irc.Client.update_nickname(uid, newnickname)
            self.__Irc.Admin.update_nickname(uid, newnickname)
            self.__Irc.Reputation.update(uid, newnickname)

            return None

        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_sjoin(self, serverMsg: list[str]) -> None:
        """Handle sjoin coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # ['@msgid=5sTwGdj349D82L96p749SY;time=2024-08-15T09:50:23.528Z', ':001', 'SJOIN', '1721564574', '#welcome', ':001JD94QH']
            # ['@msgid=bvceb6HthbLJapgGLXn1b0;time=2024-08-15T09:50:11.464Z', ':001', 'SJOIN', '1721564574', '#welcome', '+lnrt', '13', ':001CIVLQF', '+11ZAAAAAB', '001QGR10C', '*@0014UE10B', '001NL1O07', '001SWZR05', '001HB8G04', '@00BAAAAAJ', '0019M7101']
            # ['@msgid=SKUeuVzOrTShRDduq8VerX;time=2024-08-23T19:37:04.266Z', ':001', 'SJOIN', '1723993047', '#welcome', '+lnrt', '13', 
            # ':001T6VU3F', '001JGWB2K', '@11ZAAAAAB', 
            # '001F16WGR', '001X9YMGQ', '*+001DYPFGP', '@00BAAAAAJ', '001AAGOG9', '001FMFVG8', '001DAEEG7', 
            # '&~G:unknown-users', '"~G:websocket-users', '"~G:known-users', '"~G:webirc-users']
            # [':00B', 'SJOIN', '1731872579', '#services', '+', ':00BAAAAAB']
            serverMsg_copy = serverMsg.copy()
            if serverMsg_copy[0].startswith('@'):
                serverMsg_copy.pop(0)

            channel = str(serverMsg_copy[3]).lower()
            len_cmd = len(serverMsg_copy)
            list_users:list = []
            occurence = 0
            start_boucle = 0

            # Trouver le premier user
            for i in range(len_cmd):
                s: list = findall(fr':', serverMsg_copy[i])
                if s:
                    occurence += 1
                    if occurence == 2:
                        start_boucle = i

            # Boucle qui va ajouter l'ensemble des users (UID)
            for i in range(start_boucle, len(serverMsg_copy)):
                parsed_UID = str(serverMsg_copy[i])
                clean_uid = self.__Utils.clean_uid(parsed_UID)
                if not clean_uid is None and len(clean_uid) == 9:
                    list_users.append(clean_uid)

            if list_users:
                self.__Irc.Channel.insert(
                    self.__Irc.Loader.Definition.MChannel(
                        name=channel,
                        uids=list_users
                    )
                )
            return None

        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_part(self, serverMsg: list[str]) -> None:
        """Handle part coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # ['@unrealircd.org', ':001EPFBRD', 'PART', '#welcome', ':WEB', 'IRC', 'Paris']
            uid = str(serverMsg[1]).lstrip(':')
            channel = str(serverMsg[3]).lower()
            self.__Irc.Channel.delete_user_from_channel(channel, uid)
            return None

        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_eos(self, serverMsg: list[str]) -> None:
        """Handle EOS coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # [':001', 'EOS']
            server_msg_copy = serverMsg.copy()
            hsid = str(server_msg_copy[0]).replace(':','')
            if hsid == self.__Config.HSID:
                if self.__Config.DEFENDER_INIT == 1:
                    current_version = self.__Config.CURRENT_VERSION
                    latest_version = self.__Config.LATEST_VERSION
                    if self.__Base.check_for_new_version(False):
                        version = f'{current_version} >>> {latest_version}'
                    else:
                        version = f'{current_version}'

                    print(f"################### DEFENDER ###################")
                    print(f"#               SERVICE CONNECTE                ")
                    print(f"# SERVEUR  :    {self.__Config.SERVEUR_IP}        ")
                    print(f"# PORT     :    {self.__Config.SERVEUR_PORT}      ")
                    print(f"# SSL      :    {self.__Config.SERVEUR_SSL}       ")
                    print(f"# SSL VER  :    {self.__Config.SSL_VERSION}       ")
                    print(f"# NICKNAME :    {self.__Config.SERVICE_NICKNAME}  ")
                    print(f"# CHANNEL  :    {self.__Config.SERVICE_CHANLOG}   ")
                    print(f"# VERSION  :    {version}                       ")
                    print(f"################################################")

                    self.__Logs.info(f"################### DEFENDER ###################")
                    self.__Logs.info(f"#               SERVICE CONNECTE                ")
                    self.__Logs.info(f"# SERVEUR  :    {self.__Config.SERVEUR_IP}        ")
                    self.__Logs.info(f"# PORT     :    {self.__Config.SERVEUR_PORT}      ")
                    self.__Logs.info(f"# SSL      :    {self.__Config.SERVEUR_SSL}       ")
                    self.__Logs.info(f"# SSL VER  :    {self.__Config.SSL_VERSION}       ")
                    self.__Logs.info(f"# NICKNAME :    {self.__Config.SERVICE_NICKNAME}  ")
                    self.__Logs.info(f"# CHANNEL  :    {self.__Config.SERVICE_CHANLOG}   ")
                    self.__Logs.info(f"# VERSION  :    {version}                       ")
                    self.__Logs.info(f"################################################")

                    self.send_sjoin(self.__Config.SERVICE_CHANLOG)

                    if self.__Base.check_for_new_version(False):
                        self.send_priv_msg(
                            nick_from=self.__Config.SERVICE_NICKNAME,
                            msg=f" New Version available {version}",
                            channel=self.__Config.SERVICE_CHANLOG
                        )

                # Initialisation terminé aprés le premier PING
                self.send_priv_msg(
                    nick_from=self.__Config.SERVICE_NICKNAME,
                    msg=tr("[ %sINFORMATION%s ] >> %s is ready!", self.__Config.COLORS.green, self.__Config.COLORS.nogc, self.__Config.SERVICE_NICKNAME),
                    channel=self.__Config.SERVICE_CHANLOG
                )
                self.__Config.DEFENDER_INIT = 0

                # Send EOF to other modules
                for module in self.__Irc.ModuleUtils.model_get_loaded_modules().copy():
                    module.class_instance.cmd(server_msg_copy)

                # Join saved channels & load existing modules
                self.__Irc.join_saved_channels()
                self.__Irc.ModuleUtils.db_load_all_existing_modules(self.__Irc)

                return None
        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Key Error: {ie}")
        except KeyError as ke:
            self.__Logs.error(f"{__name__} - Key Error: {ke}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_reputation(self, serverMsg: list[str]) -> None:
        """Handle REPUTATION coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # :001 REPUTATION 127.0.0.1 118
            server_msg_copy = serverMsg.copy()
            self.__Irc.first_connexion_ip = server_msg_copy[2]
            self.__Irc.first_score = 0

            if str(server_msg_copy[3]).find('*') != -1:
                # If * available, it means that an ircop changed the repurtation score
                # means also that the user exist will try to update all users with same IP
                self.__Irc.first_score = int(str(server_msg_copy[3]).replace('*',''))
                for user in self.__Irc.User.UID_DB:
                    if user.remote_ip == self.__Irc.first_connexion_ip:
                        user.score_connexion = self.__Irc.first_score
            else:
                self.__Irc.first_score = int(server_msg_copy[3])

            # Possibilité de déclancher les bans a ce niveau.
        except IndexError as ie:
            self.__Logs.error(f'Index Error {__name__}: {ie}')
        except ValueError as ve:
            self.__Irc.first_score = 0
            self.__Logs.error(f'Value Error {__name__}: {ve}')
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_uid(self, serverMsg: list[str]) -> None:
        """Handle uid message coming from the server

        Args:
            serverMsg (list[str]): Original server message
        """
        # ['@s2s-md/geoip=cc=GB|cd=United\\sKingdom|asn=16276|asname=OVH\\sSAS;s2s-md/tls_cipher=TLSv1.3-TLS_CHACHA20_POLY1305_SHA256;s2s-md/creationtime=1721564601', 
        # ':001', 'UID', 'albatros', '0', '1721564597', 'albatros', 'vps-91b2f28b.vps.ovh.net', 
        # '001HB8G04', '0', '+iwxz', 'Clk-A62F1D18.vps.ovh.net', 'Clk-A62F1D18.vps.ovh.net', 'MyZBwg==', ':...']
        try:

            isWebirc = True if 'webirc' in serverMsg[0] else False
            isWebsocket = True if 'websocket' in serverMsg[0] else False

            uid = str(serverMsg[8])
            nickname = str(serverMsg[3])
            username = str(serverMsg[6])
            hostname = str(serverMsg[7])
            umodes = str(serverMsg[10])
            vhost = str(serverMsg[11])

            if not 'S' in umodes:
                remote_ip = self.__Base.decode_ip(str(serverMsg[13]))
            else:
                remote_ip = '127.0.0.1'

            # extract realname
            realname = ' '.join(serverMsg[14:]).lstrip(':')

            # Extract Geoip information
            pattern = r'^.*geoip=cc=(\S{2}).*$'
            geoip_match = match(pattern, serverMsg[0])

            # Extract Fingerprint information
            pattern = r'^.*certfp=([^;]+).*$'
            fp_match = match(pattern, serverMsg[0])
            fingerprint = fp_match.group(1) if fp_match else None

            # Extract tls_cipher information
            pattern = r'^.*tls_cipher=([^;]+).*$'
            tlsc_match = match(pattern, serverMsg[0])
            tls_cipher = tlsc_match.group(1) if tlsc_match else None

            if geoip_match:
                geoip = geoip_match.group(1)
            else:
                geoip = None

            score_connexion = self.__Irc.first_score

            self.__Irc.User.insert(
                self.__Irc.Loader.Definition.MUser(
                    uid=uid,
                    nickname=nickname,
                    username=username,
                    realname=realname,
                    hostname=hostname,
                    umodes=umodes,
                    vhost=vhost,
                    fingerprint=fingerprint,
                    tls_cipher=tls_cipher,
                    isWebirc=isWebirc,
                    isWebsocket=isWebsocket,
                    remote_ip=remote_ip,
                    geoip=geoip,
                    score_connexion=score_connexion,
                    connexion_datetime=datetime.now()
                )
            )

            # Auto Auth admin via fingerprint
            dnickname = self.__Config.SERVICE_NICKNAME
            dchanlog  = self.__Config.SERVICE_CHANLOG
            GREEN = self.__Config.COLORS.green
            RED = self.__Config.COLORS.red
            NOGC = self.__Config.COLORS.nogc

            for module in self.__Irc.ModuleUtils.model_get_loaded_modules().copy():
                module.class_instance.cmd(serverMsg)

            # SASL authentication
            # ['@s2s-md/..', ':001', 'UID', 'adator__', '0', '1755987444', '...', 'desktop-h1qck20.mshome.net', '001XLTT0U', '0', '+iwxz', '*', 'Clk-EC2256B2.mshome.net', 'rBKAAQ==', ':...']

            uid = serverMsg[8]
            nickname = serverMsg[3]
            sasl_obj = self.__Irc.Sasl.get_sasl_obj(uid)
            if sasl_obj:
                if sasl_obj.auth_success:
                    self.__Irc.insert_db_admin(sasl_obj.client_uid, sasl_obj.username, sasl_obj.level, sasl_obj.language)
                    self.send_priv_msg(nick_from=dnickname, 
                                        msg=tr("[ %sSASL AUTH%s ] - %s (%s) is now connected successfuly to %s", GREEN, NOGC, nickname, sasl_obj.username, dnickname),
                                        channel=dchanlog)
                    self.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Successfuly connected to %s", dnickname))
                else:
                    self.send_priv_msg(nick_from=dnickname, 
                                            msg=tr("[ %sSASL AUTH%s ] - %s provided a wrong password for this username %s", RED, NOGC, nickname, sasl_obj.username),
                                            channel=dchanlog)
                    self.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Wrong password!"))

                # Delete sasl object!
                self.__Irc.Sasl.delete_sasl_client(uid)
                return None

            # If no sasl authentication then auto connect via fingerprint
            if self.__Irc.Admin.db_auth_admin_via_fingerprint(fingerprint, uid):
                admin = self.__Irc.Admin.get_admin(uid)
                account = admin.account if admin else ''
                self.send_priv_msg(nick_from=dnickname, 
                                   msg=tr("[ %sFINGERPRINT AUTH%s ] - %s (%s) is now connected successfuly to %s", GREEN, NOGC, nickname, account, dnickname),
                                   channel=dchanlog)
                self.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Successfuly connected to %s", dnickname))

            return None
        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_privmsg(self, serverMsg: list[str]) -> None:
        """Handle PRIVMSG message coming from the server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            srv_msg = serverMsg.copy()
            cmd = serverMsg.copy()
            # Supprimer la premiere valeur si MTAGS activé
            if cmd[0].startswith('@'):
                cmd.pop(0)

            get_uid_or_nickname = str(cmd[0].replace(':',''))
            user_trigger = self.__Irc.User.get_nickname(get_uid_or_nickname)
            dnickname = self.__Config.SERVICE_NICKNAME
            pattern = fr'(:\{self.__Config.SERVICE_PREFIX})(.*)$'
            hcmds = search(pattern, ' '.join(cmd)) # va matcher avec tout les caractéres aprés le .

            if hcmds: # Commande qui commencent par le point
                liste_des_commandes = list(hcmds.groups())
                convert_to_string = ' '.join(liste_des_commandes)
                arg = convert_to_string.split()
                arg.remove(f':{self.__Config.SERVICE_PREFIX}')
                if not self.__Irc.Commands.is_command_exist(arg[0]):
                    self.__Logs.debug(f"This command {arg[0]} is not available")
                    self.send_notice(
                        nick_from=self.__Config.SERVICE_NICKNAME,
                        nick_to=user_trigger,
                        msg=f"This command [{self.__Config.COLORS.bold}{arg[0]}{self.__Config.COLORS.bold}] is not available"
                    )
                    return None

                cmd_to_send = convert_to_string.replace(':','')
                self.__Base.log_cmd(user_trigger, cmd_to_send)

                fromchannel = str(cmd[2]).lower() if self.__Irc.Channel.is_valid_channel(cmd[2]) else None
                self.__Irc.hcmds(user_trigger, fromchannel, arg, cmd)

            if cmd[2] == self.__Config.SERVICE_ID:
                pattern = fr'^:.*?:(.*)$'
                hcmds = search(pattern, ' '.join(cmd))

                if hcmds: # par /msg defender [commande]
                    liste_des_commandes = list(hcmds.groups())
                    convert_to_string = ' '.join(liste_des_commandes)
                    arg = convert_to_string.split()

                    # Réponse a un CTCP VERSION
                    if arg[0] == '\x01VERSION\x01':
                        self.on_version(srv_msg)
                        return None

                    # Réponse a un TIME
                    if arg[0] == '\x01TIME\x01':
                        self.on_time(srv_msg)
                        return None

                    # Réponse a un PING
                    if arg[0] == '\x01PING':
                        self.on_ping(srv_msg)
                        return None

                    if not self.__Irc.Commands.is_command_exist(arg[0]):
                        self.__Logs.debug(f"This command {arg[0]} sent by {user_trigger} is not available")
                        return None

                    # if not arg[0].lower() in self.__Irc.module_commands_list:
                    #     self.__Logs.debug(f"This command {arg[0]} sent by {user_trigger} is not available")
                    #     return False

                    cmd_to_send = convert_to_string.replace(':','')
                    self.__Base.log_cmd(user_trigger, cmd_to_send)

                    fromchannel = None
                    if len(arg) >= 2:
                        fromchannel = str(arg[1]).lower() if self.__Irc.Channel.is_valid_channel(arg[1]) else None

                    self.__Irc.hcmds(user_trigger, fromchannel, arg, cmd)
            return None

        except KeyError as ke:
            self.__Logs.error(f"Key Error: {ke}")
        except AttributeError as ae:
            self.__Logs.error(f"Attribute Error: {ae}")
        except Exception as err:
            self.__Logs.error(f"General Error: {err} - {srv_msg}" , exc_info=True)

    def on_server_ping(self, serverMsg: list[str]) -> None:
        """Send a PONG message to the server

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        try:
            pong = str(serverMsg[1]).replace(':','')
            self.send2socket(f"PONG :{pong}", print_log=False)

            return None
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_server(self, serverMsg: list[str]) -> None:
        """_summary_

        Args:
            serverMsg (list[str]): _description_
        """
        try:
            # ['SERVER', 'irc.local.org', '1', ':U6100-Fhn6OoE-001', 'Local', 'Server']
            sCopy = serverMsg.copy()
            self.__Irc.Settings.MAIN_SERVER_HOSTNAME = sCopy[1]
        except Exception as err:
            self.__Logs.error(f'General Error: {err}')

    def on_version(self, serverMsg: list[str]) -> None:
        """Sending Server Version to the server

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':00BAAAAAI', 'PRIVMSG', '12ZAAAAAB', ':\x01VERSION\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self.__Irc.User.get_nickname(self.__Utils.clean_uid(serverMsg[1]))
            dnickname = self.__Config.SERVICE_NICKNAME
            arg = serverMsg[4].replace(':', '')

            if nickname is None:
                return None

            if arg == '\x01VERSION\x01':
                self.send2socket(f':{dnickname} NOTICE {nickname} :\x01VERSION Service {self.__Config.SERVICE_NICKNAME} V{self.__Config.CURRENT_VERSION}\x01')

            return None
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_time(self, serverMsg: list[str]) -> None:
        """Sending TIME answer to a requestor

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':00BAAAAAI', 'PRIVMSG', '12ZAAAAAB', ':\x01TIME\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self.__Irc.User.get_nickname(self.__Utils.clean_uid(serverMsg[1]))
            dnickname = self.__Config.SERVICE_NICKNAME
            arg = serverMsg[4].replace(':', '')
            current_datetime = self.__Utils.get_sdatetime()

            if nickname is None:
                return None

            if arg == '\x01TIME\x01':
                self.send2socket(f':{dnickname} NOTICE {nickname} :\x01TIME {current_datetime}\x01')

            return None
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_ping(self, serverMsg: list[str]) -> None:
        """Sending a PING answer to requestor

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/...', ':001INC60B', 'PRIVMSG', '12ZAAAAAB', ':\x01PING', '762382207\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self.__Irc.User.get_nickname(self.__Utils.clean_uid(serverMsg[1]))
            dnickname = self.__Config.SERVICE_NICKNAME
            arg = serverMsg[4].replace(':', '')

            if nickname is None:
                self.__Logs.debug(serverMsg)
                return None

            if arg == '\x01PING':
                recieved_unixtime = int(serverMsg[5].replace('\x01',''))
                current_unixtime = self.__Utils.get_unixtime()
                ping_response = current_unixtime - recieved_unixtime

                # self.__Irc.send2socket(f':{dnickname} NOTICE {nickname} :\x01PING {ping_response} secs\x01')
                self.send_notice(
                    nick_from=dnickname,
                    nick_to=nickname,
                    msg=f"\x01PING {ping_response} secs\x01"
                )
                self.__Logs.debug(serverMsg)

            return None
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_version_msg(self, serverMsg: list[str]) -> None:
        """Handle version coming from the server
        \n ex. /version Defender
        Args:
            serverMsg (list[str]): Original message from the server
        """
        try:
            # ['@label=0073', ':0014E7P06', 'VERSION', 'PyDefender']
            serverMsg_copy = serverMsg.copy()
            if '@' in list(serverMsg_copy[0])[0]:
                serverMsg_copy.pop(0)

            getUser  = self.__Irc.User.get_user(self.__Utils.clean_uid(serverMsg_copy[0]))

            if getUser is None:
                return None

            response_351 = f"{self.__Config.SERVICE_NAME.capitalize()}-{self.__Config.CURRENT_VERSION} {self.__Config.SERVICE_HOST} {self.name}"
            self.send2socket(f':{self.__Config.SERVICE_HOST} 351 {getUser.nickname} {response_351}')

            modules = self.__Irc.ModuleUtils.get_all_available_modules()
            response_005 = ' | '.join(modules)
            self.send2socket(f':{self.__Config.SERVICE_HOST} 005 {getUser.nickname} {response_005} are supported by this server')

            response_005 = ''.join(self.__Settings.PROTOCTL_USER_MODES)
            self.send2socket(f":{self.__Config.SERVICE_HOST} 005 {getUser.nickname} {response_005} are supported by this server")

            return None

        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_smod(self, serverMsg: list[str]) -> None:
        """Handle SMOD message coming from the server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # [':001', 'SMOD', ':L:history_backend_mem:2.0', 'L:channeldb:1.0', 'L:tkldb:1.10', 'L:staff:3.8', 'L:ircops:3.71', ...]
            sCopy = serverMsg.copy()
            modules = [m.lstrip(':') for m in sCopy[2:]]

            for smod in modules:
                smod_split = smod.split(':')
                sModObj = self.__Irc.Loader.Definition.MSModule(type=smod_split[0], name=smod_split[1], version=smod_split[2])
                self.__Settings.SMOD_MODULES.append(sModObj)

        except Exception as err:
            self.__Logs.error(f'General Error: {err}')

    def on_sasl(self, serverMsg: list[str]) -> Optional['MSasl']:
        """Handle SASL coming from a server

        Args:
            serverMsg (list[str]): Original server message
            psasl (Sasl): The SASL process object
        """
        try:
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'H', '172.18.128.1', '172.18.128.1']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'S', 'PLAIN']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '0014ZZH1F', 'S', 'EXTERNAL', 'zzzzzzzkey']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'C', 'sasakey==']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'D', 'A']
            psasl = self.__Irc.Sasl
            sasl_enabled = False
            for smod in self.__Settings.SMOD_MODULES:
                if smod.name == 'sasl':
                    sasl_enabled = True
                    break

            if not sasl_enabled:
                return None

            sCopy = serverMsg.copy()
            client_uid = sCopy[3] if len(sCopy) >= 6 else None
            sasl_obj = None
            sasl_message_type = sCopy[4] if len(sCopy) >= 6 else None
            psasl.insert_sasl_client(self.__Irc.Loader.Definition.MSasl(client_uid=client_uid))
            sasl_obj = psasl.get_sasl_obj(client_uid)

            if sasl_obj is None:
                return None

            match sasl_message_type:
                case 'H':
                    sasl_obj.remote_ip = str(sCopy[5])
                    sasl_obj.message_type = sasl_message_type
                    return sasl_obj

                case 'S':
                    sasl_obj.message_type = sasl_message_type
                    if str(sCopy[5]) in ['PLAIN', 'EXTERNAL']:
                        sasl_obj.mechanisme = str(sCopy[5])

                    if sasl_obj.mechanisme == "PLAIN":
                        self.send2socket(f":{self.__Config.SERVEUR_LINK} SASL {self.__Settings.MAIN_SERVER_HOSTNAME} {sasl_obj.client_uid} C +")
                    elif sasl_obj.mechanisme == "EXTERNAL":
                        if str(sCopy[5]) == "+":
                            return None

                        sasl_obj.fingerprint = str(sCopy[6])
                        self.send2socket(f":{self.__Config.SERVEUR_LINK} SASL {self.__Settings.MAIN_SERVER_HOSTNAME} {sasl_obj.client_uid} C +")

                    self.on_sasl_authentication_process(sasl_obj)
                    return sasl_obj

                case 'C':
                    if sasl_obj.mechanisme == "PLAIN":
                        credentials = sCopy[5]
                        decoded_credentials = b64decode(credentials).decode()
                        user, username, password = decoded_credentials.split('\0')

                        sasl_obj.message_type = sasl_message_type
                        sasl_obj.username = username
                        sasl_obj.password = password

                        self.on_sasl_authentication_process(sasl_obj)
                        return sasl_obj
                    elif sasl_obj.mechanisme == "EXTERNAL":
                        sasl_obj.message_type = sasl_message_type

                        self.on_sasl_authentication_process(sasl_obj)
                        return sasl_obj

        except Exception as err:
            self.__Logs.error(f'General Error: {err}', exc_info=True)

    def on_sasl_authentication_process(self, sasl_model: 'MSasl') -> bool:
        s = sasl_model
        if sasl_model:
            def db_get_admin_info(*, username: Optional[str] = None, password: Optional[str] = None, fingerprint: Optional[str] = None) -> Optional[dict[str, Any]]:
                if fingerprint:
                    mes_donnees = {'fingerprint': fingerprint}
                    query = f"SELECT user, level, language FROM {self.__Config.TABLE_ADMIN} WHERE fingerprint = :fingerprint"
                else:
                    mes_donnees = {'user': username, 'password': self.__Utils.hash_password(password)}
                    query = f"SELECT user, level, language FROM {self.__Config.TABLE_ADMIN} WHERE user = :user AND password = :password"

                result = self.__Base.db_execute_query(query, mes_donnees)
                user_from_db = result.fetchone()
                if user_from_db:
                    return {'user': user_from_db[0], 'level': user_from_db[1], 'language': user_from_db[2]}
                else:
                    return None

            if s.message_type == 'C' and s.mechanisme == 'PLAIN':
                # Connection via PLAIN
                admin_info = db_get_admin_info(username=s.username, password=s.password)
                if admin_info is not None:
                    s.auth_success = True
                    s.level = admin_info.get('level', 0)
                    s.language = admin_info.get('language', 'EN')
                    self.send2socket(f":{self.__Config.SERVEUR_LINK} SASL {self.__Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D S")
                    self.send2socket(f":{self.__Config.SERVEUR_LINK} 903 {s.username} :SASL authentication successful")
                else:
                    self.send2socket(f":{self.__Config.SERVEUR_LINK} SASL {self.__Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D F")
                    self.send2socket(f":{self.__Config.SERVEUR_LINK} 904 {s.username} :SASL authentication failed")

            elif s.message_type == 'S' and s.mechanisme == 'EXTERNAL':
                # Connection using fingerprints
                admin_info = db_get_admin_info(fingerprint=s.fingerprint)
                
                if admin_info is not None:
                    s.auth_success = True
                    s.level = admin_info.get('level', 0)
                    s.username = admin_info.get('user', None)
                    s.language = admin_info.get('language', 'EN')
                    self.send2socket(f":{self.__Config.SERVEUR_LINK} SASL {self.__Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D S")
                    self.send2socket(f":{self.__Config.SERVEUR_LINK} 903 {s.username} :SASL authentication successful")
                else:
                    # "904 <nick> :SASL authentication failed"
                    self.send2socket(f":{self.__Config.SERVEUR_LINK} SASL {self.__Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D F")
                    self.send2socket(f":{self.__Config.SERVEUR_LINK} 904 {s.username} :SASL authentication failed")

    def on_md(self, serverMsg: list[str]) -> None:
        """Handle MD responses
        [':001', 'MD', 'client', '001MYIZ03', 'certfp', ':d1235648...']
        Args:
            serverMsg (list[str]): The server reply
        """
        try:
            scopy = serverMsg.copy()
            available_vars = ['creationtime', 'certfp', 'tls_cipher']

            uid = str(scopy[3])
            var = str(scopy[4]).lower()
            value = str(scopy[5]).replace(':', '')

            user_obj = self.__Irc.User.get_user(uid)
            if user_obj is None:
                return None
            
            match var:
                case 'certfp':
                    user_obj.fingerprint = value
                case 'tls_cipher':
                    user_obj.tls_cipher = value
                case _:
                    return None

            ...
        except Exception as e:
            self.__Logs.error(f"General Error: {e}")