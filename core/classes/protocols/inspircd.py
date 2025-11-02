import sys
from base64 import b64decode
from re import match, findall, search
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from ssl import SSLEOFError, SSLError
from core.classes.protocols.interface import IProtocol
from core.utils import tr

if TYPE_CHECKING:
    from core.definition import MSasl, MClient, MUser, MChannel

class Inspircd(IProtocol):

    def init_protocol(self):
        self.name = 'InspIRCd-4'
        self.protocol_version = 1206

        self.known_protocol: set[str] = {'UID', 'ERROR', 'PRIVMSG',
                                         'SINFO', 'FJOIN', 'PING', 'PONG',
                                         'SASL', 'PART', 'CAPAB', 'ENDBURST',
                                         'METADATA', 'NICK',
                                         'MODE', 'QUIT', 'SQUIT',
                                         'VERSION'}

    def get_ircd_protocol_poisition(self, cmd: list[str], log: bool = False) -> tuple[int, Optional[str]]:
        """Get the position of known commands

        Args:
            cmd (list[str]): The server response
            log (bool): if True then print logs

        Returns:
            tuple[int, Optional[str]]: The position and the command.
        """
        for index, token in enumerate(cmd):
            if token.upper() in self.known_protocol:
                return index, token.upper()

        if log:
            self._Logs.debug(f"[IRCD LOGS] You need to handle this response: {cmd}")

        return -1, None

    def register_command(self):
        m = self._Irc.Loader.Definition.MIrcdCommand
        self.Handler.register(m('PING', self.on_server_ping))
        self.Handler.register(m('NICK', self.on_nick))
        self.Handler.register(m('SASL', self.on_sasl))
        self.Handler.register(m('SINFO', self.on_server))
        self.Handler.register(m('UID', self.on_uid))
        self.Handler.register(m('QUIT', self.on_quit))
        self.Handler.register(m('FJOIN', self.on_sjoin))
        self.Handler.register(m('PART', self.on_part))
        self.Handler.register(m('PRIVMSG', self.on_privmsg))
        self.Handler.register(m('ERROR', self.on_error))
        self.Handler.register(m('CAPAB', self.on_protoctl))
        self.Handler.register(m('ENDBURST', self.on_endburst))
        self.Handler.register(m('METADATA', self.on_metedata))

    def send2socket(self, message: str, print_log: bool = True) -> None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            message (str): The message to send to the socket.
            print_log (bool): if True print the log.
        """
        try:
            with self._Base.lock:
                self._Irc.IrcSocket.send(f"{message}\r\n".encode(self._Config.SERVEUR_CHARSET[0]))
                if print_log:
                    self._Logs.debug(f'<< {message}')

        except UnicodeDecodeError as ude:
            self._Logs.error(f'Decode Error try iso-8859-1 - {ude} - {message}')
            self._Irc.IrcSocket.send(f"{message}\r\n".encode(self._Config.SERVEUR_CHARSET[1],'replace'))
        except UnicodeEncodeError as uee:
            self._Logs.error(f'Encode Error try iso-8859-1 - {uee} - {message}')
            self._Irc.IrcSocket.send(f"{message}\r\n".encode(self._Config.SERVEUR_CHARSET[1],'replace'))
        except AssertionError as ae:
            self._Logs.warning(f'Assertion Error {ae} - message: {message}')
        except SSLEOFError as soe:
            self._Logs.error(f"SSLEOFError: {soe} - {message}")
        except SSLError as se:
            self._Logs.error(f"SSLError: {se} - {message}")
        except OSError as oe:
            self._Logs.error(f"OSError: {oe} - {message}")
            if oe.errno == 10053:
                sys.exit(oe.__str__())
        except AttributeError as ae:
            self._Logs.critical(f"Attribute Error: {ae}")

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
            batch_size   = self._Config.BATCH_SIZE
            user_from    = self._Irc.User.get_user(nick_from)
            user_to      = self._Irc.User.get_user(nick_to) if nick_to is not None else None

            if user_from is None:
                self._Logs.error(f"The sender nickname [{nick_from}] do not exist")
                return None

            if not channel is None:
                for i in range(0, len(str(msg)), batch_size):
                    batch = str(msg)[i:i+batch_size]
                    self.send2socket(f":{user_from.uid} PRIVMSG {channel} :{batch}")

            if not nick_to is None:
                for i in range(0, len(str(msg)), batch_size):
                    batch = str(msg)[i:i+batch_size]
                    self.send2socket(f":{nick_from} PRIVMSG {user_to.uid} :{batch}")
        except Exception as err:
            self._Logs.error(f"General Error: {err}")

    def send_notice(self, nick_from: str, nick_to: str, msg: str) -> None:
        """Sending NOTICE by batches

        Args:
            msg (str): The message to send to the server
            nick_from (str): The sender Nickname
            nick_to (str): The reciever nickname
        """
        try:
            batch_size  = self._Config.BATCH_SIZE
            user_from   = self._Irc.User.get_user(nick_from)
            user_to     = self._Irc.User.get_user(nick_to)

            if user_from is None or user_to is None:
                self._Logs.error(f"The sender [{nick_from}] or the Reciever [{nick_to}] do not exist")
                return None

            for i in range(0, len(str(msg)), batch_size):
                batch = str(msg)[i:i+batch_size]
                self.send2socket(f":{user_from.uid} NOTICE {user_to.uid} :{batch}")

        except Exception as err:
            self._Logs.error(f"General Error: {err}")

    def send_link(self):
        """Créer le link et envoyer les informations nécessaires pour la 
        connexion au serveur.
        """
        service_id = self._Config.SERVICE_ID
        service_nickname = self._Config.SERVICE_NICKNAME
        service_username = self._Config.SERVICE_USERNAME
        service_realname = self._Config.SERVICE_REALNAME
        service_info = self._Config.SERVICE_INFO
        service_smodes = self._Config.SERVICE_SMODES
        service_hostname = self._Config.SERVICE_HOST
        service_name = self._Config.SERVICE_NAME

        server_password = self._Config.SERVEUR_PASSWORD
        server_link = self._Config.SERVEUR_LINK
        server_id = self._Config.SERVEUR_ID
        server_hostname = self._Settings.MAIN_SERVER_HOSTNAME = self._Config.SERVEUR_HOSTNAME

        version = self._Config.CURRENT_VERSION
        unixtime = self._Utils.get_unixtime()

        self.send2socket(f"CAPAB START {self.protocol_version}")
        self.send2socket(f"CAPAB MODULES :services")
        self.send2socket(f"CAPAB MODSUPPORT :")
        self.send2socket(f"CAPAB CAPABILITIES :NICKMAX=30 CHANMAX=64 MAXMODES=20 IDENTMAX=10 MAXQUIT=255 MAXTOPIC=307 MAXKICK=255 MAXREAL=128 MAXAWAY=200 MAXHOST=64 MAXLINE=512 CASEMAPPING=ascii GLOBOPS=0")
        self.send2socket(f"CAPAB END")
        self.send2socket(f"SERVER {server_link} {server_password} {server_id} :{service_info}")
        self.send2socket(f"BURST {unixtime}")
        self.send2socket(f":{server_id} SINFO version :{service_name}-{version.split('.')[0]}. {server_hostname} :")
        self.send2socket(f":{server_id} SINFO fullversion :{service_name}-{version}. {service_hostname} :")
        self.send2socket(f":{server_id} SINFO rawversion :{service_name}-{version}")
        self.send_uid(service_nickname, service_username, service_hostname, service_id, service_smodes, service_hostname, "127.0.0.1", service_realname)
        self.send2socket(f":{server_id} ENDBURST")
        # self.send_sjoin(chan)

        self._Logs.debug(f'>> {__name__} Link information sent to the server')

    def gline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + G user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self._Config.SERVEUR_ID} TKL + G {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def send_set_nick(self, newnickname: str) -> None:

        self.send2socket(f":{self._Config.SERVICE_NICKNAME} NICK {newnickname}")
        return None

    def send_set_mode(self, modes: str, *, nickname: Optional[str] = None, channel_name: Optional[str] = None, params: Optional[str] = None) -> None:
        """Set a mode to channel or to a nickname or for a user in a channel

        Args:
            modes (str): The selected mode
            nickname (Optional[str]): The nickname
            channel_name (Optional[str]): The channel name
            params (Optional[str]): Params to pass to the mode
        """
        service_id = self._Config.SERVICE_ID
        params = '' if params is None else params

        if modes[0] not in ['+', '-']:
            self._Logs.error(f"[MODE ERROR] The mode you have provided is missing the sign: {modes}")
            return None

        if nickname and channel_name:
            # :98KAAAAAB MODE #services +o defenderdev
            if not self._Irc.Channel.is_valid_channel(channel_name):
                self._Logs.error(f"[MODE ERROR] The channel is not valid: {channel_name}")
                return None

            if not all(mode in self._Settings.PROTOCTL_PREFIX_MODES_SIGNES for mode in list(modes.replace('+','').replace('-',''))):
                self._Logs.debug(f'[USERMODE UNVAILABLE] This mode {modes} is not available!')
                return None

            self.send2socket(f":{service_id} MODE {channel_name} {modes} {nickname}")
            return None
        
        if nickname and channel_name is None:
            # :98KAAAAAB MODE nickname +o
            if not all(mode in self._Settings.PROTOCTL_USER_MODES for mode in list(modes.replace('+','').replace('-',''))):
                self._Logs.debug(f'[USERMODE UNVAILABLE] This mode {modes} is not available!')
                return None

            self.send2socket(f":{service_id} MODE {nickname} {modes}")
            return None
        
        if nickname is None and channel_name:
            # :98KAAAAAB MODE #channel +o
            if not all(mode in self._Settings.PROTOCTL_CHANNEL_MODES for mode in list(modes.replace('+','').replace('-',''))):
                self._Logs.debug(f'[USERMODE UNVAILABLE] This mode {modes} is not available!')
                return None
                
            if not self._Irc.Channel.is_valid_channel(channel_name):
                self._Logs.error(f"[MODE ERROR] The channel is not valid: {channel_name}")
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

        self.send2socket(f":{self._Config.SERVEUR_ID} TKL - G {nickname} {hostname} {self._Config.SERVICE_NICKNAME}")

        return None

    def send_kline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + k user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self._Config.SERVEUR_ID} TKL + k {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def send_sjoin(self, channel: str) -> None:
        """Service join a channel

        Args:
            channel (str): The channel name.
        """
        server_id = self._Config.SERVEUR_ID
        service_nickname = self._Config.SERVICE_NICKNAME
        service_modes = self._Config.SERVICE_UMODES
        service_id = self._Config.SERVICE_ID

        if not self._Irc.Channel.is_valid_channel(channel):
            self._Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{server_id} FJOIN {channel} {self._Utils.get_unixtime()} :o, {service_id}")
        self.send_set_mode(service_modes, nickname=service_nickname, channel_name=channel)

        # Add defender to the channel uids list
        self._Irc.Channel.insert(self._Irc.Loader.Definition.MChannel(name=channel, uids=[service_id]))
        return None

    def send_quit(self, uid: str, reason: str, print_log: bool = True) -> None:
        """Send quit message

        Args:
            uid (str): The UID.
            reason (str): The reason for the quit
            print_log (bool): If True then print logs
        """
        user_obj = self._Irc.User.get_user(uidornickname=uid)
        reputation_obj = self._Irc.Reputation.get_reputation(uidornickname=uid)

        if not user_obj is None:
            self.send2socket(f":{user_obj.uid} QUIT :{reason}", print_log=print_log)
            self._Irc.User.delete(user_obj.uid)

        if not reputation_obj is None:
            self._Irc.Reputation.delete(reputation_obj.uid)

        if not self._Irc.Channel.delete_user_from_all_channel(uid):
            self._Logs.error(f"The UID [{uid}] has not been deleted from all channels")

        return None

    def send_uid(self, nickname:str, username: str, hostname: str, uid:str, umodes: str, vhost: str, remote_ip: str, realname: str, print_log: bool = True) -> None:
        """Send UID to the server
        [:<sid>] UID <uid> <ts> <nick> <real-host> <displayed-host> <real-user> <ip> <signon> <modes> [<mode-parameters>]+ :<real>
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
        # {clone.nickname} 1 {self._Utils.get_unixtime()} {clone.username} {clone.hostname} {clone.uid} * {clone.umodes}  {clone.vhost} * {self.Base.encode_ip(clone.remote_ip)} :{clone.realname}
        try:
            unixtime = self._Utils.get_unixtime()
            # encoded_ip = self._Base.encode_ip(remote_ip)
            new_umodes = []
            for mode in list(umodes.replace('+', '').replace('-', '')):
                if mode in self._Settings.PROTOCTL_USER_MODES:
                    new_umodes.append(mode)

            final_umodes = '+' + ''.join(new_umodes)

            # Create the user
            self._Irc.User.insert(
                self._Irc.Loader.Definition.MUser(
                            uid=uid, nickname=nickname, username=username, 
                            realname=realname,hostname=hostname, umodes=final_umodes,
                            vhost=vhost, remote_ip=remote_ip
                        )
                    )

            # [:<sid>] UID <uid> <ts> <nick> <real-host> <displayed-host> <real-user> <ip> <signon> <modes> [<mode-parameters>]+ :<real>
            # :98K UID 98KAAAAAB 1756932359 defenderdev defenderdev.deb.biz.st defenderdev.deb.biz.st Dev-PyDefender 127.0.0.1 1756932359 + :Dev Python Security
            # [':97K', 'UID', '97KAAAAAA', '1756926679', 'adator', '172.18.128.1', 'attila.example.org', '...', '...', '172.18.128.1', '1756926678', '+o', ':...']
            uid_msg = f":{self._Config.SERVEUR_ID} UID {uid} {unixtime} {nickname} {hostname} {vhost} {username} {username} {remote_ip} {unixtime} {final_umodes} :{realname}"
            self.send2socket(uid_msg, print_log=print_log)

            return None

        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def send_join_chan(self, uidornickname: str, channel: str, password: str = None, print_log: bool = True) -> None:
        """Joining a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            password (str, optional): The password of the channel to join. Default to None
            print_log (bool, optional): Write logs. Defaults to True.
        """

        user_obj = self._Irc.User.get_user(uidornickname)
        password_channel = password if not password is None else ''

        if user_obj is None:
            return None

        if not self._Irc.Channel.is_valid_channel(channel):
            self._Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{user_obj.uid} FJOIN {channel} {self._Utils.get_unixtime()} :,{user_obj.uid} {password_channel}", print_log=print_log)

        # Add defender to the channel uids list
        self._Irc.Channel.insert(self._Irc.Loader.Definition.MChannel(name=channel, uids=[user_obj.uid]))
        return None

    def send_part_chan(self, uidornickname:str, channel: str, print_log: bool = True) -> None:
        """Part from a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            print_log (bool, optional): Write logs. Defaults to True.
        """

        user_obj = self._Irc.User.get_user(uidornickname)

        if user_obj is None:
            self._Logs.error(f"The user [{uidornickname}] is not valid")
            return None

        if not self._Irc.Channel.is_valid_channel(channel):
            self._Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{user_obj.uid} PART {channel}", print_log=print_log)

        # Add defender to the channel uids list
        self._Irc.Channel.delete_user_from_channel(channel, user_obj.uid)
        return None

    def send_unkline(self, nickname:str, hostname: str) -> None:

        self.send2socket(f":{self._Config.SERVEUR_ID} TKL - K {nickname} {hostname} {self._Config.SERVICE_NICKNAME}")

        return None

    def send_raw(self, raw_command: str) -> None:

        self.send2socket(f":{self._Config.SERVEUR_ID} {raw_command}")
        return None

    # ------------------------------------------------------------------------
    #                           RECIEVED IRC MESSAGES
    # ------------------------------------------------------------------------

    def on_umode2(self, server_msg: list[str]) -> None:
        """Handle umode2 coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':adator_', 'UMODE2', '-iwx']

            user_obj  = self._Irc.User.get_user(str(server_msg[0]).lstrip(':'))
            user_mode = server_msg[2]

            if user_obj is None: # If user is not created
                return None

            # TODO : User object should be able to update user modes
            if self._Irc.User.update_mode(user_obj.uid, user_mode):
                return None
                # self._Logs.debug(f"Updating user mode for [{userObj.nickname}] [{old_umodes}] => [{userObj.umodes}]")

            return None

        except IndexError as ie:
            self._Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_quit(self, server_msg: list[str]) -> None:
        """Handle quit coming from a server
        >> [':97KAAAAAZ', 'QUIT', ':Quit:', '....']
        Args:
            server_msg (list[str]): Original server message
        """
        try:

            uid_who_quit = str(server_msg[0]).lstrip(':')

            self._Irc.Channel.delete_user_from_all_channel(uid_who_quit)
            self._Irc.User.delete(uid_who_quit)
            self._Irc.Reputation.delete(uid_who_quit)

            return None

        except IndexError as ie:
            self._Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_squit(self, server_msg: list[str]) -> None:
        """Handle squit coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        # ['@msgid=QOEolbRxdhpVW5c8qLkbAU;time=2024-09-21T17:33:16.547Z', 'SQUIT', 'defender.deb.biz.st', ':Connection', 'closed']

        server_hostname = server_msg[2]
        uid_to_delete = None
        for s_user in self._Irc.User.UID_DB:
            if s_user.hostname == server_hostname and 'S' in s_user.umodes:
                uid_to_delete = s_user.uid

        if uid_to_delete is None:
            return None

        self._Irc.User.delete(uid_to_delete)
        self._Irc.Channel.delete_user_from_all_channel(uid_to_delete)

        return None

    def on_protoctl(self, server_msg: list[str]) -> None:
        """Handle CAPAB coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        # ['CAPAB', 'CHANMODES', ':list:ban=b', 'param-set:limit=l', 'param:key=k', 'prefix:10000:voice=+v', 'prefix:30000:op=@o', 'prefix:50000:founder=~q', 
        # 'simple:c_registered=r', 'simple:inviteonly=i', 'simple:moderated=m', 'simple:noextmsg=n', 'simple:private=p', 
        # 'simple:secret=s', 'simple:sslonly=z', 'simple:topiclock=t']

        scopy = server_msg.copy()

        # Get Chan modes.
        if scopy[1] == 'CHANMODES':
            sign_mode = {}
            mode_sign = {}
            channel_modes = []
            for prefix in scopy:
                if prefix.startswith('prefix:'):
                    sign = prefix.split('=')[1][0] if len(prefix.split('=')) > 1 else None
                    mode = prefix.split('=')[1][1] if len(prefix.split('=')) > 1 else None
                    sign_mode[sign] = mode
                    mode_sign[mode] = sign

                if prefix.startswith('simple:') or prefix.startswith('param-set:') or prefix.startswith('param:'):
                    cmode = prefix.split('=')[1] if len(prefix.split('=')) > 1 else None
                    channel_modes.append(cmode)


            self._Settings.PROTOCTL_PREFIX_SIGNES_MODES = sign_mode
            self._Settings.PROTOCTL_PREFIX_MODES_SIGNES = mode_sign
            self._Settings.PROTOCTL_CHANNEL_MODES = list(set(channel_modes))
        
        # ['CAPAB', 'USERMODES', ':param-set:snomask=s', 'simple:bot=B', 'simple:invisible=i', 'simple:oper=o', 'simple:servprotect=k', 
        # 'simple:sslqueries=z', 'simple:u_registered=r', 'simple:wallops=w']
        # Get user modes
        if scopy[1] == 'USERMODES':
            user_modes = []
            for prefix in scopy:
                if prefix.startswith('param-set:') or prefix.startswith('simple:'):
                    umode = prefix.split('=')[1] if len(prefix.split('=')) > 1 else None
                    user_modes.append(umode)

            self._Settings.PROTOCTL_USER_MODES = list(set(user_modes))

        return None

    def on_nick(self, server_msg: list[str]) -> None:
        """Handle nick coming from a server
        new nickname

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':97KAAAAAF', 'NICK', 'test', '1757370509']
            # Changement de nickname

            scopy = server_msg.copy()
            if scopy[0].startswith('@'):
                scopy.pop(0)

            uid = str(scopy[0]).replace(':','')
            newnickname = scopy[2]
            self._Irc.User.update_nickname(uid, newnickname)
            self._Irc.Client.update_nickname(uid, newnickname)
            self._Irc.Admin.update_nickname(uid, newnickname)

            return None

        except IndexError as ie:
            self._Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_sjoin(self, server_msg: list[str]) -> None:
        """Handle sjoin coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':97K', 'FJOIN', '#services', '1757156589', '+nt', ':,97KAAAAA2:22', 'o,97KAAAAAA:2']

            channel = str(server_msg[2]).lower()
            list_users:list = []

            # Find uid's
            for uid in server_msg:
                matches = findall(r',([0-9A-Z]+):', uid)
                list_users.extend(matches)

            list_users = list(set(list_users))

            if list_users:
                self._Irc.Channel.insert(
                    self._Irc.Loader.Definition.MChannel(
                        name=channel,
                        uids=list_users
                    )
                )
            return None

        except IndexError as ie:
            self._Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_endburst(self, server_msg: list[str]) -> None:
        """Handle EOS coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':97K', 'ENDBURST']
            scopy = server_msg.copy()
            hsid = str(scopy[0]).replace(':','')
            if hsid == self._Config.HSID:
                if self._Config.DEFENDER_INIT == 1:
                    current_version = self._Config.CURRENT_VERSION
                    latest_version = self._Config.LATEST_VERSION
                    if self._Base.check_for_new_version(False):
                        version = f'{current_version} >>> {latest_version}'
                    else:
                        version = f'{current_version}'

                    print(f"################### DEFENDER ###################")
                    print(f"#               SERVICE CONNECTE                ")
                    print(f"# SERVEUR  :    {self._Config.SERVEUR_IP}        ")
                    print(f"# PORT     :    {self._Config.SERVEUR_PORT}      ")
                    print(f"# SSL      :    {self._Config.SERVEUR_SSL}       ")
                    print(f"# SSL VER  :    {self._Config.SSL_VERSION}       ")
                    print(f"# NICKNAME :    {self._Config.SERVICE_NICKNAME}  ")
                    print(f"# CHANNEL  :    {self._Config.SERVICE_CHANLOG}   ")
                    print(f"# VERSION  :    {version}                       ")
                    print(f"################################################")

                    self._Logs.info(f"################### DEFENDER ###################")
                    self._Logs.info(f"#               SERVICE CONNECTE                ")
                    self._Logs.info(f"# SERVEUR  :    {self._Config.SERVEUR_IP}        ")
                    self._Logs.info(f"# PORT     :    {self._Config.SERVEUR_PORT}      ")
                    self._Logs.info(f"# SSL      :    {self._Config.SERVEUR_SSL}       ")
                    self._Logs.info(f"# SSL VER  :    {self._Config.SSL_VERSION}       ")
                    self._Logs.info(f"# NICKNAME :    {self._Config.SERVICE_NICKNAME}  ")
                    self._Logs.info(f"# CHANNEL  :    {self._Config.SERVICE_CHANLOG}   ")
                    self._Logs.info(f"# VERSION  :    {version}                       ")
                    self._Logs.info(f"################################################")

                    self.send_sjoin(self._Config.SERVICE_CHANLOG)

                    if self._Base.check_for_new_version(False):
                        self.send_priv_msg(
                            nick_from=self._Config.SERVICE_NICKNAME,
                            msg=f" New Version available {version}",
                            channel=self._Config.SERVICE_CHANLOG
                        )

                # Initialisation terminé aprés le premier PING
                self.send_priv_msg(
                    nick_from=self._Config.SERVICE_NICKNAME,
                    msg=tr("[ %sINFORMATION%s ] >> %s is ready!", self._Config.COLORS.green, self._Config.COLORS.nogc, self._Config.SERVICE_NICKNAME),
                    channel=self._Config.SERVICE_CHANLOG
                )
                self._Config.DEFENDER_INIT = 0

                # Send EOF to other modules
                for module in self._Irc.ModuleUtils.model_get_loaded_modules().copy():
                    module.class_instance.cmd(scopy)
                
                # Join saved channels & load existing modules
                self._Irc.join_saved_channels()
                self._Irc.ModuleUtils.db_load_all_existing_modules(self._Irc)

                return None
        except IndexError as ie:
            self._Logs.error(f"{__name__} - Key Error: {ie}")
        except KeyError as ke:
            self._Logs.error(f"{__name__} - Key Error: {ke}")
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_part(self, server_msg: list[str]) -> None:
        """Handle part coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':97KAAAAA2', 'PART', '#v', ':"Closing', 'Window"']

            uid = str(server_msg[0]).lstrip(':')
            channel = str(server_msg[2]).lower()
            # reason = str(' '.join(server_msg[3:]))
            self._Irc.Channel.delete_user_from_channel(channel, uid)

            return None

        except IndexError as ie:
            self._Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_uid(self, server_msg: list[str]) -> None:
        """Handle uid message coming from the server
        [:<sid>] UID    <uid>       <ts>           <nick>     <real-host>     <displayed-host> <real-user> <displayed-user> <ip>            <signon>      <modes> [<mode-parameters>]+ :<real>
        [':97K', 'UID', '97KAAAAAB', '1756928055', 'adator_', '172.18.128.1', '172.18.128.1',  '...',      '...',           '172.18.128.1', '1756928055', '+', ':...']
        Args:
            server_msg (list[str]): Original server message
        """
        try:
            red = self._Config.COLORS.red
            green = self._Config.COLORS.green
            nogc = self._Config.COLORS.nogc
            is_webirc = True if 'webirc' in server_msg[0] else False
            is_websocket = True if 'websocket' in server_msg[0] else False

            uid = str(server_msg[2])
            nickname = str(server_msg[4])
            username = str(server_msg[7])
            hostname = str(server_msg[5])
            umodes = str(server_msg[11])
            vhost = str(server_msg[6])

            if not 'S' in umodes:
                # remote_ip = self._Base.decode_ip(str(serverMsg[9]))
                remote_ip = str(server_msg[9])
            else:
                remote_ip = '127.0.0.1'

            # extract realname
            realname = ' '.join(server_msg[12:]).lstrip(':')

            # Extract Geoip information
            pattern = r'^.*geoip=cc=(\S{2}).*$'
            geoip_match = match(pattern, server_msg[0])

            if geoip_match:
                geoip = geoip_match.group(1)
            else:
                geoip = None

            score_connexion = 0

            self._Irc.User.insert(
                self._Irc.Loader.Definition.MUser(
                    uid=uid,
                    nickname=nickname,
                    username=username,
                    realname=realname,
                    hostname=hostname,
                    umodes=umodes,
                    vhost=vhost,
                    isWebirc=is_webirc,
                    isWebsocket=is_websocket,
                    remote_ip=remote_ip,
                    geoip=geoip,
                    score_connexion=score_connexion,
                    connexion_datetime=datetime.now()
                )
            )

            for module in self._Irc.ModuleUtils.model_get_loaded_modules().copy():
                module.class_instance.cmd(server_msg)

            # SASL authentication
            dnickname = self._Config.SERVICE_NICKNAME
            dchanlog = self._Config.SERVICE_CHANLOG
            # uid = serverMsg[8]
            # nickname = serverMsg[3]
            sasl_obj = self._Irc.Sasl.get_sasl_obj(uid)
            if sasl_obj:
                if sasl_obj.auth_success:
                    self._Irc.insert_db_admin(sasl_obj.client_uid, sasl_obj.username, sasl_obj.level, sasl_obj.language)
                    self.send_priv_msg(nick_from=dnickname, 
                                        msg=tr("[ %sSASL AUTH%s ] - %s (%s) is now connected successfuly to %s", green, nogc, nickname, sasl_obj.username, dnickname),
                                        channel=dchanlog)
                    self.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Successfuly connected to %s", dnickname))
                else:
                    self.send_priv_msg(nick_from=dnickname, 
                                            msg=tr("[ %sSASL AUTH%s ] - %s provided a wrong password for this username %s", red, nogc, nickname, sasl_obj.username),
                                            channel=dchanlog)
                    self.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Wrong password!"))

                # Delete sasl object!
                self._Irc.Sasl.delete_sasl_client(uid)
                return None
            
            return None
        except IndexError as ie:
            self._Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}", exc_info=True)

    def on_privmsg(self, server_msg: list[str]) -> None:
        """Handle PRIVMSG message coming from the server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            srv_msg = server_msg.copy()
            cmd = server_msg.copy()
            # Supprimer la premiere valeur si MTAGS activé
            if cmd[0].startswith('@'):
                cmd.pop(0)

            get_uid_or_nickname = str(cmd[0].replace(':',''))
            user_trigger = self._Irc.User.get_nickname(get_uid_or_nickname)
            # dnickname = self._Config.SERVICE_NICKNAME
            pattern = fr'(:\{self._Config.SERVICE_PREFIX})(.*)$'
            hcmds = search(pattern, ' '.join(cmd)) # va matcher avec tout les caractéres aprés le .

            if hcmds: # Commande qui commencent par le point
                liste_des_commandes = list(hcmds.groups())
                convert_to_string = ' '.join(liste_des_commandes)
                arg = convert_to_string.split()
                arg.remove(f":{self._Config.SERVICE_PREFIX}")
                if not self._Irc.Commands.is_command_exist(arg[0]):
                    self._Logs.debug(f"This command {arg[0]} is not available")
                    self.send_notice(
                        nick_from=self._Config.SERVICE_NICKNAME,
                        nick_to=user_trigger,
                        msg=f"This command [{self._Config.COLORS.bold}{arg[0]}{self._Config.COLORS.bold}] is not available"
                    )
                    return None

                cmd_to_send = convert_to_string.replace(':','')
                self._Base.log_cmd(user_trigger, cmd_to_send)

                fromchannel = str(cmd[2]).lower() if self._Irc.Channel.is_valid_channel(cmd[2]) else None
                self._Irc.hcmds(user_trigger, fromchannel, arg, cmd)

            if cmd[2] == self._Config.SERVICE_ID:
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

                    if not self._Irc.Commands.is_command_exist(arg[0]):
                        self._Logs.debug(f"This command {arg[0]} sent by {user_trigger} is not available")
                        return None

                    # if not arg[0].lower() in self._Irc.module_commands_list:
                    #     self._Logs.debug(f"This command {arg[0]} sent by {user_trigger} is not available")
                    #     return False

                    cmd_to_send = convert_to_string.replace(':','')
                    self._Base.log_cmd(user_trigger, cmd_to_send)

                    fromchannel = None
                    if len(arg) >= 2:
                        fromchannel = str(arg[1]).lower() if self._Irc.Channel.is_valid_channel(arg[1]) else None

                    self._Irc.hcmds(user_trigger, fromchannel, arg, cmd)
            return None

        except KeyError as ke:
            self._Logs.error(f"Key Error: {ke}")
        except AttributeError as ae:
            self._Logs.error(f"Attribute Error: {ae}")
        except Exception as err:
            self._Logs.error(f"General Error: {err}", exc_info=True)

    def on_server_ping(self, server_msg: list[str]) -> None:
        """Send a PONG message to the server

        Args:
            server_msg (list[str]): List of str coming from the server
        """
        try:
            # InspIRCd 4:
            # <- :3IN PING 808
            # -> :808 PONG 3IN

            hsid = str(server_msg[0]).replace(':','')
            self.send2socket(f":{self._Config.SERVEUR_ID} PONG {hsid}", print_log=False)

            return None
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_server(self, server_msg: list[str]) -> None:
        """_summary_
        >>> [':97K', 'SINFO', 'customversion', ':']
        >>> [':97K', 'SINFO', 'rawbranch', ':InspIRCd-4']
        >>> [':97K', 'SINFO', 'rawversion', ':InspIRCd-4.8.0']
        Args:
            server_msg (list[str]): The server message
        """
        try:
            param = str(server_msg[2])
            self._Config.HSID = self._Settings.MAIN_SERVER_ID = str(server_msg[0]).replace(':', '')
            if param == 'rawversion':
                self._Logs.debug(f">> Server Version: {server_msg[3].replace(':', '')}")
            elif param == 'rawbranch':
                self._Logs.debug(f">> Branch Version: {server_msg[3].replace(':', '')}")

        except Exception as err:
            self._Logs.error(f'General Error: {err}')

    def on_version(self, server_msg: list[str]) -> None:
        """Sending Server Version to the server

        Args:
            server_msg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':00BAAAAAI', 'PRIVMSG', '12ZAAAAAB', ':\x01VERSION\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self._Irc.User.get_nickname(self._Utils.clean_uid(server_msg[1]))
            dnickname = self._Config.SERVICE_NICKNAME
            arg = server_msg[4].replace(':', '')

            if nickname is None:
                return None

            if arg == '\x01VERSION\x01':
                self.send2socket(f':{dnickname} NOTICE {nickname} :\x01VERSION Service {self._Config.SERVICE_NICKNAME} V{self._Config.CURRENT_VERSION}\x01')

            return None
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_time(self, server_msg: list[str]) -> None:
        """Sending TIME answer to a requestor

        Args:
            server_msg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':00BAAAAAI', 'PRIVMSG', '12ZAAAAAB', ':\x01TIME\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self._Irc.User.get_nickname(self._Utils.clean_uid(server_msg[1]))
            dnickname = self._Config.SERVICE_NICKNAME
            arg = server_msg[4].replace(':', '')
            current_datetime = self._Utils.get_sdatetime()

            if nickname is None:
                return None

            if arg == '\x01TIME\x01':
                self.send2socket(f':{dnickname} NOTICE {nickname} :\x01TIME {current_datetime}\x01')

            return None
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_ping(self, server_msg: list[str]) -> None:
        """Sending a PING answer to requestor

        Args:
            server_msg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':001INC60B', 'PRIVMSG', '12ZAAAAAB', ':\x01PING', '762382207\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self._Irc.User.get_nickname(self._Utils.clean_uid(server_msg[1]))
            dnickname = self._Config.SERVICE_NICKNAME
            arg = server_msg[4].replace(':', '')

            if nickname is None:
                return None

            if arg == '\x01PING':
                recieved_unixtime = int(server_msg[5].replace('\x01',''))
                current_unixtime = self._Utils.get_unixtime()
                ping_response = current_unixtime - recieved_unixtime

                # self._Irc.send2socket(f':{dnickname} NOTICE {nickname} :\x01PING {ping_response} secs\x01')
                self.send_notice(
                    nick_from=dnickname,
                    nick_to=nickname,
                    msg=f"\x01PING {ping_response} secs\x01"
                )

            return None
        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_version_msg(self, server_msg: list[str]) -> None:
        """Handle version coming from the server

        Args:
            server_msg (list[str]): Original message from the server
        """
        try:
            # ['@label=0073', ':0014E7P06', 'VERSION', 'PyDefender']
            user_obj  = self._Irc.User.get_user(self._Utils.clean_uid(server_msg[1]))

            if user_obj is None:
                return None

            response_351 = f"{self._Config.SERVICE_NAME.capitalize()}-{self._Config.CURRENT_VERSION} {self._Config.SERVICE_HOST} {self.name}"
            self.send2socket(f':{self._Config.SERVICE_HOST} 351 {user_obj.nickname} {response_351}')

            modules = self._Irc.ModuleUtils.get_all_available_modules()
            response_005 = ' | '.join(modules)
            self.send2socket(f':{self._Config.SERVICE_HOST} 005 {user_obj.nickname} {response_005} are supported by this server')

            return None

        except Exception as err:
            self._Logs.error(f"{__name__} - General Error: {err}")

    def on_sasl(self, server_msg: list[str]) -> Optional['MSasl']:
        """Handle SASL coming from a server

        Args:
            server_msg (list[str]): Original server message
        Returns:
            Optional[MSasl]: The MSasl object
        """
        try:
            # [':97K', 'ENCAP', '98K', 'SASL', '97KAAAAAF', '*', 'H', '172.18.128.1', '172.18.128.1', 'P']
            # [':97K', 'ENCAP', '98K', 'SASL', '97KAAAAAF', '*', 'S', 'PLAIN']
            # [':97K', 'ENCAP', '98K', 'SASL', '97KAAAAAP', 'irc.inspircd.local', 'C', 'YWRzefezfzefzefzefzefzefzefzezak=']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '0014ZZH1F', 'S', 'EXTERNAL', 'zzzzzzzkey']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'C', 'sasakey==']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'D', 'A']
            psasl = self._Irc.Sasl
            sasl_enabled = True # Should be False
            for smod in self._Settings.SMOD_MODULES:
                if smod.name == 'sasl':
                    sasl_enabled = True
                    break

            if not sasl_enabled:
                return None

            scopy = server_msg.copy()
            client_uid = scopy[4] if len(scopy) >= 6 else None
            # sasl_obj = None
            sasl_message_type = scopy[6] if len(scopy) >= 6 else None
            psasl.insert_sasl_client(self._Irc.Loader.Definition.MSasl(client_uid=client_uid))
            sasl_obj = psasl.get_sasl_obj(client_uid)

            if sasl_obj is None:
                return None

            match sasl_message_type:
                case 'H':
                    sasl_obj.remote_ip = str(scopy[8])
                    sasl_obj.message_type = sasl_message_type
                    return sasl_obj

                case 'S':
                    sasl_obj.message_type = sasl_message_type
                    if str(scopy[7]) in ['PLAIN', 'EXTERNAL']:
                        sasl_obj.mechanisme = str(scopy[7])

                    if sasl_obj.mechanisme == "PLAIN":
                        self.send2socket(f":{self._Config.SERVEUR_ID} SASL {self._Config.SERVEUR_HOSTNAME} {sasl_obj.client_uid} C +")
                    elif sasl_obj.mechanisme == "EXTERNAL":
                        if str(scopy[7]) == "+":
                            return None

                        sasl_obj.fingerprint = str(scopy[8])
                        self.send2socket(f":{self._Config.SERVEUR_ID} SASL {self._Config.SERVEUR_HOSTNAME} {sasl_obj.client_uid} C +")

                    self.on_sasl_authentication_process(sasl_obj)
                    return sasl_obj

                case 'C':
                    if sasl_obj.mechanisme == "PLAIN":
                        credentials = scopy[7]
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
            self._Logs.error(f'General Error: {err}', exc_info=True)

    def on_sasl_authentication_process(self, sasl_model: 'MSasl'):
        s = sasl_model
        server_id = self._Config.SERVEUR_ID
        main_server_hostname = self._Settings.MAIN_SERVER_HOSTNAME
        db_admin_table = self._Config.TABLE_ADMIN
        if sasl_model:
            def db_get_admin_info(*, username: Optional[str] = None, password: Optional[str] = None, fingerprint: Optional[str] = None) -> Optional[dict[str, Any]]:
                if fingerprint:
                    mes_donnees = {'fingerprint': fingerprint}
                    query = f"SELECT user, level, language FROM {db_admin_table} WHERE fingerprint = :fingerprint"
                else:
                    mes_donnees = {'user': username, 'password': self._Utils.hash_password(password)}
                    query = f"SELECT user, level, language FROM {db_admin_table} WHERE user = :user AND password = :password"

                result = self._Base.db_execute_query(query, mes_donnees)
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
                    self.send2socket(f":{server_id} SASL {main_server_hostname} {s.client_uid} D S")
                    self.send2socket(f":{server_id} SASL {s.username} :SASL authentication successful")
                else:
                    self.send2socket(f":{server_id} SASL {main_server_hostname} {s.client_uid} D F")
                    self.send2socket(f":{server_id} SASL {s.username} :SASL authentication failed")

            elif s.message_type == 'S' and s.mechanisme == 'EXTERNAL':
                # Connection using fingerprints
                admin_info = db_get_admin_info(fingerprint=s.fingerprint)
                
                if admin_info is not None:
                    s.auth_success = True
                    s.level = admin_info.get('level', 0)
                    s.username = admin_info.get('user', None)
                    s.language = admin_info.get('language', 'EN')
                    self.send2socket(f":{server_id} SASL {main_server_hostname} {s.client_uid} D S")
                    self.send2socket(f":{server_id} SASL {s.username} :SASL authentication successful")
                else:
                    # "904 <nick> :SASL authentication failed"
                    self.send2socket(f":{server_id} SASL {main_server_hostname} {s.client_uid} D F")
                    self.send2socket(f":{server_id} SASL {s.username} :SASL authentication failed")

    def on_error(self, server_msg: list[str]) -> None:
        self._Logs.debug(f"{server_msg}")

    def on_metedata(self, server_msg: list[str]) -> None:
        """_summary_

        Args:
            server_msg (list[str]): _description_
        """
        # [':97K', 'METADATA', '97KAAAAAA', 'ssl_cert', ':vTrSe', 'fingerprint90753683519522875', 
        # '/C=FR/OU=Testing/O=Test', 'Sasl/CN=localhost', '/C=FR/OU=Testing/O=Test', 'Sasl/CN=localhost']
        scopy = server_msg.copy()
        dnickname = self._Config.SERVICE_NICKNAME
        dchanlog = self._Config.SERVICE_CHANLOG
        green = self._Config.COLORS.green
        nogc = self._Config.COLORS.nogc

        if 'ssl_cert' in scopy:
            fingerprint = scopy[5]
            uid = scopy[2]
            user_obj = self._Irc.User.get_user(uid)
            if user_obj:
                user_obj.fingerprint = fingerprint
                if self._Irc.Admin.db_auth_admin_via_fingerprint(fingerprint, uid):
                    admin = self._Irc.Admin.get_admin(uid)
                    account = admin.account if admin else ''
                    self.send_priv_msg(nick_from=dnickname, 
                                       msg=tr("[ %sSASL AUTO AUTH%s ] - %s (%s) is now connected successfuly to %s", green, nogc, user_obj.nickname, account, dnickname),
                                       channel=dchanlog)
                    self.send_notice(nick_from=dnickname, nick_to=user_obj.nickname, msg=tr("Successfuly connected to %s", dnickname))

    def on_kick(self, server_msg: list[str]) -> None:
        ...

    # ------------------------------------------------------------------------
    #                           COMMON IRC PARSER
    # ------------------------------------------------------------------------

    def parse_uid(self, server_msg: list[str]) -> dict[str, str]:
        """Parse UID and return dictionary.

        Args:
            server_msg (list[str]): _description_
        """
        umodes = str(server_msg[11])
        remote_ip = server_msg[9] if 'S' not in umodes else '127.0.0.1'

        # Extract Geoip information
        pattern = r'^.*geoip=cc=(\S{2}).*$'
        geoip_match = match(pattern, server_msg[0])
        geoip = geoip_match.group(1) if geoip_match else None

        response = {
            'uid': str(server_msg[2]),
            'nickname': str(server_msg[4]),
            'username': str(server_msg[7]),
            'hostname': str(server_msg[5]),
            'umodes': umodes,
            'vhost': str(server_msg[6]),
            'ip': remote_ip,
            'realname': ' '.join(server_msg[12:]).lstrip(':'),
            'geoip': geoip,
            'reputation_score': 0,
            'iswebirc': True if 'webirc' in server_msg[0] else False,
            'iswebsocket': True if 'websocket' in server_msg[0] else False
        }
        return response

    def parse_quit(self, server_msg: list[str]) -> dict[str, str]:
        """Parse quit and return dictionary.
        >>> [':97KAAAAAB', 'QUIT', ':Quit:', 'this', 'is', 'my', 'reason', 'to', 'quit']
        Args:
            server_msg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The dictionary.
        """
        scopy = server_msg.copy()

        if scopy[0].startswith('@'):
            scopy.pop(0)

        response = {
            "uid": scopy[0].replace(':', ''),
            "reason": " ".join(scopy[3:])
        }
        return response

    def parse_nick(self, server_msg: list[str]) -> dict[str, str]:
        """Parse nick changes.
        >>> [':97KAAAAAC', 'NICK', 'testinspir', '1757360740']

        Args:
            server_msg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The response as dictionary.
        """
        scopy = server_msg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)

        response = {
            "uid": scopy[0].replace(':', ''),
            "newnickname": scopy[2],
            "timestamp": scopy[3]
        }
        return response

    def parse_privmsg(self, server_msg: list[str]) -> tuple[Optional['MUser'], Optional['MUser'], Optional['MChannel'], str]:
        """Parse PRIVMSG message.
        >>> [':97KAAAAAE', 'PRIVMSG', '#welcome', ':This', 'is', 'my', 'public', 'message']
        >>> [':97KAAAAAF', 'PRIVMSG', '98KAAAAAB', ':My','Message','...']

        Args:
            server_msg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The response as dictionary.
        """
        scopy = server_msg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)

        sender = self._User.get_user(self._Utils.clean_uid(scopy[0]))
        reciever = self._User.get_user(self._Utils.clean_uid(scopy[2]))
        channel = self._Channel.get_channel(scopy[2]) if self._Channel.is_valid_channel(scopy[2]) else None

        tmp_message = scopy[3:]
        tmp_message = tmp_message[0].replace(':', '')
        message = ' '.join(tmp_message)

        return sender, reciever, channel, message


    # ------------------------------------------------------------------------
    #                           IRC SENDER METHODS
    # ------------------------------------------------------------------------

    def send_mode_chan(self, channel_name: str, channel_mode: str) -> None:
        """_summary_

        Args:
            channel_name (str): _description_
            channel_mode (str): _description_
        """
        ...
    
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
        ...
    
    def send_sajoin(self, nick_to_sajoin: str, channel_name: str) -> None:
        """_summary_

        Args:
            nick_to_sajoin (str): _description_
            channel_name (str): _description_
        """
        ...

    def send_sapart(self, nick_to_sapart: str, channel_name: str) -> None:
        """_summary_

        Args:
            nick_to_sapart (str): _description_
            channel_name (str): _description_
        """
        ...
    
    def send_svs2mode(self, nickname: str, user_mode: str) -> None:
        """_summary_

        Args:
            nickname (str): _description_
            user_mode (str): _description_
        """
        ...
    
    def send_svsjoin(self, nick_to_part: str, channels: list[str], keys: list[str]) -> None:
        """_summary_

        Args:
            nick_to_part (str): _description_
            channels (list[str]): _description_
            keys (list[str]): _description_
        """
        ...

    def send_svslogin(self, client_uid: str, user_account: str) -> None:
        """Log a client into his account.

        Args:
            client_uid (str): Client UID
            user_account (str): The account of the user
        """
        ...

    def send_svslogout(self, client_obj: 'MClient') -> None:
        """Logout a client from his account

        Args:
            client_obj (MClient): The Client Object Model
        """
        ...

    def send_svsmode(self, nickname: str, user_mode: str) -> None:
        """_summary_

        Args:
            nickname (str): _description_
            user_mode (str): _description_
        """
        ...
    
    def send_svspart(self, nick_to_part: str, channels: list[str], reason: str) -> None:
        """_summary_

        Args:
            nick_to_part (str): _description_
            channels (list[str]): _description_
            reason (str): _description_
        """
        ...

    def on_md(self, server_msg: list[str]) -> None:
        """Handle MD responses
        [':001', 'MD', 'client', '001MYIZ03', 'certfp', ':d1235648...']
        Args:
            server_msg (list[str]): The server reply
        """
        ...
    
    def on_mode(self, server_msg: list[str]) -> None:
        """Handle mode coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        ...
    
    def on_reputation(self, server_msg: list[str]) -> None:
        """Handle REPUTATION coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        ...
    
    def on_smod(self, server_msg: list[str]) -> None:
        """Handle SMOD message coming from the server

        Args:
            server_msg (list[str]): Original server message
        """
        ...
    
    def on_svs2mode(self, server_msg: list[str]) -> None:
        """Handle svs2mode coming from a server
        >>> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']

        Args:
            server_msg (list[str]): Original server message
        """
        ...

    def on_eos(self, server_msg: list[str]) -> None:
        """Handle EOS coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        ...
