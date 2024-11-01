from typing import TYPE_CHECKING
from ssl import SSLEOFError, SSLError

if TYPE_CHECKING:
    from core.irc import Irc

class Unrealircd6:

    def  __init__(self, ircInstance: 'Irc'):
        self.__Irc = ircInstance
        self.__Config = ircInstance.Config
        self.__Base = ircInstance.Base

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

        except UnicodeDecodeError:
            self.__Base.logs.error(f'Decode Error try iso-8859-1 - message: {message}')
            self.__Irc.IrcSocket.send(f"{message}\r\n".encode(self.__Config.SERVEUR_CHARSET[0],'replace'))
        except UnicodeEncodeError:
            self.__Base.logs.error(f'Encode Error try iso-8859-1 - message: {message}')
            self.__Irc.IrcSocket.send(f"{message}\r\n".encode(self.__Config.SERVEUR_CHARSET[0],'replace'))
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

    def sendPrivMsg(self, nick_from: str, msg: str, channel: str = None, nick_to: str = None):
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

    def sendNotice(self, nick_from: str, nick_to: str, msg: str) -> None:
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

        password = self.__Config.SERVEUR_PASSWORD
        link = self.__Config.SERVEUR_LINK
        server_id = self.__Config.SERVEUR_ID
        service_id = self.__Config.SERVICE_ID

        version = self.__Config.CURRENT_VERSION
        unixtime = self.__Base.get_unixtime()

        self.send2socket(f":{server_id} PASS :{password}")
        self.send2socket(f":{server_id} PROTOCTL SID NOQUIT NICKv2 SJOIN SJ3 NICKIP TKLEXT2 NEXTBANS CLK EXTSWHOIS MLOCK MTAGS")
        # self.__Irc.send2socket(f":{sid} PROTOCTL NICKv2 VHP UMODE2 NICKIP SJOIN SJOIN2 SJ3 NOQUIT TKLEXT MLOCK SID MTAGS")
        self.send2socket(f":{server_id} PROTOCTL EAUTH={link},,,{service_name}-v{version}")
        self.send2socket(f":{server_id} PROTOCTL SID={server_id}")
        self.send2socket(f":{server_id} SERVER {link} 1 :{info}")
        self.send2socket(f":{server_id} {nickname} :Reserved for services")
        #self.__Irc.send2socket(f":{sid} UID {nickname} 1 {unixtime} {username} {host} {service_id} * {smodes} * * * :{realname}")
        self.send2socket(f":{server_id} UID {nickname} 1 {unixtime} {username} {host} {service_id} * {smodes} * * fwAAAQ== :{realname}")
        # self.__Irc.send2socket(f":{server_id} SJOIN {unixtime} {chan} + :{service_id}")
        self.sjoin(chan)
        self.send2socket(f":{server_id} TKL + Q * {nickname} {host} 0 {unixtime} :Reserved for services")

        self.send2socket(f":{service_id} MODE {chan} {cmodes}")
        self.send2socket(f":{service_id} MODE {chan} {umodes} {service_id}")

        self.__Base.logs.debug(f'>> {__name__} Link information sent to the server')

    def gline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + G user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL + G {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def set_nick(self, newnickname: str) -> None:

        self.send2socket(f":{self.__Config.SERVICE_NICKNAME} NICK {newnickname}")
        return None

    def squit(self, server_id: str, server_link: str, reason: str) -> None:

        self.send2socket(f":{server_id} SQUIT {server_link} :{reason}")
        return None

    def ungline(self, nickname:str, hostname: str) -> None:

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL - G {nickname} {hostname} {self.__Config.SERVICE_NICKNAME}")

        return None

    def kline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        # TKL + k user host set_by expire_timestamp set_at_timestamp :reason

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL + k {nickname} {hostname} {set_by} {expire_timestamp} {set_at_timestamp} :{reason}")

        return None

    def sjoin(self, channel: str) -> None:

        self.send2socket(f":{self.__Config.SERVEUR_ID} SJOIN {self.__Base.get_unixtime()} {channel} + :{self.__Config.SERVICE_ID}")

        # Add defender to the channel uids list
        self.__Irc.Channel.insert(self.__Irc.Loader.Definition.MChannel(name=channel, uids=[self.__Config.SERVICE_ID]))
        return None

    def join(self, uidornickname: str, channel: str, password: str = None, print_log: bool = True) -> None:
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
            return None

        self.send2socket(f":{userObj.uid} JOIN {channel} {passwordChannel}", print_log=print_log)

        # Add defender to the channel uids list
        self.__Irc.Channel.insert(self.__Irc.Loader.Definition.MChannel(name=channel, uids=[userObj.uid]))
        return None

    def part(self, uidornickname:str, channel: str, print_log: bool = True) -> None:
        """Part from a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            print_log (bool, optional): Write logs. Defaults to True.
        """

        userObj = self.__Irc.User.get_User(uidornickname)

        if userObj is None:
            return None

        if not self.__Irc.Channel.Is_Channel(channel):
            return None

        self.send2socket(f":{userObj.uid} PART {channel}", print_log=print_log)

        # Add defender to the channel uids list
        self.__Irc.Channel.delete_user_from_channel(channel, userObj.uid)
        return None

    def unkline(self, nickname:str, hostname: str) -> None:

        self.send2socket(f":{self.__Config.SERVEUR_ID} TKL - K {nickname} {hostname} {self.__Config.SERVICE_NICKNAME}")

        return None

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
                self.sendNotice(
                    nick_from=dnickname,
                    nick_to=nickname,
                    msg=f"\x01PING {ping_response} secs\x01"
                )

            return None
        except Exception as err:
            self.__Base.logs.error(f"{__name__} - General Error: {err}")

    def on_version_msg(self, serverMsg: list[str]) -> None:

        # ['@label=0073', ':0014E7P06', 'VERSION', 'PyDefender']
        getUser  = self.__Irc.User.get_User(self.__Irc.User.clean_uid(serverMsg[1]))

        if getUser is None:
            return None

        self.send2socket(f'{self.__Config.SERVEUR_ID} 351 {getUser.nickname} {self.__Config.CURRENT_VERSION} {self.__Config.SERVICE_NAME} *:')