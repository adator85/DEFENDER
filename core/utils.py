from pathlib import Path
from typing import Literal, Optional, Any
from datetime import datetime
from time import time
from random import choice
from hashlib import md5, sha3_512

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