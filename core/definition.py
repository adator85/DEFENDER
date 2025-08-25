from datetime import datetime
from json import dumps
from dataclasses import dataclass, field, asdict, fields
from typing import Literal, Any, Optional
from os import sep

@dataclass
class MainModel:
    """Parent Model contains important methods"""
    def to_dict(self) -> dict[str, Any]:
        """Return the fields of a dataclass instance as a new dictionary mapping field names to field values."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Return the object of a dataclass a json str."""
        return dumps(self.to_dict())

    def get_attributes(self) -> list[str]:
        """Return a list of attributes name"""
        return [f.name for f in fields(self)]

@dataclass
class MClient(MainModel):
    """Model Client for registred nickname"""
    uid: str = None
    account: str = None
    nickname: str = None
    username: str = None
    realname: str = None
    hostname: str = None
    umodes: str = None
    vhost: str = None
    fingerprint: str = None
    isWebirc: bool = False
    isWebsocket: bool = False
    remote_ip: str = None
    score_connexion: int = 0
    geoip: str = None
    connexion_datetime: datetime = field(default=datetime.now())

@dataclass
class MUser(MainModel):
    """Model User"""

    uid: str = None
    nickname: str = None
    username: str = None
    realname: str = None
    hostname: str = None
    umodes: str = None
    vhost: str = None
    fingerprint: str = None
    isWebirc: bool = False
    isWebsocket: bool = False
    remote_ip: str = None
    score_connexion: int = 0
    geoip: str = None
    connexion_datetime: datetime = field(default=datetime.now())

@dataclass
class MAdmin(MainModel):
    """Model Admin"""

    uid: str = None
    account: str = None
    nickname: str = None
    username: str = None
    realname: str = None
    hostname: str = None
    umodes: str = None
    vhost: str = None
    fingerprint: str = None
    isWebirc: bool = False
    isWebsocket: bool = False
    remote_ip: str = None
    score_connexion: int = 0
    geoip: str = None
    connexion_datetime: datetime = field(default=datetime.now())
    language: str = "EN"
    level: int = 0

@dataclass
class MReputation(MainModel):
    """Model Reputation"""
    uid: str = None
    nickname: str = None
    username: str = None
    realname: str = None
    hostname: str = None
    umodes: str = None
    vhost: str = None
    fingerprint: str = None
    isWebirc: bool = False
    isWebsocket: bool = False
    remote_ip: str = None
    score_connexion: int = 0
    geoip: str = None
    connexion_datetime: datetime = field(default=datetime.now())
    secret_code: str = None

@dataclass
class MChannel(MainModel):
    """Model Channel"""

    name: str = None
    """### Channel name 
    It include the #"""
    uids: list[str] = field(default_factory=list[str])
    """### List of UID available in the channel
    including their modes ~ @ % + *

    Returns:
        list: The list of UID's including theirs modes
    """

@dataclass
class ColorModel(MainModel):
    white: str  = "\x0300"
    black: str  = "\x0301"
    blue: str   = "\x0302"
    green: str  = "\x0303"
    red: str    = "\x0304"
    yellow: str = "\x0306"
    bold: str   = "\x02"
    nogc: str   = "\x03"
    underline: str = "\x1F"

