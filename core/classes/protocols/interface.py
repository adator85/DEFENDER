from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
from core.classes.protocols.command_handler import CommandHandler

if TYPE_CHECKING:
    from core.definition import MClient, MSasl
    from core.irc import Irc

class IProtocol(ABC):

    Handler: Optional[CommandHandler] = None

    def __init__(self, uplink: 'Irc'):
        self.name: Optional[str] = None
        self.protocol_version: int = -1
        self.known_protocol: set[str] = {}

        self._Irc = uplink
        self._Config = uplink.Config
        self._Base = uplink.Base
        self._Settings = uplink.Base.Settings
        self._Utils = uplink.Loader.Utils
        self._Logs = uplink.Loader.Logs

        self.Handler = CommandHandler(uplink.Loader)

        self.init_protocol()

        self._Logs.info(f"[PROTOCOL] Protocol [{self.__class__.__name__}] loaded!")

    @abstractmethod
    def init_protocol(self):
        """_summary_

        Returns:
            _type_: _description_
        """

    @abstractmethod
    def get_ircd_protocol_poisition(self, cmd: list[str], log: bool = False) -> tuple[int, Optional[str]]:
        """Get the position of known commands

        Args:
            cmd (list[str]): The server response
            log (bool): If true it will log in the logger

        Returns:
            tuple[int, Optional[str]]: The position and the command.
        """

    @abstractmethod
    def register_command(self):
        """Register all commands that you need to handle
        """

    @abstractmethod
    def send2socket(self, message: str, print_log: bool = True) -> None:
        """Envoit les commandes à envoyer au serveur.

        Args:
            message (str): contient la commande à envoyer au serveur.
            print_log (bool): If True then print logs
        """

    @abstractmethod
    def send_priv_msg(self, nick_from: str, msg: str, channel: str = None, nick_to: str = None):
        """Sending PRIVMSG to a channel or to a nickname by batches
        could be either channel or nickname not both together
        Args:
            msg (str): The message to send
            nick_from (str): The sender nickname
            channel (str, optional): The receiver channel. Defaults to None.
            nick_to (str, optional): The reciever nickname. Defaults to None.
        """

    @abstractmethod
    def send_notice(self, nick_from: str, nick_to: str, msg: str) -> None:
        """Sending NOTICE by batches

        Args:
            msg (str): The message to send to the server
            nick_from (str): The sender Nickname
            nick_to (str): The reciever nickname
        """

    @abstractmethod
    def send_link(self) -> None:
        """Créer le link et envoyer les informations nécessaires pour la 
        connexion au serveur.
        """

    @abstractmethod
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

    @abstractmethod
    def send_set_nick(self, newnickname: str) -> None:
        """Change nickname of the server
        \n This method will also update the User object
        Args:
            newnickname (str): New nickname of the server
        """

    @abstractmethod
    def send_set_mode(self, modes: str, *, nickname: Optional[str] = None, channel_name: Optional[str] = None, params: Optional[str] = None) -> None:
        """Set a mode to channel or to a nickname or for a user in a channel

        Args:
            modes (str): The selected mode
            nickname (Optional[str]): The nickname
            channel_name (Optional[str]): The channel name
            params (Optional[str]): Parameters like password.
        """

    @abstractmethod
    def send_squit(self, server_id: str, server_link: str, reason: str) -> None:
        """_summary_

        Args:
            server_id (str): _description_
            server_link (str): _description_
            reason (str): _description_
        """

    @abstractmethod
    def send_ungline(self, nickname:str, hostname: str) -> None:
        """_summary_

        Args:
            nickname (str): _description_
            hostname (str): _description_
        """

    @abstractmethod
    def send_kline(self, nickname: str, hostname: str, set_by: str, expire_timestamp: int, set_at_timestamp: int, reason: str) -> None:
        """_summary_

        Args:
            nickname (str): _description_
            hostname (str): _description_
            set_by (str): _description_
            expire_timestamp (int): _description_
            set_at_timestamp (int): _description_
            reason (str): _description_
        """

    @abstractmethod
    def send_unkline(self, nickname:str, hostname: str) -> None:
        """_summary_

        Args:
            nickname (str): _description_
            hostname (str): _description_
        """

    @abstractmethod
    def send_sjoin(self, channel: str) -> None:
        """Server will join a channel with pre defined umodes

        Args:
            channel (str): Channel to join
        """

    @abstractmethod
    def send_sapart(self, nick_to_sapart: str, channel_name: str) -> None:
        """_summary_

        Args:
            nick_to_sapart (str): _description_
            channel_name (str): _description_
        """

    @abstractmethod
    def send_sajoin(self, nick_to_sajoin: str, channel_name: str) -> None:
        """_summary_

        Args:
            nick_to_sajoin (str): _description_
            channel_name (str): _description_
        """

    @abstractmethod
    def send_svspart(self, nick_to_part: str, channels: list[str], reason: str) -> None:
        """_summary_

        Args:
            nick_to_part (str): _description_
            channels (list[str]): _description_
            reason (str): _description_
        """

    @abstractmethod
    def send_svsjoin(self, nick_to_part: str, channels: list[str], keys: list[str]) -> None:
        """_summary_

        Args:
            nick_to_part (str): _description_
            channels (list[str]): _description_
            keys (list[str]): _description_
        """

    @abstractmethod
    def send_svsmode(self, nickname: str, user_mode: str) -> None:
        """_summary_

        Args:
            nickname (str): _description_
            user_mode (str): _description_
        """

    @abstractmethod
    def send_svs2mode(self, nickname: str, user_mode: str) -> None:
        """_summary_

        Args:
            nickname (str): _description_
            user_mode (str): _description_
        """

    @abstractmethod
    def send_svslogin(self, client_uid: str, user_account: str) -> None:
        """Log a client into his account.

        Args:
            client_uid (str): Client UID
            user_account (str): The account of the user
        """

    @abstractmethod
    def send_svslogout(self, client_obj: 'MClient') -> None:
        """Logout a client from his account

        Args:
            client_obj (MClient): The Client UID
        """

    @abstractmethod
    def send_quit(self, uid: str, reason: str, print_log: bool = True) -> None:
        """Send quit message
        - Delete uid from User object
        - Delete uid from Reputation object

        Args:
            uid (str): The UID or the Nickname
            reason (str): The reason for the quit
            print_log (bool): If True then print logs
        """

    @abstractmethod
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

    @abstractmethod
    def send_join_chan(self, uidornickname: str, channel: str, password: str = None, print_log: bool = True) -> None:
        """Joining a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            password (str, optional): The password of the channel to join. Default to None
            print_log (bool, optional): Write logs. Defaults to True.
        """

    @abstractmethod
    def send_part_chan(self, uidornickname:str, channel: str, print_log: bool = True) -> None:
        """Part from a channel

        Args:
            uidornickname (str): UID or nickname that need to join
            channel (str): channel to join
            print_log (bool, optional): Write logs. Defaults to True.
        """

    @abstractmethod
    def send_mode_chan(self, channel_name: str, channel_mode: str) -> None:
        """_summary_

        Args:
            channel_name (str): _description_
            channel_mode (str): _description_
        """

    @abstractmethod
    def send_raw(self, raw_command: str) -> None:
        """Send raw message to the server

        Args:
            raw_command (str): The raw command you want to send.
        """

    # ------------------------------------------------------------------------
    #                           COMMON IRC PARSER
    # ------------------------------------------------------------------------

    @abstractmethod
    def parse_uid(self, serverMsg: list[str]) -> dict[str, str]:
        """Parse UID and return dictionary.

        Args:
            serverMsg (list[str]): The UID IRCD message
        
        Returns:
            dict[str, str]: The response as dictionary.
        """

    @abstractmethod
    def parse_quit(self, serverMsg: list[str]) -> dict[str, str]:
        """Parse quit and return dictionary.
        >>> [':97KAAAAAB', 'QUIT', ':Quit:', 'this', 'is', 'my', 'reason', 'to', 'quit']
        Args:
            serverMsg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The response as dictionary.
        """

    @abstractmethod
    def parse_nick(self, serverMsg: list[str]) -> dict[str, str]:
        """Parse nick changes and return dictionary.
        >>> [':97KAAAAAC', 'NICK', 'testinspir', '1757360740']

        Args:
            serverMsg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The response as dictionary.
        """

    @abstractmethod
    def parse_privmsg(self, serverMsg: list[str]) -> dict[str, str]:
        """Parse PRIVMSG message.
        >>> [':97KAAAAAE', 'PRIVMSG', '#welcome', ':This', 'is', 'my', 'public', 'message']

        Args:
            serverMsg (list[str]): The server message to parse

        Returns:
            dict[str, str]: The response as dictionary.
            ```python 
            response = {
                "uid": '97KAAAAAE',
                "channel": '#welcome',
                "message": 'This is my public message'
            }
            ```
        """

    # ------------------------------------------------------------------------
    #                           EVENT HANDLER
    # ------------------------------------------------------------------------

    @abstractmethod
    def on_svs2mode(self, serverMsg: list[str]) -> None:
        """Handle svs2mode coming from a server
        >>> [':00BAAAAAG', 'SVS2MODE', '001U01R03', '-r']

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_mode(self, serverMsg: list[str]) -> None:
        """Handle mode coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_umode2(self, serverMsg: list[str]) -> None:
        """Handle umode2 coming from a server
        >>> [':adator_', 'UMODE2', '-i']

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_quit(self, serverMsg: list[str]) -> None:
        """Handle quit coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_squit(self, serverMsg: list[str]) -> None:
        """Handle squit coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_protoctl(self, serverMsg: list[str]) -> None:
        """Handle protoctl coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_nick(self, serverMsg: list[str]) -> None:
        """Handle nick coming from a server
        new nickname

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_sjoin(self, serverMsg: list[str]) -> None:
        """Handle sjoin coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_part(self, serverMsg: list[str]) -> None:
        """Handle part coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_eos(self, serverMsg: list[str]) -> None:
        """Handle EOS coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_reputation(self, serverMsg: list[str]) -> None:
        """Handle REPUTATION coming from a server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_uid(self, serverMsg: list[str]) -> None:
        """Handle uid message coming from the server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_privmsg(self, serverMsg: list[str]) -> None:
        """Handle PRIVMSG message coming from the server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_server_ping(self, serverMsg: list[str]) -> None:
        """Send a PONG message to the server

        Args:
            serverMsg (list[str]): List of str coming from the server
        """

    @abstractmethod
    def on_server(self, serverMsg: list[str]) -> None:
        """_summary_

        Args:
            serverMsg (list[str]): _description_
        """

    @abstractmethod
    def on_version(self, serverMsg: list[str]) -> None:
        """Sending Server Version to the server

        Args:
            serverMsg (list[str]): List of str coming from the server
        """

    @abstractmethod
    def on_time(self, serverMsg: list[str]) -> None:
        """Sending TIME answer to a requestor

        Args:
            serverMsg (list[str]): List of str coming from the server
        """

    @abstractmethod
    def on_ping(self, serverMsg: list[str]) -> None:
        """Sending a PING answer to requestor

        Args:
            serverMsg (list[str]): List of str coming from the server
        """

    @abstractmethod
    def on_version_msg(self, serverMsg: list[str]) -> None:
        """Handle version coming from the server
        \n ex. /version Defender
        Args:
            serverMsg (list[str]): Original message from the server
        """

    @abstractmethod
    def on_smod(self, serverMsg: list[str]) -> None:
        """Handle SMOD message coming from the server

        Args:
            serverMsg (list[str]): Original server message
        """

    @abstractmethod
    def on_sasl(self, serverMsg: list[str]) -> Optional['MSasl']:
        """Handle SASL coming from a server

        Args:
            serverMsg (list[str]): Original server message

        Returns:

        """

    @abstractmethod
    def on_sasl_authentication_process(self, sasl_model: 'MSasl') -> bool:
        """Finalize sasl authentication

        Args:
            sasl_model (MSasl): The sasl dataclass model

        Returns:
            bool: True if success
        """

    @abstractmethod
    def on_md(self, serverMsg: list[str]) -> None:
        """Handle MD responses
        [':001', 'MD', 'client', '001MYIZ03', 'certfp', ':d1235648...']
        Args:
            serverMsg (list[str]): The server reply
        """

    @abstractmethod
    def on_kick(self, serverMsg: list[str]) -> None:
        """When a user is kicked out from a channel

        Eg. ['@unrealircd.org...', ':001', 'KICK', '#jsonrpc', '001ELW13T', ':Kicked', 'from', 'JSONRPC', 'User']
        Args:
            serverMsg (list[str]): The server message
        """
