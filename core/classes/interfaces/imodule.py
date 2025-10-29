from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass

from mods.clone.schemas import ModConfModel

if TYPE_CHECKING:
    from core.irc import Irc

class IModule(ABC):

    @abstractmethod
    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """

    def __init__(self, uplink: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = uplink

        # Add Protocol to the module (Mandatory)
        self.Protocol = uplink.Protocol

        # Add Global Configuration to the module (Mandatory)
        self.Config = uplink.Config

        # Add Base object to the module (Mandatory)
        self.Base = uplink.Base

        # Add Main Utils (Mandatory)
        self.MainUtils = uplink.Utils

        # Add logs object to the module (Mandatory)
        self.Logs = uplink.Loader.Logs

        # Add User object to the module (Mandatory)
        self.User = uplink.User

        # Add Channel object to the module (Mandatory)
        self.Channel = uplink.Channel

        # Add Reputation object to the module (Optional)
        self.Reputation = uplink.Reputation

        self.ModConfig = ModConfModel()

        self.load_module_configuration()
        """Load module configuration"""

        self.create_tables()
        """Create custom module tables"""

        # Sync the configuration with core configuration (Mandatory)
        uplink.Base.db_sync_core_config(self.module_name, self.ModConfig)

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def update_configuration(self, param_key: str, param_value: str) -> None:
        """Update the local and core configuration

        Args:
            param_key (str): The parameter key
            param_value (str): The parameter value
        """
        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    @abstractmethod
    def create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """

    @abstractmethod
    def load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Build the default configuration model (Mandatory)
            self.ModConfig = self.ModConfModel(jsonrpc=0)

            # Sync the configuration with core configuration (Mandatory)
            self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    @abstractmethod
    def unload(self) -> None:
        """This method is executed when the module is unloaded or reloaded.
        """

    @abstractmethod
    def cmd(self, data: list) -> None:
        """When recieving server messages.

        Args:
            data (list): The recieved message
        """

    @abstractmethod
    def hcmds(self, user: str, channel: Optional[str], cmd: list, fullcmd: list = []) -> None:
        """These are the commands recieved from a client

        Args:
            user (str): The client
            channel (str|None): The channel if available
            cmd (list): The user command sent
            fullcmd (list, optional): The full server message. Defaults to [].
        """