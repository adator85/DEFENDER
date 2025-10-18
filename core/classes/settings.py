"""This class should never be reloaded.
"""
from logging import Logger
from threading import Timer, Thread, RLock
from socket import socket
from typing import Any, Optional, TYPE_CHECKING
from core.definition import MSModule, MAdmin

if TYPE_CHECKING:
    from core.classes.user import User

class Settings:
    """This Class will never be reloaded. 
    Means that the variables are available during 
    the whole life of the app
    """

    RUNNING_TIMERS: list[Timer]                 = []
    RUNNING_THREADS: list[Thread]               = []
    RUNNING_SOCKETS: list[socket]               = []
    PERIODIC_FUNC: dict[str, Any]               = {}
    LOCK: RLock                                 = RLock()

    CONSOLE: bool                               = False

    MAIN_SERVER_HOSTNAME: str                   = None
    MAIN_SERVER_ID: str                         = None
    PROTOCTL_PREFIX_MODES_SIGNES : dict[str, str] = {}
    PROTOCTL_PREFIX_SIGNES_MODES : dict[str, str] = {}
    PROTOCTL_USER_MODES: list[str]              = []
    PROTOCTL_CHANNEL_MODES: list[str]           = []
    PROTOCTL_PREFIX: list[str]                  = []

    SMOD_MODULES: list[MSModule]                = []
    """List contains all Server modules"""

    __CACHE: dict[str, Any]                     = {}
    """Use set_cache or get_cache instead"""

    __TRANSLATION: dict[str, list[list[str]]]   = dict()
    """Translation Varibale"""

    __LANG: str                                 = "EN"

    __INSTANCE_OF_USER_UTILS: Optional['User']  = None
    """Instance of the User Utils class"""

    __CURRENT_ADMIN: Optional['MAdmin']         = None
    """The Current Admin Object Model"""

    __LOGGER: Optional[Logger]                  = None
    """Instance of the logger"""

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
    
    def get_cache(self, key) -> Optional[Any]:
        """It returns the value associated to the key and finally it removes the entry"""
        if self.__CACHE.get(key, None) is not None:
            return self.__CACHE.pop(key)

        return None

    def get_cache_size(self) -> int:
        return len(self.__CACHE)

    def clear_cache(self) -> None:
        self.__CACHE.clear()
    
    def show_cache(self) -> dict[str, Any]:
        return self.__CACHE.copy()
    
    @property
    def global_translation(self) -> dict[str, list[list[str]]]:
        """Get/set global translation variable"""
        return self.__TRANSLATION

    @global_translation.setter
    def global_translation(self, translation_var: dict) -> None:
        self.__TRANSLATION = translation_var

    @property
    def global_lang(self) -> str:
        """Global default language."""
        return self.__LANG
    
    @global_lang.setter
    def global_lang(self, lang: str) -> None:
        self.__LANG = lang

    @property
    def global_user(self) -> 'User':
        return self.__INSTANCE_OF_USER_UTILS

    @global_user.setter
    def global_user(self, user_utils_instance: 'User') -> None:
        self.__INSTANCE_OF_USER_UTILS = user_utils_instance

    @property
    def current_admin(self) -> MAdmin:
        """Current admin data model."""
        return self.__CURRENT_ADMIN

    @current_admin.setter
    def current_admin(self, current_admin: MAdmin) -> None:
        self.__CURRENT_ADMIN = current_admin

    @property
    def global_logger(self) -> Logger:
        """Global logger Instance"""
        return self.__LOGGER

    @global_logger.setter
    def global_logger(self, logger: Logger) -> None:
        self.__LOGGER = logger

global_settings = Settings()