@dataclass
class MConfig(MainModel):
    """Model Configuration"""

    SERVEUR_IP: str = "127.0.0.1"
    """Server public IP (could be 127.0.0.1 localhost)"""

    SERVEUR_HOSTNAME: str = "your.host.name"
    """IRC Server Hostname (your.hostname.extension)"""

    SERVEUR_LINK: str = "your.link.url"
    """The link hostname (should be the same as your unrealircd link block)"""

    SERVEUR_PORT: int = 6697
    """Server port as configured in your unrealircd link block"""

    SERVEUR_PASSWORD: str = "YOUR.STRONG.PASSWORD"
    """Your link password"""

    SERVEUR_ID: str = "Z01"
    """Service identification could be Z01 should be unique"""

    SERVEUR_SSL: bool = True
    """Activate SSL connexion"""

    SERVEUR_PROTOCOL: str = "unreal6"
    """Which server are you going to use. (default: unreal6)"""

    SERVEUR_CHARSET: list[str] = field(default_factory=list[str])
    """0: utf-8 | 1: iso-8859-1"""

    SERVICE_NAME: str = "Defender"
    """Service name (Ex. Defender)"""

    SERVICE_NICKNAME: str = "Defender"
    """Nickname of the service (Ex. Defender)"""

    SERVICE_REALNAME: str = "Defender IRC Service"
    """Realname of the service"""

    SERVICE_USERNAME: str = "Security"
    """Username of the service"""

    SERVICE_HOST: str = "Your.Service.Hostname"
    """The service hostname"""

    SERVICE_INFO: str = "Defender IRC Service"
    """Swhois of the service"""

    SERVICE_CHANLOG: str = "#services"
    """The channel used by the service (ex. #services)"""

    SERVICE_SMODES: str = "+ioqBS"
    """The service mode (ex. +ioqBS)"""

    SERVICE_CMODES: str = "ntsO"
    """The mode of the log channel (ex. ntsO)"""

    SERVICE_UMODES: str = "o"
    """The mode of the service when joining chanlog (ex. o, the service will be operator in the chanlog)"""

    SERVICE_PREFIX: str = "!"
    """The default prefix to communicate with the service"""

    SERVICE_ID: str = field(init=False)
    """The service unique ID"""

    LANG: str = "EN"
    """The default language of Defender. default: EN"""

    OWNER: str = "admin"
    """The nickname of the admin of the service"""

    PASSWORD: str = "password"
    """The password of the admin of the service"""

    JSONRPC_URL: str = None
    """The RPC url, if local https://127.0.0.1:PORT/api should be fine"""

    JSONRPC_PATH_TO_SOCKET_FILE: str = None
    """The full path of the socket file (/PATH/TO/YOUR/UNREALIRCD/SOCKET/FILE.socket)"""

    JSONRPC_METHOD: str = None
    """3 methods are available; requests/socket/unixsocket"""

    JSONRPC_USER: str = None
    """The RPC User defined in your unrealircd.conf"""

    JSONRPC_PASSWORD: str = None
    """The RPC Password defined in your unrealircd.conf"""

    SALON_JAIL: str = "#jail"
    """The JAIL channel (ex. #jail)"""

    SALON_JAIL_MODES: str = "sS"
    """The jail channel modes (ex. sS)"""

    SALON_LIBERER: str = "#welcome"
    """Channel where the nickname will be released"""

    CLONE_CHANNEL: str = "clones"
    """Channel where clones are hosted and will log PRIVMSG"""

    CLONE_CMODES: str = "+nts"
    """Clone channel modes (ex. +nts)"""

    CLONE_UMODES: str = '+iwxz'
    """Clone User modes (ex. +iwxz)"""

    CLONE_LOG_HOST_EXEMPT: list[str] = field(default_factory=list[str])
    """Hosts that clones will not log"""

    CLONE_CHANNEL_PASSWORD: str = "clone_Password_1234"
    """Clone password channel"""

    API_TIMEOUT: int = 60
    """Default api timeout in second. (default: 60)"""

    PORTS_TO_SCAN: list[int] = field(default_factory=list[int])
    """List of ports to scan available for proxy_scan in the mod_defender module"""

    WHITELISTED_IP: list[str] = field(default_factory=list[str])
    """List of remote IP to don't scan"""

    GLINE_DURATION: str = "30"
    """Gline duration"""

    DEBUG_LEVEL:Literal[10, 20, 30, 40, 50] = 20
    """Logs level: DEBUG 10 | INFO 20 | WARNING 30 | ERROR 40 | CRITICAL 50. (default: 20)"""

    DEBUG_HARD: bool = False
    """Adding filename, function name and the line number to the logs. Default False"""

    LOGGING_NAME: str = "defender"
    """The name of the Logging instance"""

    TABLE_CLIENT: str = "core_client"
    """Core Client table"""

    TABLE_ADMIN: str = "core_admin"
    """Core Admin table"""

    TABLE_COMMAND: str = "core_command"
    """Core command table"""

    TABLE_LOG: str = "core_log"
    """Core log table"""

    TABLE_MODULE: str = "core_module"
    """Core module table"""

    TABLE_CONFIG: str = "core_config"
    """Core configuration table"""

    TABLE_CHANNEL: str = "core_channel"
    """Core channel table"""

    CURRENT_VERSION: str = None
    """Current version of Defender"""

    LATEST_VERSION: str = None
    """The Latest version fetched from github"""

    DB_NAME: str = "defender"
    """The database name"""

    DB_PATH: str = f"db{sep}"
    """The database path"""

    COLORS: ColorModel = field(default_factory=ColorModel)
    """Available colors in Defender"""

    BATCH_SIZE: int = 400
    """The batch size used for privmsg and notice"""

    DEFENDER_CONNEXION_DATETIME: datetime = field(default=datetime.now())
    """First Connexion datetime of the service"""

    DEFENDER_INIT: int = 1
    """Init flag. When Defender is ready, this variable will be set to 0. (default: 1)"""

    DEFENDER_RESTART: int = 0
    """Restart flag. When Defender should restart this variable should be set to 1 (default: 0)"""

    DEFENDER_HEARTBEAT: bool = True
    """Activate the hearbeat pulse (default: True)"""

    DEFENDER_HEARTBEAT_FREQUENCY: int = 2
    """Frequency in seconds between every pulse (default: 30 seconds)"""

    OS_SEP: str = sep
    """The OS Separator. (default: os.sep)"""

    HSID: str = None
    """Host Server ID. The Server ID of the server who is hosting Defender. (Default: None)"""

    SSL_VERSION: str = None
    """If SSL is used. This variable will be filled out by the system. (Default: None)"""

    def __post_init__(self):
        # Initialiser SERVICE_ID après la création de l'objet
        self.SERVICE_ID: str = f"{self.SERVEUR_ID}AAAAAB"
        """The service ID which is SERVEUR_ID and AAAAAB"""

        self.SERVEUR_CHARSET: list = ["utf-8", "iso-8859-1"]
        """0: utf-8 | 1: iso-8859-1"""

@dataclass
class MCommand(MainModel):
    module_name: str = None
    command_name: str = None
    description: str = None
    command_level: int = 0

@dataclass
class MModule(MainModel):
    module_name: str = None
    class_name: str = None
    class_instance: Optional[Any] = None

@dataclass
class MSModule:
    """Server Modules model"""
    name: str = None
    version: str = None
    type: str = None

@dataclass
class MSasl(MainModel):
    """Sasl model"""

    remote_ip: Optional[str] = None
    mechanisme: Optional[str] = None
    message_type: Optional[str] = None
    client_uid: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    fingerprint: Optional[str] = None
    language: str = "EN"
    auth_success: bool = False
    level: int = 0