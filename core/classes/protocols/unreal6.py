from base64 import b64decode
from re import match, findall, search
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from ssl import SSLEOFError, SSLError
from core.classes.interfaces.iprotocol import IProtocol
from core.utils import is_coroutinefunction, tr

if TYPE_CHECKING:
    from core.definition import MSasl, MUser, MChannel

class Unrealircd6(IProtocol):

    def init_protocol(self) -> None:
        self.name = 'UnrealIRCD-6'
        self.protocol_version = 6100
        self.known_protocol: set[str] = {'SJOIN', 'UID', 'MD', 'QUIT', 'SQUIT',
                               'EOS', 'PRIVMSG', 'MODE', 'UMODE2', 
                               'VERSION', 'REPUTATION', 'SVS2MODE', 
                               'SLOG', 'NICK', 'PART', 'PONG', 'SASL', 'PING',
                               'PROTOCTL', 'SERVER', 'SMOD', 'TKL', 'NETINFO',
                               'SETHOST', '006', '007', '018'}

    def get_ircd_protocol_poisition(self, cmd: list[str], log: bool = False) -> tuple[int, Optional[str]]:
        """Get the position of known commands

        Args:
            cmd (list[str]): The server response
            log (bool): If true it will log in the logger

        Returns:
            tuple[int, Optional[str]]: The position and the command.
        """
        for index, token in enumerate(cmd):
            if token.upper() in self.known_protocol and index < 3:
                return index, token.upper()
        
        if log:
            self._ctx.Logs.debug(f"[IRCD LOGS] You need to handle this response: {cmd}")

        return -1, None

    def register_command(self) -> None:
        m = self._ctx.Definition.MIrcdCommand
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
        self.Handler.register(m(command_name="KICK", func=self.on_kick))
        self.Handler.register(m(command_name="SETHOST", func=self.on_sethost))

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

    async def send2socket(self, message: str, print_log: bool = True) -> None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            message (str): contient la commande à envoyer au serveur.
            print_log (bool): True print log message in the console
        """
        try:
            async with self._ctx.Settings.AILOCK:
                self._ctx.Irc.writer.write(f"{message}\r\n".encode(self._ctx.Config.SERVEUR_CHARSET[0]))
                await self._ctx.Irc.writer.drain()
                if print_log:
                    self._ctx.Logs.debug(f'<< {message}')

        except UnicodeDecodeError as ude:
            self._ctx.Logs.error(f'Decode Error try iso-8859-1 - {ude} - {message}')
            self._ctx.Irc.writer.write(f"{message}\r\n".encode(self._ctx.Config.SERVEUR_CHARSET[1],'replace'))
            await self._ctx.Irc.writer.drain()
        except UnicodeEncodeError as uee:
            self._ctx.Logs.error(f'Encode Error try iso-8859-1 - {uee} - {message}')
            self._ctx.Irc.writer.write(f"{message}\r\n".encode(self._ctx.Config.SERVEUR_CHARSET[1],'replace'))
            await self._ctx.Irc.writer.drain()
        except AssertionError as ae:
            self._ctx.Logs.warning(f'Assertion Error {ae} - message: {message}')
        except SSLEOFError as soe:
            self._ctx.Logs.error(f"SSLEOFError: {soe} - {message}")
        except SSLError as se:
            self._ctx.Logs.error(f"SSLError: {se} - {message}")
        except OSError as oe:
            self._ctx.Logs.error(f"OSError: {oe} - {message}")
        except AttributeError as ae:
            self._ctx.Logs.critical(f"Attribute Error: {ae}")

    async def send_priv_msg(self, nick_from: str, msg: str, channel: str = None, nick_to: str = None):
        """Sending PRIVMSG to a channel or to a nickname by batches
        could be either channel or nickname not both together
        Args:
            msg (str): The message to send
            nick_from (str): The sender nickname
            channel (str, optional): The receiver channel. Defaults to None.
            nick_to (str, optional): The reciever nickname. Defaults to None.
        """
        try:
            batch_size      = self._ctx.Config.BATCH_SIZE
            user_from       = self._ctx.User.get_user(nick_from)
            user_to         = self._ctx.User.get_user(nick_to) if not nick_to is None else None

            if user_from is None:
                self._ctx.Logs.error(f"The sender nickname [{nick_from}] do not exist")
                return None

            if not channel is None:
                for i in range(0, len(str(msg)), batch_size):
                    batch = str(msg)[i:i+batch_size]
                    await self.send2socket(f":{user_from.uid} PRIVMSG {channel} :{batch}")

            if not nick_to is None:
                for i in range(0, len(str(msg)), batch_size):
                    batch = str(msg)[i:i+batch_size]
                    await self.send2socket(f":{nick_from} PRIVMSG {user_to.uid} :{batch}")

        except Exception as err:
            self._ctx.Logs.error(f"General Error: {err}")
            self._ctx.Logs.error(f"General Error: {nick_from} - {channel} - {nick_to}")

    async def send_notice(self, nick_from: str, nick_to: str, msg: str) -> None:
        """Sending NOTICE by batches

        Args:
            msg (str): The message to send to the server
            nick_from (str): The sender Nickname
            nick_to (str): The reciever nickname
        """
        try:
            batch_size  = self._ctx.Config.BATCH_SIZE
            user_from   = self._ctx.User.get_user(nick_from)
            user_to     = self._ctx.User.get_user(nick_to)

            if user_from is None or user_to is None:
                self._ctx.Logs.error(f"The sender [{nick_from}] or the Reciever [{nick_to}] do not exist")
                return None

            for i in range(0, len(str(msg)), batch_size):
                batch = str(msg)[i:i+batch_size]
                await self.send2socket(f":{user_from.uid} NOTICE {user_to.uid} :{batch}")

        except Exception as err:
            self._ctx.Logs.error(f"General Error: {err}")

    async def send_link(self):
        """Créer le link et envoyer les informations nécessaires pour la 
        connexion au serveur.
        """
        service_id = self._ctx.Config.SERVICE_ID
        service_nickname = self._ctx.Config.SERVICE_NICKNAME
        service_username = self._ctx.Config.SERVICE_USERNAME
        service_realname = self._ctx.Config.SERVICE_REALNAME
        service_channel_log = self._ctx.Config.SERVICE_CHANLOG
        service_info = self._ctx.Config.SERVICE_INFO
        service_smodes = self._ctx.Config.SERVICE_SMODES
        service_cmodes = self._ctx.Config.SERVICE_CMODES
        # service_umodes = self._ctx.Config.SERVICE_UMODES
        service_hostname = self._ctx.Config.SERVICE_HOST
        service_name = self._ctx.Config.SERVICE_NAME
        protocolversion = self.protocol_version

        server_password = self._ctx.Config.SERVEUR_PASSWORD
        server_link = self._ctx.Config.SERVEUR_LINK
        server_id = self._ctx.Config.SERVEUR_ID

        version = self._ctx.Config.CURRENT_VERSION
        unixtime = self._ctx.Utils.get_unixtime()

        await self.send2socket(f":{server_id} PASS :{server_password}", print_log=False)
        await self.send2socket(f":{server_id} PROTOCTL SID NOQUIT NICKv2 SJOIN SJ3 NICKIP TKLEXT2 NEXTBANS CLK EXTSWHOIS MLOCK MTAGS")
        await self.send2socket(f":{server_id} PROTOCTL EAUTH={server_link},{protocolversion},,{service_name}-v{version}")
        await self.send2socket(f":{server_id} PROTOCTL SID={server_id}")
        await self.send2socket(f":{server_id} PROTOCTL BOOTED={unixtime}")
        await self.send2socket(f":{server_id} SERVER {server_link} 1 :{service_info}")
        await self.send2socket(f":{server_id} {service_nickname} :Reserved for services")
        await self.send2socket(f":{server_id} UID {service_nickname} 1 {unixtime} {service_username} {service_hostname} {service_id} * {service_smodes} * * fwAAAQ== :{service_realname}")
        await self.send2socket("EOS")
        await self.send_sjoin(service_channel_log)
        await self.send2socket(f":{server_id} TKL + Q * {service_nickname} {service_hostname} 0 {unixtime} :Reserved for services")
        await self.send2socket(f":{service_id} MODE {service_channel_log} {service_cmodes}")

        self._ctx.Logs.debug(f'>> {__name__} Link information sent to the server')

    async def send_gline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
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

        await self.send2socket(f":{self._ctx.Config.SERVEUR_ID} TKL + G {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    async def send_set_nick(self, newnickname: str) -> None:
        """Change nickname of the server
        \n This method will also update the User object
        Args:
            newnickname (str): New nickname of the server
        """
        await self.send2socket(f":{self._ctx.Config.SERVICE_NICKNAME} NICK {newnickname}")

        user_obj = self._ctx.User.get_user(self._ctx.Config.SERVICE_NICKNAME)
        self._ctx.User.update_nickname(user_obj.uid, newnickname)
        return None

    async def send_set_mode(self, modes: str, *, nickname: Optional[str] = None, channel_name: Optional[str] = None, params: Optional[str] = None) -> None:
        """Set a mode to channel or to a nickname or for a user in a channel
        This method will always send as the command as Defender's nickname (service_id)

        Args:
            modes (str): The selected mode
            nickname (Optional[str]): The nickname
            channel_name (Optional[str]): The channel name
            params (Optional[str]): Parameters like password.
        """
        service_id = self._ctx.Config.SERVICE_ID

        if modes[0] not in ['+', '-']:
            self._ctx.Logs.error(f"[MODE ERROR] The mode you have provided is missing the sign: {modes}")
            return None

        if nickname and channel_name:
            # :98KAAAAAB MODE #services +o defenderdev
            if not self._ctx.Channel.is_valid_channel(channel_name):
                self._ctx.Logs.error(f"[MODE ERROR] The channel is not valid: {channel_name}")
                return None
            await self.send2socket(f":{service_id} MODE {channel_name} {modes} {nickname}")
            return None

        if nickname and channel_name is None:
            await self.send2socket(f":{service_id} MODE {nickname} {modes}")
            return None

        if nickname is None and channel_name:
            if not self._ctx.Channel.is_valid_channel(channel_name):
                self._ctx.Logs.error(f"[MODE ERROR] The channel is not valid: {channel_name}")
                return None
            await self.send2socket(f":{service_id} MODE {channel_name} {modes}") if params is None else await self.send2socket(f":{service_id} MODE {channel_name} {modes} {params}")
            return None

        return None

    async def send_squit(self, server_id: str, server_link: str, reason: str) -> None:

        if not reason:
            reason = 'Service Shutdown'

        await self.send2socket(f":{server_id} SQUIT {server_link} :{reason}")
        return None

    async def send_ungline(self, nickname:str, hostname: str) -> None:

        await self.send2socket(f":{self._ctx.Config.SERVEUR_ID} TKL - G {nickname} {hostname} {self._ctx.Config.SERVICE_NICKNAME}")

        return None

    async def send_kline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + k user host set_by expire_timestamp set_at_timestamp :reason

        await self.send2socket(f":{self._ctx.Config.SERVEUR_ID} TKL + k {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    async def send_unkline(self, nickname:str, hostname: str) -> None:

        await self.send2socket(f":{self._ctx.Config.SERVEUR_ID} TKL - K {nickname} {hostname} {self._ctx.Config.SERVICE_NICKNAME}")

        return None

    async def send_sjoin(self, channel: str) -> None:
        """Server will join a channel with pre defined umodes

        Args:
            channel (str): Channel to join
        """
        if not self._ctx.Channel.is_valid_channel(channel):
            self._ctx.Logs.error(f"The channel [{channel}] is not valid")
            return None

        await self.send2socket(f":{self._ctx.Config.SERVEUR_ID} SJOIN {self._ctx.Utils.get_unixtime()} {channel} {self._ctx.Config.SERVICE_UMODES} :{self._ctx.Config.SERVICE_ID}")
        await self.send2socket(f":{self._ctx.Config.SERVICE_ID} MODE {channel} {self._ctx.Config.SERVICE_UMODES} {self._ctx.Config.SERVICE_ID}")

        # Add defender to the channel uids list
        self._ctx.Channel.insert(self._ctx.Definition.MChannel(name=channel, uids=[self._ctx.Config.SERVICE_ID]))
        return None

    async def send_sapart(self, nick_to_sapart: str, channel_name: str) -> None:
        """_summary_

        Args:
            nick_to_sapart (str): _description_
            channel_name (str): _description_
        """
        try:

            user_obj = self._ctx.User.get_user(uidornickname=nick_to_sapart)
            chan_obj = self._ctx.Channel.get_channel(channel_name)
            service_uid = self._ctx.Config.SERVICE_ID

            if user_obj is None or chan_obj is None:
                return None

            await self.send2socket(f":{service_uid} SAPART {user_obj.nickname} {chan_obj.name}")
            self._ctx.Channel.delete_user_from_channel(chan_obj.name, user_obj.uid)

            return None

        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def send_sajoin(self, nick_to_sajoin: str, channel_name: str) -> None:
        """_summary_

        Args:
            nick_to_sajoin (str): _description_
            channel_name (str): _description_
        """
        try:

            user_obj = self._ctx.User.get_user(uidornickname=nick_to_sajoin)
            chan_obj = self._ctx.Channel.get_channel(channel_name)
            service_uid = self._ctx.Config.SERVICE_ID

            if user_obj is None:
                # User not exist: leave
                return None

            if chan_obj is None:
                # Channel not exist
                if not self._ctx.Channel.is_valid_channel(channel_name):
                    # Incorrect channel: leave
                    return None

                # Create the new channel with the uid
                new_chan_obj = self._ctx.Definition.MChannel(name=channel_name, uids=[user_obj.uid])
                self._ctx.Channel.insert(new_chan_obj)
                await self.send2socket(f":{service_uid} SAJOIN {user_obj.nickname} {new_chan_obj.name}")

            else:
                self._ctx.Channel.add_user_to_a_channel(channel_name=channel_name, uid=user_obj.uid)
                await self.send2socket(f":{service_uid} SAJOIN {user_obj.nickname} {chan_obj.name}")

            return None

        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def send_svspart(self, nick_to_part: str, channels: list[str], reason: str) -> None:
        user_obj = self._ctx.User.get_user(nick_to_part)

        if user_obj is None:
            self._ctx.Logs.debug(f"[SVSPART] The nickname {nick_to_part} do not exist!")
            return None

        channels_list = ','.join([channel for channel in channels if self._ctx.Channel.is_valid_channel(channel)])
        service_id = self._ctx.Config.SERVICE_ID
        await self.send2socket(f':{service_id} SVSPART {user_obj.nickname} {channels_list} {reason}')
        return None

    async def send_svsjoin(self, nick_to_part: str, channels: list[str], keys: list[str]) -> None:
        user_obj = self._ctx.User.get_user(nick_to_part)

        if user_obj is None:
            self._ctx.Logs.debug(f"[SVSJOIN] The nickname {nick_to_part} do not exist!")
            return None

        channels_list = ','.join([channel for channel in channels if self._ctx.Channel.is_valid_channel(channel)])
        keys_list = ','.join([key for key in keys])
        service_id = self._ctx.Config.SERVICE_ID
        await self.send2socket(f':{service_id} SVSJOIN {user_obj.nickname} {channels_list} {keys_list}')
        return None

    async def send_svsmode(self, nickname: str, user_mode: str) -> None:
        try:
            user_obj = self._ctx.User.get_user(uidornickname=nickname)
            service_uid = self._ctx.Config.SERVICE_ID

            if user_obj is None:
                return None

            await self.send2socket(f':{service_uid} SVSMODE {nickname} {user_mode}')

            # Update new mode
            self._ctx.User.update_mode(user_obj.uid, user_mode)

            return None
        except Exception as err:
                self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def send_svs2mode(self, nickname: str, user_mode: str) -> None:
        try:
            user_obj = self._ctx.User.get_user(uidornickname=nickname)
            service_uid = self._ctx.Config.SERVICE_ID

            if user_obj is None:
                return None

            await self.send2socket(f':{service_uid} SVS2MODE {nickname} {user_mode}')

            # Update new mode
            self._ctx.User.update_mode(user_obj.uid, user_mode)

            return None
        except Exception as err:
                self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def send_svslogin(self, client_uid: str, user_account: str) -> None:
        """Log a client into his account.

        Args:
            client_uid (str): Client UID
            user_account (str): The account of the user
        """
        try:
            await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} SVSLOGIN {self._ctx.Settings.MAIN_SERVER_HOSTNAME} {client_uid} {user_account}")
        except Exception as err:
            self._ctx.Logs.error(f'General Error: {err}')

    async def send_svslogout(self) -> None:
        """Logout a client from his account
        """
        try:
            # await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} SVSLOGIN {self._ctx.Settings.MAIN_SERVER_HOSTNAME} {c_uid} 0")
            # await self.send_svs2mode(c_nickname, '-r')
            pass
        except Exception as err:
            self._ctx.Logs.error(f'General Error: {err}')

    async def send_quit(self, uid: str, reason: str, print_log: bool = True) -> None:
        """Send quit message
        - Delete uid from User object
        - Delete uid from Reputation object

        Args:
            uid (str): The UID or the Nickname
            reason (str): The reason for the quit
            print_log (bool): Print the log
        """
        user_obj = self._ctx.User.get_user(uidornickname=uid)
        reputation_obj = self._ctx.Reputation.get_reputation(uidornickname=uid)

        if not user_obj is None:
            await self.send2socket(f":{user_obj.uid} QUIT :{reason}", print_log=print_log)
            self._ctx.User.delete(user_obj.uid)

        if not reputation_obj is None:
            self._ctx.Reputation.delete(reputation_obj.uid)

        if not self._ctx.Channel.delete_user_from_all_channel(uid):
            self._ctx.Logs.error(f"The UID [{uid}] has not been deleted from all channels")

        return None

    async def send_uid(self, nickname:str, username: str, hostname: str, uid:str, umodes: str,
                 vhost: str, remote_ip: str, realname: str, geoip: str, print_log: bool = True) -> None:
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
        # {clone.nickname} 1 {self._ctx.Utils.get_unixtime()} {clone.username} {clone.hostname} {clone.uid} * {clone.umodes}  {clone.vhost} * {self.Base.encode_ip(clone.remote_ip)} :{clone.realname}
        try:
            unixtime = self._ctx.Utils.get_unixtime()
            encoded_ip = self._ctx.Base.encode_ip(remote_ip)

            # Create the user
            self._ctx.User.insert(
                self._ctx.Definition.MUser(
                            uid=uid, nickname=nickname, username=username, 
                            realname=realname,hostname=hostname, umodes=umodes,
                            vhost=vhost, remote_ip=remote_ip, geoip=geoip
                        )
                    )

            uid_msg = f":{self._ctx.Config.SERVEUR_ID} UID {nickname} 1 {unixtime} {username} {hostname} {uid} * {umodes} {vhost} * {encoded_ip} :{realname}"

            await self.send2socket(uid_msg, print_log=print_log)

            return None

        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def send_join_chan(self, uidornickname: str, channel: str, password: str = None, print_log: bool = True) -> None:
        """Joining a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            password (str, optional): The password of the channel to join. Default to None
            print_log (bool, optional): Write logs. Defaults to True.
        """

        user_obj = self._ctx.User.get_user(uidornickname)
        pwd_channel = password if not password is None else ''

        if user_obj is None:
            return None

        if not self._ctx.Channel.is_valid_channel(channel):
            self._ctx.Logs.error(f"The channel [{channel}] is not valid")
            return None

        await self.send2socket(f":{user_obj.uid} JOIN {channel} {pwd_channel}", print_log=print_log)

        if uidornickname == self._ctx.Config.SERVICE_NICKNAME or uidornickname == self._ctx.Config.SERVICE_ID:
            await self.send2socket(f":{self._ctx.Config.SERVICE_ID} MODE {channel} {self._ctx.Config.SERVICE_UMODES} {self._ctx.Config.SERVICE_ID}")

        # Add defender to the channel uids list
        self._ctx.Channel.insert(self._ctx.Definition.MChannel(name=channel, uids=[user_obj.uid]))

        # Set the automode to the user
        if 'r' not in user_obj.umodes and 'o' not in user_obj.umodes:
            return None

        db_data: dict[str, str] = {"nickname": user_obj.nickname, "channel": channel}
        db_query = await self._ctx.Base.db_execute_query("SELECT id, mode FROM command_automode WHERE nickname = :nickname AND channel = :channel", db_data)
        db_result = db_query.fetchone()
        if db_result is not None:
            id_cmd_automode, mode = db_result
            await self.send2socket(f":{self._ctx.Config.SERVICE_ID} MODE {channel} {mode} {user_obj.nickname}")

        return None

    async def send_part_chan(self, uidornickname:str, channel: str, print_log: bool = True) -> None:
        """Part from a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            print_log (bool, optional): Write logs. Defaults to True.
        """

        u = self._ctx.User.get_user(uidornickname)

        if u is None:
            self._ctx.Logs.error(f"The user [{uidornickname}] is not valid")
            return None

        if not self._ctx.Channel.is_valid_channel(channel):
            self._ctx.Logs.error(f"The channel [{channel}] is not valid")
            return None

        await self.send2socket(f":{u.uid} PART {channel}", print_log=print_log)

        # Add defender to the channel uids list
        self._ctx.Channel.delete_user_from_channel(channel, u.uid)
        return None

    async def send_mode_chan(self, channel_name: str, channel_mode: str) -> None:

        channel = self._ctx.Channel.is_valid_channel(channel_name)
        if not channel:
            self._ctx.Logs.error(f'The channel [{channel_name}] is not correct')
            return None

        await self.send2socket(f":{self._ctx.Config.SERVICE_NICKNAME} MODE {channel_name} {channel_mode}")
        return None

    async def send_raw(self, raw_command: str) -> None:

        await self.send2socket(f":{self._ctx.Config.SERVICE_NICKNAME} {raw_command}")

        return None

    # ------------------------------------------------------------------------
    #                           COMMON IRC PARSER
    # ------------------------------------------------------------------------

    def parse_uid(self, server_msg: list[str]) -> Optional['MUser']:
        """Parse UID and return dictionary.
        >>> ['@s2s-md/geoip=cc=GBtag...', ':001', 'UID', 'albatros', '0', '1721564597', 'albatros', 'hostname...', '001HB8G04', '0', '+iwxz', 'hostname-vhost', 'hostname-vhost', 'MyZBwg==', ':...']
        Args:
            server_msg (list[str]): The UID ircd response
        """
        scopy = server_msg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)

        uid = scopy[7]
        return self._ctx.User.get_user(uid)

    def parse_quit(self, server_msg: list[str]) -> tuple[Optional['MUser'], str]:
        """Parse quit and return dictionary.
        >>> # ['@unrealtag...', ':001JKNY0N', 'QUIT', ':Quit:', '....']
        Args:
            server_msg (list[str]): The server message to parse

        Returns:
            tuple[MUser, str]: The User Who Quit Object and the reason.
        """
        scopy = server_msg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)
        
        user_obj = self._ctx.User.get_user(self._ctx.Utils.clean_uid(scopy[0]))
        tmp_reason = scopy[3:]
        tmp_reason[0] = tmp_reason[0].replace(':', '')
        reason = ' '.join(tmp_reason)

        return user_obj, reason

    def parse_nick(self, server_msg: list[str]) -> tuple[Optional['MUser'], str, str]:
        """Parse nick changes and return dictionary.
        >>> ['@unrealircd.org/geoip=FR;unrealircd.org/', ':001OOU2H3', 'NICK', 'WebIrc', '1703795844']

        Args:
            server_msg (list[str]): The server message to parse

        Returns:
            tuple(MUser, newnickname(str), timestamp(str)): Tuple of the response.

            >>> MUser, newnickname, timestamp
        """
        scopy = server_msg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)

        user_obj = self._ctx.User.get_user(self._ctx.User.clean_uid(scopy[0]))
        newnickname = scopy[2]
        timestamp = scopy[3]
        return user_obj, newnickname, timestamp

    def parse_privmsg(self, server_msg: list[str]) -> tuple[Optional['MUser'], Optional['MUser'], Optional['MChannel'], str]:
        """Parse PRIVMSG message.
        >>> ['@....', ':97KAAAAAE', 'PRIVMSG', '#welcome', ':This', 'is', 'my', 'public', 'message']
        >>> [':97KAAAAAF', 'PRIVMSG', '98KAAAAAB', ':sasa']

        Args:
            server_msg (list[str]): The server message to parse

        Returns:
            tuple[MUser(Sender), MUser(Reciever), MChannel, str]: Sender user model, reciever user model, Channel model, messgae .
        """
        scopy = server_msg.copy()
        if scopy[0].startswith('@'):
            scopy.pop(0)

        sender = self._ctx.User.get_user(self._ctx.Utils.clean_uid(scopy[0]))
        reciever = self._ctx.User.get_user(self._ctx.Utils.clean_uid(scopy[2]))
        channel = self._ctx.Channel.get_channel(scopy[2]) if self._ctx.Channel.is_valid_channel(scopy[2]) else None

        tmp_message = scopy[3:]
        tmp_message[0] = tmp_message[0].replace(':', '')
        message = ' '.join(tmp_message)

        return sender, reciever, channel, message

    #####################
    #   HANDLE EVENTS   #
    #####################

    async def on_svs2mode(self, server_msg: list[str]) -> None:
        """Handle svs2mode coming from a server
        >>> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # >> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']
            scopy = server_msg.copy()
            uid_user_to_edit = scopy[2]
            umode = scopy[3]

            u = self._ctx.User.get_user(uid_user_to_edit)

            if u is None:
                return None

            if self._ctx.User.update_mode(u.uid, umode):
                return None

            return None
        except IndexError as ie:
            self._ctx.Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_mode(self, server_msg: list[str]) -> None:
        """Handle mode coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        #['@msgid=d0ySx56Yd0nc35oHts2SkC-/J9mVUA1hfM6...', ':001', 'MODE', '#a', '+nt', '1723207536']
        #['@unrealircd.org/userhost=adator@localhost;...', ':001LQ0L0C', 'MODE', '#services', '-l']

        return None

    async def on_umode2(self, server_msg: list[str]) -> None:
        """Handle umode2 coming from a server
        >>> [':adator_', 'UMODE2', '-i']

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':adator_', 'UMODE2', '-iwx']
            scopy = server_msg.copy()
            u  = self._ctx.User.get_user(str(scopy[0]).lstrip(':'))
            user_mode = scopy[2]

            if u is None: # If user is not created
                return None

            # TODO : User object should be able to update user modes
            if self._ctx.User.update_mode(u.uid, user_mode):
                return None

            return None

        except IndexError as ie:
            self._ctx.Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_quit(self, server_msg: list[str]) -> None:
        """Handle quit coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # ['@unrealircd.org/userhost=...@192.168.1.10;unrealircd.org/userip=...@192.168.1.10;msgid=CssUrV08BzekYuq7BfvPHn;time=2024-11-02T15:03:33.182Z', ':001JKNY0N', 'QUIT', ':Quit:', '....']
            scopy = server_msg.copy()
            uid_who_quit = str(scopy[1]).lstrip(':')

            self._ctx.Channel.delete_user_from_all_channel(uid_who_quit)
            self._ctx.User.delete(uid_who_quit)
            self._ctx.Reputation.delete(uid_who_quit)
            self._ctx.Admin.delete(uid_who_quit)

            return None

        except IndexError as ie:
            self._ctx.Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_squit(self, server_msg: list[str]) -> None:
        """Handle squit coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        # ['@msgid=QOEolbRxdhpVW5c8qLkbAU;time=2024-09-21T17:33:16.547Z', 'SQUIT', 'defender.deb.biz.st', ':Connection', 'closed']
        scopy = server_msg.copy()
        server_hostname = scopy[2]
        uid_to_delete = None
        for s_user in self._ctx.User.UID_DB:
            if s_user.hostname == server_hostname and 'S' in s_user.umodes:
                uid_to_delete = s_user.uid

        if uid_to_delete is None:
            return None

        self._ctx.User.delete(uid_to_delete)
        self._ctx.Channel.delete_user_from_all_channel(uid_to_delete)

        return None

    async def on_protoctl(self, server_msg: list[str]) -> None:
        """Handle protoctl coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        # ['PROTOCTL', 'CHANMODES=beI,fkL,lFH,cdimnprstzCDGKMNOPQRSTVZ', 'USERMODES=diopqrstwxzBDGHIRSTWZ', 'BOOTED=1728815798', 'PREFIX=(qaohv)~&@%+', 'SID=001', 'MLOCK', 'TS=1730662755', 'EXTSWHOIS']
        user_modes: Optional[str] = None
        prefix: Optional[str] = None
        host_server_id: Optional[str] = None

        for msg in server_msg:

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

        self._ctx.Config.HSID = host_server_id
        self._ctx.Settings.PROTOCTL_USER_MODES = list(user_modes)
        self._ctx.Settings.PROTOCTL_PREFIX = list(prefix)

        return None

    async def on_nick(self, server_msg: list[str]) -> None:
        """Handle nick coming from a server
        new nickname

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # ['@unrealircd.org/geoip=FR;unrealircd.org/', ':001OOU2H3', 'NICK', 'WebIrc', '1703795844']
            # Changement de nickname

            uid = str(server_msg[1]).lstrip(':')
            newnickname = server_msg[3]
            self._ctx.User.update_nickname(uid, newnickname)
            self._ctx.Admin.update_nickname(uid, newnickname)
            self._ctx.Reputation.update(uid, newnickname)

            return None

        except IndexError as ie:
            self._ctx.Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_sjoin(self, server_msg: list[str]) -> None:
        """Handle sjoin coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # ['@msgid=5sTwGdj349D82L96p749SY;time=2024-08-15T09:50:23.528Z', ':001', 'SJOIN', '1721564574', '#welcome', ':001JD94QH']
            # ['@msgid=bvceb6HthbLJapgGLXn1b0;time=2024-08-15T09:50:11.464Z', ':001', 'SJOIN', '1721564574', '#welcome', '+lnrt', '13', ':001CIVLQF', '+11ZAAAAAB', '001QGR10C', '*@0014UE10B', '001NL1O07', '001SWZR05', '001HB8G04', '@00BAAAAAJ', '0019M7101']
            # ['@msgid=SKUeuVzOrTShRDduq8VerX;time=2024-08-23T19:37:04.266Z', ':001', 'SJOIN', '1723993047', '#welcome', '+lnrt', '13', 
            # ':001T6VU3F', '001JGWB2K', '@11ZAAAAAB', 
            # '001F16WGR', '001X9YMGQ', '*+001DYPFGP', '@00BAAAAAJ', '001AAGOG9', '001FMFVG8', '001DAEEG7', 
            # '&~G:unknown-users', '"~G:websocket-users', '"~G:known-users', '"~G:webirc-users']
            # [':00B', 'SJOIN', '1731872579', '#services', '+', ':00BAAAAAB']
            scopy = server_msg.copy()
            if scopy[0].startswith('@'):
                scopy.pop(0)

            channel = str(scopy[3]).lower()
            len_cmd = len(scopy)
            list_users:list = []
            occurence = 0
            start_boucle = 0

            # Trouver le premier user
            for i in range(len_cmd):
                s: list = findall(fr':', scopy[i])
                if s:
                    occurence += 1
                    if occurence == 2:
                        start_boucle = i

            # Boucle qui va ajouter l'ensemble des users (UID)
            for i in range(start_boucle, len(scopy)):
                parsed_uid = str(scopy[i])
                clean_uid = self._ctx.Utils.clean_uid(parsed_uid)
                if not clean_uid is None and len(clean_uid) == 9:
                    list_users.append(clean_uid)

            if list_users:
                self._ctx.Channel.insert(
                    self._ctx.Definition.MChannel(
                        name=channel,
                        uids=list_users
                    )
                )
            return None

        except IndexError as ie:
            self._ctx.Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_part(self, server_msg: list[str]) -> None:
        """Handle part coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # ['@unrealircd.org', ':001EPFBRD', 'PART', '#welcome', ':WEB', 'IRC', 'Paris']
            uid = str(server_msg[1]).lstrip(':')
            channel = str(server_msg[3]).lower()
            self._ctx.Channel.delete_user_from_channel(channel, uid)
            return None

        except IndexError as ie:
            self._ctx.Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_eos(self, server_msg: list[str]) -> None:
        """Handle EOS coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':001', 'EOS']
            server_msg_copy = server_msg.copy()
            hsid = str(server_msg_copy[0]).replace(':','')
            if hsid == self._ctx.Config.HSID:
                if self._ctx.Config.DEFENDER_INIT == 1:
                    current_version = self._ctx.Config.CURRENT_VERSION
                    latest_version = self._ctx.Config.LATEST_VERSION
                    if self._ctx.Base.check_for_new_version(False):
                        version = f'{current_version} >>> {latest_version}'
                    else:
                        version = f'{current_version}'

                    print(f"################### DEFENDER ###################")
                    print(f"#               SERVICE CONNECTE                ")
                    print(f"# SERVEUR  :    {self._ctx.Config.SERVEUR_IP}        ")
                    print(f"# PORT     :    {self._ctx.Config.SERVEUR_PORT}      ")
                    print(f"# SSL      :    {self._ctx.Config.SERVEUR_SSL}       ")
                    print(f"# SSL VER  :    {self._ctx.Config.SSL_VERSION}       ")
                    print(f"# NICKNAME :    {self._ctx.Config.SERVICE_NICKNAME}  ")
                    print(f"# CHANNEL  :    {self._ctx.Config.SERVICE_CHANLOG}   ")
                    print(f"# VERSION  :    {version}                       ")
                    print(f"################################################")

                    self._ctx.Logs.info(f"################### DEFENDER ###################")
                    self._ctx.Logs.info(f"#               SERVICE CONNECTE                ")
                    self._ctx.Logs.info(f"# SERVEUR  :    {self._ctx.Config.SERVEUR_IP}        ")
                    self._ctx.Logs.info(f"# PORT     :    {self._ctx.Config.SERVEUR_PORT}      ")
                    self._ctx.Logs.info(f"# SSL      :    {self._ctx.Config.SERVEUR_SSL}       ")
                    self._ctx.Logs.info(f"# SSL VER  :    {self._ctx.Config.SSL_VERSION}       ")
                    self._ctx.Logs.info(f"# NICKNAME :    {self._ctx.Config.SERVICE_NICKNAME}  ")
                    self._ctx.Logs.info(f"# CHANNEL  :    {self._ctx.Config.SERVICE_CHANLOG}   ")
                    self._ctx.Logs.info(f"# VERSION  :    {version}                       ")
                    self._ctx.Logs.info(f"################################################")

                    await self.send_sjoin(self._ctx.Config.SERVICE_CHANLOG)

                    if self._ctx.Base.check_for_new_version(False):
                        await self.send_priv_msg(
                            nick_from=self._ctx.Config.SERVICE_NICKNAME,
                            msg=f" New Version available {version}",
                            channel=self._ctx.Config.SERVICE_CHANLOG
                        )

                # Initialisation terminé aprés le premier PING
                await self.send_priv_msg(
                    nick_from=self._ctx.Config.SERVICE_NICKNAME,
                    msg=tr("[ %sINFORMATION%s ] >> %s is ready!", self._ctx.Config.COLORS.green, self._ctx.Config.COLORS.nogc, self._ctx.Config.SERVICE_NICKNAME),
                    channel=self._ctx.Config.SERVICE_CHANLOG
                )
                self._ctx.Config.DEFENDER_INIT = 0

                # Send EOF to other modules
                for module in self._ctx.ModuleUtils.model_get_loaded_modules().copy():
                    await module.class_instance.cmd(server_msg_copy) if self._ctx.Utils.is_coroutinefunction(module.class_instance.cmd) else module.class_instance.cmd(server_msg_copy)

                # Join saved channels & load existing modules
                await self._ctx.Channel.db_join_saved_channels()
                await self._ctx.ModuleUtils.db_load_all_existing_modules()

                await self.send2socket(f":{self._ctx.Config.SERVEUR_ID} SMOD :L:Defender:1.0.0 :L:Command:1.0.0")

                return None
        except IndexError as ie:
            self._ctx.Logs.error(f"{__name__} - Index Error: {ie}")
        except KeyError as ke:
            self._ctx.Logs.error(f"{__name__} - Key Error: {ke}")
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}", exc_info=True)

    async def on_reputation(self, server_msg: list[str]) -> None:
        """Handle REPUTATION coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # :001 REPUTATION 127.0.0.1 118
            server_msg_copy = server_msg.copy()
            self._ctx.Irc.first_connexion_ip = server_msg_copy[2]
            self._ctx.Irc.first_score = 0

            if str(server_msg_copy[3]).find('*') != -1:
                # If * available, it means that an ircop changed the repurtation score
                # means also that the user exist will try to update all users with same IP
                self._ctx.Irc.first_score = int(str(server_msg_copy[3]).replace('*',''))
                for user in self._ctx.User.UID_DB:
                    if user.remote_ip == self._ctx.Irc.first_connexion_ip:
                        user.score_connexion = self._ctx.Irc.first_score
            else:
                self._ctx.Irc.first_score = int(server_msg_copy[3])

            # Possibilité de déclancher les bans a ce niveau.
        except IndexError as ie:
            self._ctx.Logs.error(f'Index Error {__name__}: {ie}')
        except ValueError as ve:
            self._ctx.Irc.first_score = 0
            self._ctx.Logs.error(f'Value Error {__name__}: {ve}', exc_info=True)
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_uid(self, server_msg: list[str]) -> None:
        """Handle uid message coming from the server

        Args:
            server_msg (list[str]): Original server message
        """
        # ['@s2s-md/geoip=cc=GB|cd=United\\sKingdom|asn=16276|asname=OVH\\sSAS;s2s-md/tls_cipher=TLSv1.3-TLS_CHACHA20_POLY1305_SHA256;s2s-md/creationtime=1721564601', 
        # ':001', 'UID', 'albatros', '0', '1721564597', 'albatros', 'vps-91b2f28b.vps.ovh.net', 
        # '001HB8G04', '0', '+iwxz', 'Clk-A62F1D18.vps.ovh.net', 'Clk-A62F1D18.vps.ovh.net', 'MyZBwg==', ':...']
        try:
            scopy = server_msg.copy()
            is_webirc = True if 'webirc' in scopy[0] else False
            is_websocket = True if 'websocket' in scopy[0] else False

            uid = str(scopy[8])
            nickname = str(scopy[3])
            username = str(scopy[6])
            hostname = str(scopy[7])
            umodes = str(scopy[10])
            vhost = str(scopy[11])
            remote_ip = '127.0.0.1' if 'S' in umodes else self._ctx.Base.decode_ip(str(scopy[13]))
            
            # extract realname
            realname = ' '.join(scopy[14:]).lstrip(':')

            # Extract Geoip information
            pattern = r'^.*geoip=cc=(\S{2}).*$'
            geoip_match = match(pattern, scopy[0])
            geoip = geoip_match.group(1) if geoip_match else None

            # Extract Fingerprint information
            pattern = r'^.*certfp=([^;]+).*$'
            fp_match = match(pattern, scopy[0])
            fingerprint = fp_match.group(1) if fp_match else None

            # Extract tls_cipher information
            pattern = r'^.*tls_cipher=([^;]+).*$'
            tlsc_match = match(pattern, scopy[0])
            tls_cipher = tlsc_match.group(1) if tlsc_match else None
            score_connexion = self._ctx.Irc.first_score

            self._ctx.User.insert(
                self._ctx.Definition.MUser(
                    uid=uid,
                    nickname=nickname,
                    username=username,
                    realname=realname,
                    hostname=hostname,
                    umodes=umodes,
                    vhost=vhost,
                    fingerprint=fingerprint,
                    tls_cipher=tls_cipher,
                    isWebirc=is_webirc,
                    isWebsocket=is_websocket,
                    remote_ip=remote_ip,
                    geoip=geoip,
                    score_connexion=score_connexion,
                    connexion_datetime=datetime.now()
                )
            )

            # Auto Auth admin via fingerprint
            dnickname = self._ctx.Config.SERVICE_NICKNAME
            dchanlog  = self._ctx.Config.SERVICE_CHANLOG
            green = self._ctx.Config.COLORS.green
            red = self._ctx.Config.COLORS.red
            nogc = self._ctx.Config.COLORS.nogc

            # for module in self._ctx.ModuleUtils.model_get_loaded_modules().copy():
            #     module.class_instance.cmd(serverMsg)

            # SASL authentication
            # ['@s2s-md/..', ':001', 'UID', 'adator__', '0', '1755987444', '...', 'desktop-h1qck20.mshome.net', '001XLTT0U', '0', '+iwxz', '*', 'Clk-EC2256B2.mshome.net', 'rBKAAQ==', ':...']

            sasl_obj = self._ctx.Sasl.get_sasl_obj(uid)
            if sasl_obj:
                if sasl_obj.auth_success:
                    self._ctx.Irc.insert_db_admin(sasl_obj.client_uid, sasl_obj.username, sasl_obj.level, sasl_obj.language)
                    await self.send_priv_msg(nick_from=dnickname, 
                                        msg=tr("[ %sSASL AUTH%s ] - %s (%s) is now connected successfuly to %s", green, nogc, nickname, sasl_obj.username, dnickname),
                                        channel=dchanlog)
                    await self.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Successfuly connected to %s", dnickname))
                else:
                    await self.send_priv_msg(nick_from=dnickname, 
                                            msg=tr("[ %sSASL AUTH%s ] - %s provided a wrong password for this username %s", red, nogc, nickname, sasl_obj.username),
                                            channel=dchanlog)
                    await self.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Wrong password!"))

                # Delete sasl object!
                self._ctx.Sasl.delete_sasl_client(uid)
                return None

            # If no sasl authentication then auto connect via fingerprint
            if await self._ctx.Admin.db_auth_admin_via_fingerprint(fingerprint, uid):
                admin = self._ctx.Admin.get_admin(uid)
                account = admin.account if admin else ''
                await self.send_priv_msg(nick_from=dnickname, 
                                   msg=tr("[ %sFINGERPRINT AUTH%s ] - %s (%s) is now connected successfuly to %s", green, nogc, nickname, account, dnickname),
                                   channel=dchanlog)
                await self.send_notice(nick_from=dnickname, nick_to=nickname, msg=tr("Successfuly connected to %s", dnickname))

            return None
        except IndexError as ie:
            self._ctx.Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_privmsg(self, server_msg: list[str]) -> None:
        """Handle PRIVMSG message coming from the server

        Args:
            server_msg (list[str]): Original server message
        """
        srv_msg = server_msg.copy()
        cmd = server_msg.copy()
        try:

            # Supprimer la premiere valeur si MTAGS activé
            if cmd[0].startswith('@'):
                cmd.pop(0)

            get_uid_or_nickname = str(cmd[0].replace(':',''))
            user_trigger = self._ctx.User.get_nickname(get_uid_or_nickname)
            pattern = fr'(:\{self._ctx.Config.SERVICE_PREFIX})(.*)$'
            hcmds = search(pattern, ' '.join(cmd)) # va matcher avec tout les caractéres aprés le .

            if hcmds: # Commande qui commencent par le point
                liste_des_commandes = list(hcmds.groups())
                convert_to_string = ' '.join(liste_des_commandes)
                arg = convert_to_string.split()
                arg.remove(f':{self._ctx.Config.SERVICE_PREFIX}')
                if not self._ctx.Commands.is_command_exist(arg[0]):
                    self._ctx.Logs.debug(f"This command {arg[0]} is not available")
                    await self.send_notice(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        nick_to=user_trigger,
                        msg=f"This command [{self._ctx.Config.COLORS.bold}{arg[0]}{self._ctx.Config.COLORS.bold}] is not available"
                    )
                    return None

                cmd_to_send = convert_to_string.replace(':','')
                await self._ctx.Base.log_cmd(user_trigger, cmd_to_send)

                fromchannel = str(cmd[2]).lower() if self._ctx.Channel.is_valid_channel(cmd[2]) else None
                await self._ctx.Irc.hcmds(user_trigger, fromchannel, arg, cmd)

            if cmd[2] == self._ctx.Config.SERVICE_ID:
                pattern = fr'^:.*?:(.*)$'
                hcmds = search(pattern, ' '.join(cmd))

                if hcmds: # par /msg defender [commande]
                    liste_des_commandes = list(hcmds.groups())
                    convert_to_string = ' '.join(liste_des_commandes)
                    arg = convert_to_string.split()

                    # Réponse a un CTCP VERSION
                    if arg[0] == '\x01VERSION\x01':
                        await self.on_version(srv_msg)
                        return None

                    # Réponse a un TIME
                    if arg[0] == '\x01TIME\x01':
                        await self.on_time(srv_msg)
                        return None

                    # Réponse a un PING
                    if arg[0] == '\x01PING':
                        await self.on_ping(srv_msg)
                        return None

                    if not self._ctx.Commands.is_command_exist(arg[0]):
                        self._ctx.Logs.debug(f"This command {arg[0]} sent by {user_trigger} is not available")
                        return None

                    cmd_to_send = convert_to_string.replace(':','')
                    await self._ctx.Base.log_cmd(user_trigger, cmd_to_send)
                    fromchannel = None

                    if len(arg) >= 2:
                        fromchannel = str(arg[1]).lower() if self._ctx.Channel.is_valid_channel(arg[1]) else None

                    await self._ctx.Irc.hcmds(user_trigger, fromchannel, arg, cmd)
            return None

        except KeyError as ke:
            self._ctx.Logs.error(f"Key Error: {ke}")
        except AttributeError as ae:
            self._ctx.Logs.error(f"Attribute Error: {ae}", exc_info=True)
        except Exception as err:
            self._ctx.Logs.error(f"General Error: {err} - {srv_msg}" , exc_info=True)

    async def on_server_ping(self, server_msg: list[str]) -> None:
        """Send a PONG message to the server

        Args:
            server_msg (list[str]): List of str coming from the server
        """
        try:
            scopy = server_msg.copy()
            await self.send2socket(' '.join(scopy).replace('PING', 'PONG'), print_log=False)

            return None
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_server(self, server_msg: list[str]) -> None:
        """_summary_

        Args:
            server_msg (list[str]): _description_
        """
        try:
            # ['SERVER', 'irc.local.org', '1', ':U6100-Fhn6OoE-001', 'Local', 'Server']
            scopy = server_msg.copy()
            self._ctx.Settings.MAIN_SERVER_HOSTNAME = scopy[1]
        except Exception as err:
            self._ctx.Logs.error(f'General Error: {err}')

    async def on_version(self, server_msg: list[str]) -> None:
        """Sending Server Version to the server

        Args:
            server_msg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':00BAAAAAI', 'PRIVMSG', '12ZAAAAAB', ':\x01VERSION\x01']
        # Réponse a un CTCP VERSION
        try:
            scopy = server_msg.copy()
            nickname = self._ctx.User.get_nickname(self._ctx.Utils.clean_uid(scopy[1]))
            dnickname = self._ctx.Config.SERVICE_NICKNAME
            arg = scopy[4].replace(':', '')

            if nickname is None:
                return None

            if arg == '\x01VERSION\x01':
                await self.send2socket(f':{dnickname} NOTICE {nickname} :\x01VERSION Service {self._ctx.Config.SERVICE_NICKNAME} V{self._ctx.Config.CURRENT_VERSION}\x01')

            return None
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_time(self, server_msg: list[str]) -> None:
        """Sending TIME answer to a requestor

        Args:
            server_msg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':00BAAAAAI', 'PRIVMSG', '12ZAAAAAB', ':\x01TIME\x01']
        # Réponse a un CTCP VERSION
        try:
            scopy = server_msg.copy()
            nickname = self._ctx.User.get_nickname(self._ctx.Utils.clean_uid(scopy[1]))
            dnickname = self._ctx.Config.SERVICE_NICKNAME
            arg = scopy[4].replace(':', '')
            current_datetime = self._ctx.Utils.get_sdatetime()

            if nickname is None:
                return None

            if arg == '\x01TIME\x01':
                await self.send2socket(f':{dnickname} NOTICE {nickname} :\x01TIME {current_datetime}\x01')

            return None
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_ping(self, server_msg: list[str]) -> None:
        """Sending a PING answer to requestor

        Args:
            server_msg (list[str]): List of str coming from the server
        """
        # ['@unrealircd.org/...', ':001INC60B', 'PRIVMSG', '12ZAAAAAB', ':\x01PING', '762382207\x01']
        # Réponse a un CTCP VERSION
        try:
            scopy = server_msg.copy()
            nickname = self._ctx.User.get_nickname(self._ctx.Utils.clean_uid(scopy[1]))
            dnickname = self._ctx.Config.SERVICE_NICKNAME
            arg = scopy[4].replace(':', '')

            if nickname is None:
                self._ctx.Logs.debug(scopy)
                return None

            if arg == '\x01PING':
                recieved_unixtime = int(scopy[5].replace('\x01',''))
                current_unixtime = self._ctx.Utils.get_unixtime()
                ping_response = current_unixtime - recieved_unixtime

                # self._ctx.Irc.send2socket(f':{dnickname} NOTICE {nickname} :\x01PING {ping_response} secs\x01')
                await self.send_notice(
                    nick_from=dnickname,
                    nick_to=nickname,
                    msg=f"\x01PING {ping_response} secs\x01"
                )
                self._ctx.Logs.debug(scopy)

            return None
        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_version_msg(self, server_msg: list[str]) -> None:
        """Handle version coming from the server
        \n ex. /version Defender
        Args:
            server_msg (list[str]): Original message from the server
        """
        try:
            # ['@label=0073', ':0014E7P06', 'VERSION', 'PyDefender']
            scopy = server_msg.copy()
            if '@' in list(scopy[0])[0]:
                scopy.pop(0)

            u = self._ctx.User.get_user(self._ctx.Utils.clean_uid(scopy[0]))

            if u is None:
                return None

            response_351 = f"{self._ctx.Config.SERVICE_NAME.capitalize()}-{self._ctx.Config.CURRENT_VERSION} {self._ctx.Config.SERVICE_HOST} {self.name}"
            await self.send2socket(f':{self._ctx.Config.SERVICE_HOST} 351 {u.nickname} {response_351}')

            modules = self._ctx.ModuleUtils.get_all_available_modules()
            response_005 = ' | '.join(modules)
            await self.send2socket(f':{self._ctx.Config.SERVICE_HOST} 005 {u.nickname} {response_005} are supported by this server')

            response_005 = ''.join(self._ctx.Settings.PROTOCTL_USER_MODES)
            await self.send2socket(f":{self._ctx.Config.SERVICE_HOST} 005 {u.nickname} {response_005} are supported by this server")

            return None

        except Exception as err:
            self._ctx.Logs.error(f"{__name__} - General Error: {err}")

    async def on_smod(self, server_msg: list[str]) -> None:
        """Handle SMOD message coming from the server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':001', 'SMOD', ':L:history_backend_mem:2.0', 'L:channeldb:1.0', 'L:tkldb:1.10', 'L:staff:3.8', 'L:ircops:3.71', ...]
            scopy = server_msg.copy()
            modules = [m.lstrip(':') for m in scopy[2:]]

            for smod in modules:
                smod_split = smod.split(':')
                smodobj = self._ctx.Definition.MSModule(type=smod_split[0], name=smod_split[1], version=smod_split[2])
                self._ctx.Settings.SMOD_MODULES.append(smodobj)

        except Exception as err:
            self._ctx.Logs.error(f'General Error: {err}')

    async def on_sasl(self, server_msg: list[str]) -> Optional['MSasl']:
        """Handle SASL coming from a server

        Args:
            server_msg (list[str]): Original server message
        """
        try:
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'H', '172.18.128.1', '172.18.128.1']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'S', 'PLAIN']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '0014ZZH1F', 'S', 'EXTERNAL', 'zzzzzzzkey']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'C', 'sasakey==']
            # [':irc.local.org', 'SASL', 'defender-dev.deb.biz.st', '00157Z26U', 'D', 'A']
            if not self._ctx.Config.SASL_ACTIVE:
                None

            scopy = server_msg.copy()
            psasl = self._ctx.Sasl
            sasl_enabled = False
            for smod in self._ctx.Settings.SMOD_MODULES:
                if smod.name == 'sasl':
                    sasl_enabled = True
                    break

            if not sasl_enabled:
                return None

            client_uid = scopy[3] if len(scopy) >= 6 else None
            sasl_message_type = scopy[4] if len(scopy) >= 6 else None
            psasl.insert_sasl_client(self._ctx.Definition.MSasl(client_uid=client_uid))
            sasl_obj = psasl.get_sasl_obj(client_uid)

            if sasl_obj is None:
                return None

            match sasl_message_type:
                case 'H':
                    sasl_obj.remote_ip = str(scopy[5])
                    sasl_obj.message_type = sasl_message_type
                    return sasl_obj

                case 'S':
                    sasl_obj.message_type = sasl_message_type
                    if str(scopy[5]) in ['PLAIN', 'EXTERNAL']:
                        sasl_obj.mechanisme = str(scopy[5])

                    if sasl_obj.mechanisme == "PLAIN":
                        await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} SASL {self._ctx.Settings.MAIN_SERVER_HOSTNAME} {sasl_obj.client_uid} C +")
                    elif sasl_obj.mechanisme == "EXTERNAL":
                        if str(scopy[5]) == "+":
                            return None

                        sasl_obj.fingerprint = str(scopy[6])
                        await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} SASL {self._ctx.Settings.MAIN_SERVER_HOSTNAME} {sasl_obj.client_uid} C +")

                    await self.on_sasl_authentication_process(sasl_obj)
                    return sasl_obj

                case 'C':
                    if sasl_obj.mechanisme == "PLAIN":
                        credentials = scopy[5]
                        decoded_credentials = b64decode(credentials).decode()
                        user, username, password = decoded_credentials.split('\0')

                        sasl_obj.message_type = sasl_message_type
                        sasl_obj.username = username
                        sasl_obj.password = password

                        await self.on_sasl_authentication_process(sasl_obj)
                        return sasl_obj
                    elif sasl_obj.mechanisme == "EXTERNAL":
                        sasl_obj.message_type = sasl_message_type

                        await self.on_sasl_authentication_process(sasl_obj)
                        return sasl_obj

        except Exception as err:
            self._ctx.Logs.error(f'General Error: {err}', exc_info=True)

    async def on_sasl_authentication_process(self, sasl_model: 'MSasl') -> None:
        if not self._ctx.Config.SASL_ACTIVE:
            return None

        s = sasl_model
        if sasl_model:
            async def db_get_admin_info(*, username: Optional[str] = None, password: Optional[str] = None, fingerprint: Optional[str] = None) -> Optional[dict[str, Any]]:
                if fingerprint:
                    mes_donnees = {'fingerprint': fingerprint}
                    query = f"SELECT user, level, language FROM {self._ctx.Config.TABLE_ADMIN} WHERE fingerprint = :fingerprint"
                else:
                    mes_donnees = {'user': username, 'password': self._ctx.Utils.hash_password(password)}
                    query = f"SELECT user, level, language FROM {self._ctx.Config.TABLE_ADMIN} WHERE user = :user AND password = :password"

                result = await self._ctx.Base.db_execute_query(query, mes_donnees)
                user_from_db = result.fetchone()
                if user_from_db:
                    return {'user': user_from_db[0], 'level': user_from_db[1], 'language': user_from_db[2]}
                else:
                    return None

            if s.message_type == 'C' and s.mechanisme == 'PLAIN':
                # Connection via PLAIN
                admin_info = await db_get_admin_info(username=s.username, password=s.password)
                if admin_info is not None:
                    s.auth_success = True
                    s.level = admin_info.get('level', 0)
                    s.language = admin_info.get('language', 'EN')
                    await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} SASL {self._ctx.Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D S")
                    await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} 903 {s.username} :SASL authentication successful")
                else:
                    await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} SASL {self._ctx.Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D F")
                    await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} 904 {s.username} :SASL authentication failed")

            elif s.message_type == 'S' and s.mechanisme == 'EXTERNAL':
                # Connection using fingerprints
                admin_info = await db_get_admin_info(fingerprint=s.fingerprint)
                
                if admin_info is not None:
                    s.auth_success = True
                    s.level = admin_info.get('level', 0)
                    s.username = admin_info.get('user', None)
                    s.language = admin_info.get('language', 'EN')
                    await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} SASL {self._ctx.Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D S")
                    await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} 903 {s.username} :SASL authentication successful")
                else:
                    # "904 <nick> :SASL authentication failed"
                    await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} SASL {self._ctx.Settings.MAIN_SERVER_HOSTNAME} {s.client_uid} D F")
                    await self.send2socket(f":{self._ctx.Config.SERVEUR_LINK} 904 {s.username} :SASL authentication failed")

    async def on_md(self, server_msg: list[str]) -> None:
        """Handle MD responses
        [':001', 'MD', 'client', '001MYIZ03', 'certfp', ':d1235648...']
        Args:
            server_msg (list[str]): The server reply
        """
        try:
            scopy = server_msg.copy()
            # available_vars = ['creationtime', 'certfp', 'tls_cipher']

            uid = str(scopy[3])
            var = str(scopy[4]).lower()
            value = str(scopy[5]).replace(':', '')

            user_obj = self._ctx.User.get_user(uid)
            if user_obj is None:
                return None
            
            match var:
                case 'certfp':
                    user_obj.fingerprint = value
                case 'tls_cipher':
                    user_obj.tls_cipher = value
                case _:
                    return None

        except Exception as e:
            self._ctx.Logs.error(f"General Error: {e}")

    async def on_kick(self, server_msg: list[str]) -> None:
        """When a user is kicked out from a channel

        ['@unrealircd.org/issued-by=RPC:admin-for-test@...', ':001', 'KICK', '#jsonrpc', '001ELW13T', ':Kicked', 'from', 'JSONRPC', 'User']
        Args:
            server_msg (list[str]): The server message
        """
        scopy = server_msg.copy()
        uid = scopy[4]
        channel = scopy[3]

        # Delete the user from the channel.
        self._ctx.Channel.delete_user_from_channel(channel, uid)
        return None

    async def on_sethost(self, server_msg: list[str]) -> None:
        """On SETHOST command
        >>> [':001DN7305', 'SETHOST', ':netadmin.example.org']

        Args:
            server_msg (list[str]): _description_
        """
        scopy = server_msg.copy()
        uid = self._ctx.User.clean_uid(scopy[0])
        vhost = scopy[2].lstrip(':')
        user = self._ctx.User.get_user(uid)
        user.vhost = vhost
