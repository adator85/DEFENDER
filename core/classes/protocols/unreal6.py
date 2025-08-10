from re import match, findall, search
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union
from ssl import SSLEOFError, SSLError

if TYPE_CHECKING:
    from core.irc import Irc

class Unrealircd6:

    def  __init__(self, ircInstance: 'Irc'):
        self.name = 'UnrealIRCD-6'
        self.protocol_version = 6100

        self.__Irc = ircInstance
        self.__Config = ircInstance.Config
        self.__Base = ircInstance.Base
        self.__Settings = ircInstance.Base.Settings

        self.known_protocol: set[str] = {'SJOIN', 'UID', 'MD', 'QUIT', 'SQUIT',
                               'EOS', 'PRIVMSG', 'MODE', 'UMODE2', 
                               'VERSION', 'REPUTATION', 'SVS2MODE', 
                               'SLOG', 'NICK', 'PART', 'PONG'}

        self.__Base.logs.info(f"** Loading protocol [{__name__}]")

    def get_ircd_protocol_poisition(self, cmd: list[str]) -> tuple[int, Optional[str]]:

        for index, token in enumerate(cmd):
            if token.upper() in self.known_protocol:
                return index, token.upper()
        
        return (-1, None)

    def send2socket(self, message: str, print_log: bool = True) -> None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            string (Str): contient la commande à envoyer au serveur.
        """
        try:
            with self.__Base.lock:
                self.__Irc.IrcSocket.send(f"{message}\r\n".encode(self.__Config.SERVEUR_CHARSET[0]))
                if print_log:
                    self.__Base.logs.debug(f'<< {message}')

        except UnicodeDecodeError as ude:
            self.__Base.logs.error(f'Decode Error try iso-8859-1 - {ude} - {message}')
            self.__Irc.IrcSocket.send(f"{message}\r\n".encode(self.__Config.SERVEUR_CHARSET[1],'replace'))
        except UnicodeEncodeError as uee:
            self.__Base.logs.error(f'Encode Error try iso-8859-1 - {uee} - {message}')
            self.__Irc.IrcSocket.send(f"{message}\r\n".encode(self.__Config.SERVEUR_CHARSET[1],'replace'))
        except AssertionError as ae:
            self.__Base.logs.warning(f'Assertion Error {ae} - message: {message}')
        except SSLEOFError as soe:
            self.__Base.logs.error(f"SSLEOFError: {soe} - {message}")
        except SSLError as se:
            self.__Base.logs.error(f"SSLError: {se} - {message}")
        except OSError as oe:
            self.__Base.logs.error(f"OSError: {oe} - {message}")
        except AttributeError as ae:
            self.__Base.logs.critical(f"Attribute Error: {ae}")

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
            User_from       = self.__Irc.User.get_User(nick_from)
            User_to         = self.__Irc.User.get_User(nick_to) if not nick_to is None else None

            if User_from is None:
                self.__Base.logs.error(f"The sender nickname [{nick_from}] do not exist")
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
            self.__Base.logs.error(f"General Error: {err}")
            self.__Base.logs.error(f"General Error: {nick_from} - {channel} - {nick_to}")

    def send_notice(self, nick_from: str, nick_to: str, msg: str) -> None:
        """Sending NOTICE by batches

        Args:
            msg (str): The message to send to the server
            nick_from (str): The sender Nickname
            nick_to (str): The reciever nickname
        """
        try:
            batch_size  = self.__Config.BATCH_SIZE
            User_from   = self.__Irc.User.get_User(nick_from)
            User_to     = self.__Irc.User.get_User(nick_to)

            if User_from is None or User_to is None:
                self.__Base.logs.error(f"The sender [{nick_from}] or the Reciever [{nick_to}] do not exist")
                return None

            for i in range(0, len(str(msg)), batch_size):
                batch = str(msg)[i:i+batch_size]
                self.send2socket(f":{User_from.uid} NOTICE {User_to.uid} :{batch}")

        except Exception as err:
            self.__Base.logs.error(f"General Error: {err}")

    def parse_server_msg(self, server_msg: list[str]) -> Union[str, None]:
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

    def link(self):
        """Créer le link et envoyer les informations nécessaires pour la 
        connexion au serveur.
        """

        nickname = self.__Config.SERVICE_NICKNAME
        username = self.__Config.SERVICE_USERNAME
        realname = self.__Config.SERVICE_REALNAME
        chan = self.__Config.SERVICE_CHANLOG
        info = self.__Config.SERVICE_INFO
        smodes = self.__Config.SERVICE_SMODES
        cmodes = self.__Config.SERVICE_CMODES
        umodes = self.__Config.SERVICE_UMODES
        host = self.__Config.SERVICE_HOST
        service_name = self.__Config.SERVICE_NAME
        protocolversion = self.protocol_version

        password = self.__Config.SERVEUR_PASSWORD
        link = self.__Config.SERVEUR_LINK
        server_id = self.__Config.SERVEUR_ID
        service_id = self.__Config.SERVICE_ID

        version = self.__Config.CURRENT_VERSION
        unixtime = self.__Base.get_unixtime()

        self.send2socket(f":{server_id} PASS :{password}", print_log=False)
        self.send2socket(f":{server_id} PROTOCTL SID NOQUIT NICKv2 SJOIN SJ3 NICKIP TKLEXT2 NEXTBANS CLK EXTSWHOIS MLOCK MTAGS")
        self.send2socket(f":{server_id} PROTOCTL EAUTH={link},{protocolversion},,{service_name}-v{version}")
        self.send2socket(f":{server_id} PROTOCTL SID={server_id}")
        self.send2socket(f":{server_id} PROTOCTL BOOTED={unixtime}")
        self.send2socket(f":{server_id} SERVER {link} 1 :{info}")
        self.send2socket(f":{server_id} {nickname} :Reserved for services")
        self.send2socket(f":{server_id} UID {nickname} 1 {unixtime} {username} {host} {service_id} * {smodes} * * fwAAAQ== :{realname}")
        self.sjoin(chan)
        self.send2socket(f":{server_id} TKL + Q * {nickname} {host} 0 {unixtime} :Reserved for services")
        self.send2socket(f":{service_id} MODE {chan} {cmodes}")

        self.__Base.logs.debug(f'>> {__name__} Link information sent to the server')

    def gline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + G user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL + G {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def set_nick(self, newnickname: str) -> None:
        """Change nickname of the server
        \n This method will also update the User object
        Args:
            newnickname (str): New nickname of the server
        """
        self.send2socket(f":{self.__Config.SERVICE_NICKNAME} NICK {newnickname}")

        userObj = self.__Irc.User.get_User(self.__Config.SERVICE_NICKNAME)
        self.__Irc.User.update_nickname(userObj.uid, newnickname)
        return None

    def squit(self, server_id: str, server_link: str, reason: str) -> None:

        if not reason:
            reason = 'Service Shutdown'

        self.send2socket(f":{server_id} SQUIT {server_link} :{reason}")
        return None

    def ungline(self, nickname:str, hostname: str) -> None:

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL - G {nickname} {hostname} {self.__Config.SERVICE_NICKNAME}")

        return None

    def kline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + k user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL + k {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def unkline(self, nickname:str, hostname: str) -> None:

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL - K {nickname} {hostname} {self.__Config.SERVICE_NICKNAME}")

        return None

    def sjoin(self, channel: str) -> None:
        """Server will join a channel with pre defined umodes

        Args:
            channel (str): Channel to join
        """
        if not self.__Irc.Channel.Is_Channel(channel):
            self.__Base.logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{self.__Config.SERVEUR_ID} SJOIN {self.__Base.get_unixtime()} {channel} {self.__Config.SERVICE_UMODES} :{self.__Config.SERVICE_ID}")
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

            userObj = self.__Irc.User.get_User(uidornickname=nick_to_sapart)
            chanObj = self.__Irc.Channel.get_Channel(channel_name)
            service_uid = self.__Config.SERVICE_ID

            if userObj is None or chanObj is None:
                return None

            self.send2socket(f":{service_uid} SAPART {userObj.nickname} {chanObj.name}")
            self.__Irc.Channel.delete_user_from_channel(chanObj.name, userObj.uid)

            return None

        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def send_sajoin(self, nick_to_sajoin: str, channel_name: str) -> None:
        """_summary_

        Args:
            nick_to_sajoin (str): _description_
            channel_name (str): _description_
        """
        try:

            userObj = self.__Irc.User.get_User(uidornickname=nick_to_sajoin)
            chanObj = self.__Irc.Channel.get_Channel(channel_name)
            service_uid = self.__Config.SERVICE_ID

            if userObj is None:
                # User not exist: leave
                return None

            if chanObj is None:
                # Channel not exist
                if not self.__Irc.Channel.Is_Channel(channel_name):
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
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def send_svs_mode(self, nickname: str, user_mode: str) -> None:
        try:

            userObj = self.__Irc.User.get_User(uidornickname=nickname)
            service_uid = self.__Config.SERVICE_ID

            if userObj is None:
                # User not exist: leave
                return None

            self.send2socket(f':{service_uid} SVSMODE {nickname} {user_mode}')

            # Update new mode
            self.__Irc.User.update_mode(userObj.uid, user_mode)

            return None
        except Exception as err:
                self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def send_quit(self, uid: str, reason: str, print_log: True) -> None:
        """Send quit message
        - Delete uid from User object
        - Delete uid from Reputation object

        Args:
            uidornickname (str): The UID or the Nickname
            reason (str): The reason for the quit
        """
        user_obj = self.__Irc.User.get_User(uidornickname=uid)
        reputationObj = self.__Irc.Reputation.get_Reputation(uidornickname=uid)

        if not user_obj is None:
            self.send2socket(f":{user_obj.uid} QUIT :{reason}", print_log=print_log)
            self.__Irc.User.delete(user_obj.uid)

        if not reputationObj is None:
            self.__Irc.Reputation.delete(reputationObj.uid)

        if not self.__Irc.Channel.delete_user_from_all_channel(uid):
            self.__Base.logs.error(f"The UID [{uid}] has not been deleted from all channels")

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
        # {clone.nickname} 1 {self.Base.get_unixtime()} {clone.username} {clone.hostname} {clone.uid} * {clone.umodes}  {clone.vhost} * {self.Base.encode_ip(clone.remote_ip)} :{clone.realname}
        try:
            unixtime = self.__Base.get_unixtime()
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
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def send_join_chan(self, uidornickname: str, channel: str, password: str = None, print_log: bool = True) -> None:
        """Joining a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            password (str, optional): The password of the channel to join. Default to None
            print_log (bool, optional): Write logs. Defaults to True.
        """

        userObj = self.__Irc.User.get_User(uidornickname)
        passwordChannel = password if not password is None else ''

        if userObj is None:
            return None

        if not self.__Irc.Channel.Is_Channel(channel):
            self.__Base.logs.error(f"The channel [{channel}] is not valid")
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

        userObj = self.__Irc.User.get_User(uidornickname)

        if userObj is None:
            self.__Base.logs.error(f"The user [{uidornickname}] is not valid")
            return None

        if not self.__Irc.Channel.Is_Channel(channel):
            self.__Base.logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{userObj.uid} PART {channel}", print_log=print_log)

        # Add defender to the channel uids list
        self.__Irc.Channel.delete_user_from_channel(channel, userObj.uid)
        return None

    def send_mode_chan(self, channel_name: str, channel_mode: str) -> None:

        channel = self.__Irc.Channel.Is_Channel(channel_name)
        if not channel:
            self.__Base.logs.error(f'The channel [{channel_name}] is not correct')
            return None

        self.send2socket(f":{self.__Config.SERVICE_NICKNAME} MODE {channel_name} {channel_mode}")
        return None

    def send_raw(self, raw_command: str) -> None:

        self.send2socket(f":{self.__Config.SERVICE_NICKNAME} {raw_command}")

        return None

    #####################
    #   HANDLE EVENTS   #
    #####################

    def on_svs2mode(self, serverMsg: list[str]) -> None:
        """Handle svs2mode coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # >> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']

            uid_user_to_edit = serverMsg[2]
            umode = serverMsg[3]

            userObj = self.__Irc.User.get_User(uid_user_to_edit)

            if userObj is None:
                return None

            if self.__Irc.User.update_mode(userObj.uid, umode):
                return None

            return None
        except IndexError as ie:
            self.__Base.logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # [':adator_', 'UMODE2', '-iwx']

            userObj  = self.__Irc.User.get_User(str(serverMsg[0]).lstrip(':'))
            userMode = serverMsg[2]

            if userObj is None: # If user is not created
                return None

            # save previous user modes
            old_umodes = userObj.umodes

            # TODO : User object should be able to update user modes
            if self.__Irc.User.update_mode(userObj.uid, userMode):
                return None
                # self.__Base.logs.debug(f"Updating user mode for [{userObj.nickname}] [{old_umodes}] => [{userObj.umodes}]")

            return None

        except IndexError as ie:
            self.__Base.logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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

            return None

        except IndexError as ie:
            self.__Base.logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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

            return None

        except IndexError as ie:
            self.__Base.logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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
                clean_uid = self.__Irc.User.clean_uid(parsed_UID)
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
            self.__Base.logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def on_part(self, serverMsg: list[str]) -> None:
        """Handle part coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """
        try:
            # ['@unrealircd.org/geoip=FR;unrealircd.org/userhost=50d6492c@80.214.73.44;unrealircd.org/userip=50d6492c@80.214.73.44;msgid=YSIPB9q4PcRu0EVfC9ci7y-/mZT0+Gj5FLiDSZshH5NCw;time=2024-08-15T15:35:53.772Z', 
            # ':001EPFBRD', 'PART', '#welcome', ':WEB', 'IRC', 'Paris']

            uid = str(serverMsg[1]).lstrip(':')
            channel = str(serverMsg[3]).lower()
            self.__Irc.Channel.delete_user_from_channel(channel, uid)

            return None

        except IndexError as ie:
            self.__Base.logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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

                    self.__Base.logs.info(f"################### DEFENDER ###################")
                    self.__Base.logs.info(f"#               SERVICE CONNECTE                ")
                    self.__Base.logs.info(f"# SERVEUR  :    {self.__Config.SERVEUR_IP}        ")
                    self.__Base.logs.info(f"# PORT     :    {self.__Config.SERVEUR_PORT}      ")
                    self.__Base.logs.info(f"# SSL      :    {self.__Config.SERVEUR_SSL}       ")
                    self.__Base.logs.info(f"# SSL VER  :    {self.__Config.SSL_VERSION}       ")
                    self.__Base.logs.info(f"# NICKNAME :    {self.__Config.SERVICE_NICKNAME}  ")
                    self.__Base.logs.info(f"# CHANNEL  :    {self.__Config.SERVICE_CHANLOG}   ")
                    self.__Base.logs.info(f"# VERSION  :    {version}                       ")
                    self.__Base.logs.info(f"################################################")

                    if self.__Base.check_for_new_version(False):
                        self.send_priv_msg(
                            nick_from=self.__Config.SERVICE_NICKNAME,
                            msg=f" New Version available {version}",
                            channel=self.__Config.SERVICE_CHANLOG
                        )

                # Initialisation terminé aprés le premier PING
                self.send_priv_msg(
                    nick_from=self.__Config.SERVICE_NICKNAME,
                    msg=f"[{self.__Config.COLORS.green}INFORMATION{self.__Config.COLORS.nogc}] >> Defender is ready",
                    channel=self.__Config.SERVICE_CHANLOG
                )
                self.__Config.DEFENDER_INIT = 0

                # Send EOF to other modules
                for classe_name, classe_object in self.__Irc.loaded_classes.items():
                    classe_object.cmd(server_msg_copy)

                return None
        except IndexError as ie:
            self.__Base.logs.error(f"{__name__} - Key Error: {ie}")
        except KeyError as ke:
            self.__Base.logs.error(f"{__name__} - Key Error: {ke}")
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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
            self.Logs.error(f'Index Error {__name__}: {ie}')
        except ValueError as ve:
            self.__Irc.first_score = 0
            self.Logs.error(f'Value Error {__name__}: {ve}')
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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
                    isWebirc=isWebirc,
                    isWebsocket=isWebsocket,
                    remote_ip=remote_ip,
                    geoip=geoip,
                    score_connexion=score_connexion,
                    connexion_datetime=datetime.now()
                )
            )
            return None
        except IndexError as ie:
            self.__Base.logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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

            # Hide auth logs
            if len(cmd) == 7:
                if cmd[2] == 'PRIVMSG' and cmd[4] == ':auth':
                    data_copy = cmd.copy()
                    data_copy[6] = '**********'
                    self.__Base.logs.debug(f">> {data_copy}")
                else:
                    self.__Base.logs.debug(f">> {cmd}")
            else:
                self.__Base.logs.debug(f">> {cmd}")

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
                if not arg[0].lower() in self.__Irc.module_commands_list:
                    self.__Base.logs.debug(f"This command {arg[0]} is not available")
                    self.send_notice(
                        nick_from=self.__Config.SERVICE_NICKNAME,
                        nick_to=user_trigger,
                        msg=f"This command [{self.__Config.COLORS.bold}{arg[0]}{self.__Config.COLORS.bold}] is not available"
                    )
                    return None

                cmd_to_send = convert_to_string.replace(':','')
                self.__Base.log_cmd(user_trigger, cmd_to_send)

                fromchannel = str(cmd[2]).lower() if self.__Irc.Channel.Is_Channel(cmd[2]) else None
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
                        return False

                    # Réponse a un TIME
                    if arg[0] == '\x01TIME\x01':
                        self.on_time(srv_msg)
                        return False

                    # Réponse a un PING
                    if arg[0] == '\x01PING':
                        self.on_ping(srv_msg)
                        return False

                    if not arg[0].lower() in self.__Irc.module_commands_list:
                        self.__Base.logs.debug(f"This command {arg[0]} sent by {user_trigger} is not available")
                        return False

                    cmd_to_send = convert_to_string.replace(':','')
                    self.__Base.log_cmd(user_trigger, cmd_to_send)

                    fromchannel = None
                    if len(arg) >= 2:
                        fromchannel = str(arg[1]).lower() if self.__Irc.Channel.Is_Channel(arg[1]) else None

                    self.__Irc.hcmds(user_trigger, fromchannel, arg, cmd)
            return None

        except KeyError as ke:
            self.__Base.logs.error(f"Key Error: {ke}")
        except AttributeError as ae:
            self.__Base.logs.error(f"Attribute Error: {ae}")
        except Exception as err:
            self.__Base.logs.error(f"General Error: {err} - {srv_msg}")

    def on_server_ping(self, serverMsg: list[str]) -> None:
        """Send a PONG message to the server

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        try:
            # 
            pong = str(serverMsg[1]).replace(':','')
            self.send2socket(f"PONG :{pong}", print_log=False)

            return None
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def on_version(self, serverMsg: list[str]) -> None:
        """Sending Server Version to the server

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':00BAAAAAI', 'PRIVMSG', '12ZAAAAAB', ':\x01VERSION\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self.__Irc.User.get_nickname(self.__Base.clean_uid(serverMsg[1]))
            dnickname = self.__Config.SERVICE_NICKNAME
            arg = serverMsg[4].replace(':', '')

            if nickname is None:
                return None

            if arg == '\x01VERSION\x01':
                self.send2socket(f':{dnickname} NOTICE {nickname} :\x01VERSION Service {self.__Config.SERVICE_NICKNAME} V{self.__Config.CURRENT_VERSION}\x01')

            return None
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def on_time(self, serverMsg: list[str]) -> None:
        """Sending TIME answer to a requestor

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':00BAAAAAI', 'PRIVMSG', '12ZAAAAAB', ':\x01TIME\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self.__Irc.User.get_nickname(self.__Base.clean_uid(serverMsg[1]))
            dnickname = self.__Config.SERVICE_NICKNAME
            arg = serverMsg[4].replace(':', '')
            current_datetime = self.__Base.get_datetime()

            if nickname is None:
                return None

            if arg == '\x01TIME\x01':
                self.send2socket(f':{dnickname} NOTICE {nickname} :\x01TIME {current_datetime}\x01')

            return None
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def on_ping(self, serverMsg: list[str]) -> None:
        """Sending a PING answer to requestor

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':001INC60B', 'PRIVMSG', '12ZAAAAAB', ':\x01PING', '762382207\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self.__Irc.User.get_nickname(self.__Base.clean_uid(serverMsg[1]))
            dnickname = self.__Config.SERVICE_NICKNAME
            arg = serverMsg[4].replace(':', '')

            if nickname is None:
                return None

            if arg == '\x01PING':
                recieved_unixtime = int(serverMsg[5].replace('\x01',''))
                current_unixtime = self.__Base.get_unixtime()
                ping_response = current_unixtime - recieved_unixtime

                # self.__Irc.send2socket(f':{dnickname} NOTICE {nickname} :\x01PING {ping_response} secs\x01')
                self.send_notice(
                    nick_from=dnickname,
                    nick_to=nickname,
                    msg=f"\x01PING {ping_response} secs\x01"
                )

            return None
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

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

            getUser  = self.__Irc.User.get_User(self.__Irc.User.clean_uid(serverMsg_copy[0]))

            if getUser is None:
                return None

            response_351 = f"{self.__Config.SERVICE_NAME.capitalize()}-{self.__Config.CURRENT_VERSION} {self.__Config.SERVICE_HOST} {self.name}"
            self.send2socket(f':{self.__Config.SERVICE_HOST} 351 {getUser.nickname} {response_351}')

            modules = self.__Base.get_all_modules()
            response_005 = ' | '.join(modules)
            self.send2socket(f':{self.__Config.SERVICE_HOST} 005 {getUser.nickname} {response_005} are supported by this server')

            response_005 = ''.join(self.__Settings.PROTOCTL_USER_MODES)
            self.send2socket(f":{self.__Config.SERVICE_HOST} 005 {getUser.nickname} {response_005} are supported by this server")

            return None

        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")
