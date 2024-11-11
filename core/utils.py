from typing import Literal, Union
from datetime import datetime
from time import time
from random import choice
from hashlib import md5, sha3_512

def convert_to_int(value: any) -> Union[int, None]:
    """Convert a value to int

    Args:
        value (any): Value to convert to int if possible

    Returns:
        Union[int, None]: Return the int value or None if not possible
    """
    try:
        value_to_int = int(value)
        return value_to_int
    except ValueError:
        return None
    except Exception:
        return None

def get_unixtime() -> int:
    """Cette fonction retourne un UNIXTIME de type 12365456

    Returns:
        int: Current time in seconds since the Epoch (int)
    """
    return int(time())

def get_datetime() -> str:
    """Retourne une date au format string (24-12-2023 20:50:59)

    Returns:
        str: Current datetime in this format %d-%m-%Y %H:%M:%S
    """
    currentdate = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    return currentdate

def generate_random_string(lenght: int) -> str:
    """Retourn une chaîne aléatoire en fonction de la longueur spécifiée.
    
    Returns:
        str: The random string 
    """
    caracteres = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    randomize = ''.join(choice(caracteres) for _ in range(lenght))

    return randomize

def hash(password: str, algorithm: Literal["md5, sha3_512"] = 'md5') -> str:
    """Retourne un mot de passe chiffré en fonction de l'algorithme utilisé

    Args:
        password (str): Le password en clair
        algorithm (str): L'algorithm a utilisé

    Returns:
        str: Le password haché
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
