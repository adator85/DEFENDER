from re import match, findall
from datetime import datetime
from typing import TYPE_CHECKING
from ssl import SSLEOFError, SSLError

if TYPE_CHECKING:
    from core.irc import Irc

class Inspircd:

    def  __init__(self, ircInstance: 'Irc'):
        self.name = 'InspIRCd-4'

        self.__Irc = ircInstance
        self.__Config = ircInstance.Config
        self.__Base = ircInstance.Base
        self.__Utils = ircInstance.Loader.Utils
        self.__Logs = ircInstance.Loader.Logs

        self.__Logs.info(f"** Loading protocol [{__name__}]")

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
            User_from    = self.__Irc.User.get_User(nick_from)
            User_to      = self.__Irc.User.get_User(nick_to) if nick_to is None else None

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

        password = self.__Config.SERVEUR_PASSWORD
        link = self.__Config.SERVEUR_LINK
        server_id = self.__Config.SERVEUR_ID
        service_id = self.__Config.SERVICE_ID

        version = self.__Config.CURRENT_VERSION
        unixtime = self.__Utils.get_unixtime()


        self.send2socket(f"CAPAB START 1206")
        self.send2socket(f"CAPAB CAPABILITIES :NICKMAX=30 CHANMAX=64 MAXMODES=20 IDENTMAX=10 MAXQUIT=255 MAXTOPIC=307 MAXKICK=255 MAXREAL=128 MAXAWAY=200 MAXHOST=64 MAXLINE=512 CASEMAPPING=ascii GLOBOPS=0")
        self.send2socket(f"CAPAB END")
        self.send2socket(f"SERVER {link} {password} {server_id} :{info}")
        self.send2socket(f"BURST {unixtime}")
        self.send2socket(f":{server_id} ENDBURST")

        self.__Logs.debug(f'>> {__name__} Link information sent to the server')

    def gline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + G user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL + G {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def send_set_nick(self, newnickname: str) -> None:

        self.send2socket(f":{self.__Config.SERVICE_NICKNAME} NICK {newnickname}")
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

    def send_sjoin(self, channel: str) -> None:

        if not self.__Irc.Channel.is_valid_channel(channel):
            self.__Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{self.__Config.SERVEUR_ID} SJOIN {self.__Utils.get_unixtime()} {channel} + :{self.__Config.SERVICE_ID}")

        # Add defender to the channel uids list
        self.__Irc.Channel.insert(self.__Irc.Loader.Definition.MChannel(name=channel, uids=[self.__Config.SERVICE_ID]))
        return None

    def send_quit(self, uid: str, reason: str, print_log: True) -> None:
        """Send quit message

        Args:
            uidornickname (str): The UID or the Nickname
            reason (str): The reason for the quit
        """
        user_obj = self.__Irc.User.get_User(uidornickname=uid)
        clone_obj = self.__Irc.Clone.get_clone(uidornickname=uid)
        reputationObj = self.__Irc.Reputation.get_Reputation(uidornickname=uid)

        if not user_obj is None:
            self.send2socket(f":{user_obj.uid} QUIT :{reason}", print_log=print_log)
            self.__Irc.User.delete(user_obj.uid)

        if not clone_obj is None:
            self.__Irc.Clone.delete(clone_obj.uid)

        if not reputationObj is None:
            self.__Irc.Reputation.delete(reputationObj.uid)

        if not self.__Irc.Channel.delete_user_from_all_channel(uid):
            self.__Logs.error(f"The UID [{uid}] has not been deleted from all channels")

        return None

    def send_uid(self, nickname:str, username: str, hostname: str, uid:str, umodes: str, vhost: str, remote_ip: str, realname: str, print_log: bool = True) -> None:
        """Send UID to the server

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

        userObj = self.__Irc.User.get_User(uidornickname)
        passwordChannel = password if not password is None else ''

        if userObj is None:
            return None

        if not self.__Irc.Channel.is_valid_channel(channel):
            self.__Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{userObj.uid} JOIN {channel} {passwordChannel}", print_log=print_log)

        # Add defender to the channel uids list
        self.__Irc.Channel.insert(self.__Irc.Loader.Definition.MChannel(name=channel, uids=[userObj.uid]))
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
            self.__Logs.error(f"The user [{uidornickname}] is not valid")
            return None

        if not self.__Irc.Channel.is_valid_channel(channel):
            self.__Logs.error(f"The channel [{channel}] is not valid")
            return None

        self.send2socket(f":{userObj.uid} PART {channel}", print_log=print_log)

        # Add defender to the channel uids list
        self.__Irc.Channel.delete_user_from_channel(channel, userObj.uid)
        return None

    def send_unkline(self, nickname:str, hostname: str) -> None:

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL - K {nickname} {hostname} {self.__Config.SERVICE_NICKNAME}")

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
            self.__Irc.Reputation.delete(uid_who_quit)
            self.__Irc.Clone.delete(uid_who_quit)

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
        if len(serverMsg) > 5:
            if '=' in serverMsg[5]:
                serveur_hosting_id = str(serverMsg[5]).split('=')
                self.__Config.HSID = serveur_hosting_id[1]

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
            serverMsg.pop(0)
            channel = str(serverMsg[3]).lower()
            len_cmd = len(serverMsg)
            list_users:list = []
            occurence = 0
            start_boucle = 0

            # Trouver le premier user
            for i in range(len_cmd):
                s: list = findall(fr':', serverMsg[i])
                if s:
                    occurence += 1
                    if occurence == 2:
                        start_boucle = i

            # Boucle qui va ajouter l'ensemble des users (UID)
            for i in range(start_boucle, len(serverMsg)):
                parsed_UID = str(serverMsg[i])
                clean_uid = self.__Utils.clean_uid(parsed_UID)
                if not clean_uid is None and len(clean_uid) == 9:
                    list_users.append(parsed_UID)

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
            # ['@unrealircd.org/geoip=FR;unrealircd.org/userhost=50d6492c@80.214.73.44;unrealircd.org/userip=50d6492c@80.214.73.44;msgid=YSIPB9q4PcRu0EVfC9ci7y-/mZT0+Gj5FLiDSZshH5NCw;time=2024-08-15T15:35:53.772Z', 
            # ':001EPFBRD', 'PART', '#welcome', ':WEB', 'IRC', 'Paris']

            uid = str(serverMsg[1]).lstrip(':')
            channel = str(serverMsg[3]).lower()
            self.__Irc.Channel.delete_user_from_channel(channel, uid)

            return None

        except IndexError as ie:
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
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

            if geoip_match:
                geoip = geoip_match.group(1)
            else:
                geoip = None

            score_connexion = 0

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
            self.__Logs.error(f"{__name__} - Index Error: {ie}")
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_server_ping(self, serverMsg: list[str]) -> None:
        """Send a PONG message to the server

        Args:
            serverMsg (list[str]): List of str coming from the server
        """
        try:
            # InspIRCd 3:
            # <- :3IN PING 808
            # -> :808 PONG 3IN

            hsid = str(serverMsg[0]).replace(':','')
            self.send2socket(f":{self.__Config.SERVEUR_ID} PONG {hsid}", print_log=True)

            return None
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

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
        # ['@unrealircd.org/userhost=StatServ@stats.deb.biz.st;draft/bot;bot;msgid=ehfAq3m2yjMjhgWEfi1UCS;time=2024-10-26T13:49:06.299Z', ':001INC60B', 'PRIVMSG', '12ZAAAAAB', ':\x01PING', '762382207\x01']
        # Réponse a un CTCP VERSION
        try:

            nickname = self.__Irc.User.get_nickname(self.__Utils.clean_uid(serverMsg[1]))
            dnickname = self.__Config.SERVICE_NICKNAME
            arg = serverMsg[4].replace(':', '')

            if nickname is None:
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

            return None
        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")

    def on_version_msg(self, serverMsg: list[str]) -> None:
        """Handle version coming from the server

        Args:
            serverMsg (list[str]): Original message from the server
        """
        try:
            # ['@label=0073', ':0014E7P06', 'VERSION', 'PyDefender']
            getUser  = self.__Irc.User.get_User(self.__Utils.clean_uid(serverMsg[1]))

            if getUser is None:
                return None

            response_351 = f"{self.__Config.SERVICE_NAME.capitalize()}-{self.__Config.CURRENT_VERSION} {self.__Config.SERVICE_HOST} {self.name}"
            self.send2socket(f':{self.__Config.SERVICE_HOST} 351 {getUser.nickname} {response_351}')

            modules = self.__Base.get_all_modules()
            response_005 = ' | '.join(modules)
            self.send2socket(f':{self.__Config.SERVICE_HOST} 005 {getUser.nickname} {response_005} are supported by this server')

            return None

        except Exception as err:
            self.__Logs.error(f"{__name__} - General Error: {err}")
