"""
Main utils library.
"""
import gc
import ssl
from pathlib import Path
from re import match, sub
import threading
from typing import Literal, Optional, Any, TYPE_CHECKING
from datetime import datetime, timedelta
from time import time, sleep
from random import choice
from hashlib import md5, sha3_512
from core.classes.modules.settings import global_settings
from asyncio import iscoroutinefunction

if TYPE_CHECKING:
    from threading import Event
    from core.loader import Loader

def tr(message: str, *args) -> str:
    """Translation Engine system
    ```python
    example:
        _('Hello my firstname is %s and my lastname is %s', firstname, lastname)
    ```
    Args:
        message (str): The message to translate
        *args (any) : Whatever the variable you want to pass

    Returns:
        str: The translated message
    """
    count_args = len(args) # Count number of args sent
    count_placeholder = message.count('%s') # Count number of placeholder in the message
    is_args_available = True if args else False
    g = global_settings
    try:
        # Access to admin object
        client_language = g.current_admin.language if g.current_admin else g.global_lang

        if count_args != count_placeholder:
            g.global_logger.error(f"Translation: Original message: {message} | Args: {count_args} - Placeholder: {count_placeholder}")
            return message
        
        if g.global_lang is None:
            return message % args if is_args_available else message

        if client_language.lower() == 'en':
            return message % args if is_args_available else message
        
        for trads in g.global_translation[client_language.lower()]:
            if sub(r"\s+", "", message) == sub(r"\s+", "", trads[0]):
                return trads[1] % args if is_args_available else trads[1]

        return message % args if is_args_available else message

    except KeyError as ke:
        g.global_logger.error(f"KeyError: {ke}")
        return message % args if is_args_available else message

    except Exception as err:
        global_settings.global_logger.error(f"General Error: {err} / {message}")
        return message

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
    # cet_offset = timezone(timedelta(hours=2))
    # now_cet = datetime.now(cet_offset)
    # unixtime_cet = int(now_cet.timestamp())
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

def get_defender_uptime(loader: 'Loader') -> str:
    """Savoir depuis quand Defender est connecté

    Returns:
        str: L'écart entre la date du jour et celle de la connexion de Defender
    """
    current_datetime = datetime.now()
    diff_date = current_datetime - loader.Irc.defender_connexion_datetime
    uptime = timedelta(days=diff_date.days, seconds=diff_date.seconds)

    return uptime

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

def heartbeat(event: 'Event', loader: 'Loader', beat: float) -> None:
    """Execute certaines commandes de nettoyage toutes les x secondes
    x étant définit a l'initialisation de cette class (self.beat)

    Args:
        beat (float): Nombre de secondes entre chaque exécution
    """
    loader.Logs.debug(f"Thread started from {threading.current_thread().name}")
    while event.is_set():
        loader.Base.execute_periodic_action()
        sleep(beat)

    loader.Logs.debug("Heartbeat is off!")
    return None

def generate_random_string(lenght: int) -> str:
    """Retourn une chaîne aléatoire en fonction de la longueur spécifiée.
    
    Returns:
        str: The random string 
    """
    caracteres = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    randomize = ''.join(choice(caracteres) for _ in range(lenght))

    return randomize

def hash_password(password: str, algorithm: Literal["md5", "sha3_512"] = 'md5') -> str:
    """Return the crypted password following the selected algorithm

    Args:
        password (str): The plain text password
        algorithm (str): The algorithm to use

    Returns:
        str: The crypted password, default md5
    """

    match algorithm:
        case 'md5':
            hashed_password = md5(password.encode()).hexdigest()
            return hashed_password

        case 'sha3_512':
            hashed_password = sha3_512(password.encode()).hexdigest()
            return hashed_password

        case _:
            hashed_password = md5(password.encode()).hexdigest()
            return hashed_password

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
    parsed_uid = sub(pattern, '', uid)

    return parsed_uid

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

def is_coroutinefunction(func: Any) -> bool:
    """Check if the function is a coroutine or not

    Args:
        func (Any): an callable object

    Returns:
        bool: True if the function is a coroutine
    """
    return iscoroutinefunction(func)