'''This class should never be reloaded.
'''
from threading import Timer, Thread, RLock
from socket import socket
from typing import Any

class Settings:
    """This Class will never be reloaded. 
    Means that the variables are available during 
    the whole life of the app
    """

    RUNNING_TIMERS: list[Timer]         = []
    RUNNING_THREADS: list[Thread]       = []
    RUNNING_SOCKETS: list[socket]       = []
    PERIODIC_FUNC: dict[object]         = {}
    LOCK: RLock                         = RLock()

    CONSOLE: bool                       = False

    PROTOCTL_USER_MODES: list[str]      = []
    PROTOCTL_PREFIX: list[str]          = []

    __CACHE: dict[str, Any]             = {}
    """Use set_cache or get_cache instead"""

    def set_cache(self, key: str, value_to_cache: Any):
        """When you want to store a variable 

        Ex.
        ```python
            set_cache('MY_KEY', {'key1': 'value1', 'key2', 'value2'})
        ```
        Args:
            key (str): The key you want to add.
            value_to_cache (Any): The Value you want to store.
        """
        self.__CACHE[key] = value_to_cache
    
    def get_cache(self, key) -> Any:
        """It returns the value associated to the key and finally it removes the entry"""
        if self.__CACHE.get(key):
            return self.__CACHE.pop(key)

        return None

    def get_cache_size(self) -> int:
        return len(self.__CACHE)
        