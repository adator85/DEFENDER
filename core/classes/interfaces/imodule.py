from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass

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

        # Add Loader object to the module (Mandatory)
        self.Loader = uplink.Loader

        # Add Protocol to the module (Mandatory)
        self.Protocol = uplink.Protocol

        # Add Global Configuration to the module (Mandatory)
        self.Config = uplink.Config

        # Add Settings to the module (Mandatory)
        self.Settings = uplink.Settings

        # Add Base object to the module (Mandatory)
        self.Base = uplink.Base

        # Add Main Utils (Mandatory)
        self.MainUtils = uplink.Utils

        # Add logs object to the module (Mandatory)
        self.Logs = uplink.Loader.Logs

        # Add User object to the module (Mandatory)
        self.User = uplink.User

        # Add Client object to the module (Mandatory)
        self.Client = uplink.Client

        # Add Admin object to the module (Mandatory)
        self.Admin = uplink.Admin

        # Add Channel object to the module (Mandatory)
        self.Channel = uplink.Channel

        # Add Reputation object to the module (Optional)
        self.Reputation = uplink.Reputation

        # Load the child classes
        self.load()

        # Inspect child classes
        self.inspect_class()

        self.create_tables()

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

    def inspect_class(self):
        if not hasattr(self, 'ModConfig'):
            raise AttributeError("The Module must init ModConfig attribute in the load method!")
        if not hasattr(self, 'MOD_HEADER'):
            raise NotImplementedError(f"You must declare the header of the module in {self.__class__.__name__}!")

    @abstractmethod
    def create_tables(self) -> None:
        """Method that will create the database if it does not exist.
        A single Session for this class will be created, which will be used within this class/module.

        Returns:
            None: No return is expected
        """

    @abstractmethod
    def load(self) -> None:
        """This method is executed when the module is loaded or reloaded.
        """

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
    def hcmds(self, user: str, channel: Optional[str], cmd: list[str], fullcmd: Optional[list[str]] = None) -> None:
        """These are the commands recieved from a client

        Args:
            user (str): The client
            channel (str|None): The channel if available
            cmd (list): The user command sent
            fullcmd (list, optional): The full server message. Defaults to [].
        """