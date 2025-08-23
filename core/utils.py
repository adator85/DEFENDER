'''
Main utils library.
'''
import gc
import ssl
import socket
from pathlib import Path
from re import match, sub
import sys
from typing import Literal, Optional, Any, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from time import time
from random import choice
from hashlib import md5, sha3_512

if TYPE_CHECKING:
    from core.irc import Irc

def convert_to_int(value: Any) -> Optional[int]:
    """Convert a value to int

    Args:
        value (Any): Value to convert to int if possible

    Returns:
        int: Return the int value or None if not possible
    """
    try:
        value_to_int = int(value)
        return value_to_int
    except ValueError:
        return None

def get_unixtime() -> int:
    """Cette fonction retourne un UNIXTIME de type 12365456

    Returns:
        int: Current time in seconds since the Epoch (int)
    """
    cet_offset = timezone(timedelta(hours=2))
    now_cet = datetime.now(cet_offset)
    unixtime_cet = int(now_cet.timestamp())
    return int(time())

def get_sdatetime() -> str:
    """Retourne une date au format string (24-12-2023 20:50:59)

    Returns:
        str: Current datetime in this format %d-%m-%Y %H:%M:%S
    """
    currentdate = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    return currentdate

def get_datetime() -> datetime:
    """
    Return the current datetime in a datetime object
    """
    return datetime.now()

def get_ssl_context() -> ssl.SSLContext:
    """Generate the ssl context

    Returns:
        SSLContext: The SSL Context
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def create_socket(uplink: 'Irc') -> None:
    """Create a socket to connect SSL or Normal connection
    """
    try:
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM or socket.SOCK_NONBLOCK)
        connexion_information = (uplink.Config.SERVEUR_IP, uplink.Config.SERVEUR_PORT)

        if uplink.Config.SERVEUR_SSL:
            # Create SSL Context object
            ssl_context = get_ssl_context()
            ssl_connexion = ssl_context.wrap_socket(soc, server_hostname=uplink.Config.SERVEUR_HOSTNAME)
            ssl_connexion.connect(connexion_information)
            uplink.IrcSocket = ssl_connexion
            uplink.Config.SSL_VERSION = uplink.IrcSocket.version()
            uplink.Logs.info(f"-- Connected using SSL : Version = {uplink.Config.SSL_VERSION}")
        else:
            soc.connect(connexion_information)
            uplink.IrcSocket = soc
            uplink.Logs.info("-- Connected in a normal mode!")

        return None

    except (ssl.SSLEOFError, ssl.SSLError) as soe:
        uplink.Logs.critical(f"[SSL ERROR]: {soe}")
    except OSError as oe:
        uplink.Logs.critical(f"[OS Error]: {oe}")
        if 'connection refused' in str(oe).lower():
            sys.exit(oe)
    except AttributeError as ae:
        uplink.Logs.critical(f"AttributeError: {ae}")

def run_python_garbage_collector() -> int:
    """Run Python garbage collector

    Returns:
        int: The number of unreachable objects is returned.
    """
    return gc.collect()

def get_number_gc_objects(your_object_to_count: Optional[Any] = None) -> int:
    """Get The number of objects tracked by the collector (excluding the list returned).

    Returns:
        int: Number of tracked objects by the collector
    """
    if your_object_to_count is None:
        return len(gc.get_objects())
    
    return sum(1 for obj in gc.get_objects() if isinstance(obj, your_object_to_count))

def generate_random_string(lenght: int) -> str:
    """Retourn une chaîne aléatoire en fonction de la longueur spécifiée.
    
    Returns:
        str: The random string 
    """
    caracteres = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    randomize = ''.join(choice(caracteres) for _ in range(lenght))

    return randomize

def hash_password(password: str, algorithm: Literal["md5, sha3_512"] = 'md5') -> str:
    """Return the crypted password following the selected algorithm

    Args:
        password (str): The plain text password
        algorithm (str): The algorithm to use

    Returns:
        str: The crypted password, default md5
    """

    match algorithm:
        case 'md5':
            password = md5(password.encode()).hexdigest()
            return password

        case 'sha3_512':
            password = sha3_512(password.encode()).hexdigest()
            return password

        case _:
            password = md5(password.encode()).hexdigest()
            return password

def get_all_modules() -> list[str]:
    """Get list of all main modules
    using this pattern mod_*.py

    Returns:
        list[str]: List of module names.
    """
    base_path = Path('mods')
    return [file.name.replace('.py', '') for file in base_path.rglob('mod_*.py')]

def clean_uid(uid: str) -> Optional[str]:
    """Clean UID by removing @ / % / + / ~ / * / :

    Args:
        uid (str): The UID to clean

    Returns:
        str: Clean UID without any sign
    """
    if uid is None:
        return None

    pattern = fr'[:|@|%|\+|~|\*]*'
    parsed_UID = sub(pattern, '', uid)

    return parsed_UID

def hide_sensitive_data(srvmsg: list[str]) -> list[str]:
    try:
        srv_msg = srvmsg.copy()
        privmsg_index = srv_msg.index('PRIVMSG')
        auth_index = privmsg_index + 2
        if match(r'^:{1}\W?(auth)$', srv_msg[auth_index]) is None:
            return srv_msg

        for l in range(auth_index + 1, len(srv_msg)):
            srv_msg[l] = '*' * len(srv_msg[l])

        return srv_msg

    except ValueError:
        return srvmsg