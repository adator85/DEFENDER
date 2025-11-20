from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Union
from dataclasses import dataclass

if TYPE_CHECKING:
    from core.loader import Loader

class IModule(ABC):

    @abstractmethod
    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """

    def __init__(self, uplink: 'Loader') -> None:

        # import the context
        self.ctx = uplink

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Log the module
        self.ctx.Logs.debug(f'Loading Module {self.module_name} ...')

    async def sync_db(self) -> None:
        # Sync the configuration with core configuration (Mandatory)
        await self.ctx.Base.db_sync_core_config(self.module_name, self.mod_config)
        return None

    async def update_configuration(self, param_key: str, param_value: Union[str, int]) -> None:
        """Update the local and core configuration

        Args:
            param_key (str): The parameter key
            param_value (str): The parameter value
        """
        await self.ctx.Base.db_update_core_config(self.module_name, self.mod_config, param_key, param_value)

    @property
    @abstractmethod
    def mod_config(self) -> ModConfModel:
        """
        The module configuration model
        """

    @abstractmethod
    def create_tables(self) -> None:
        """Method that will create the database if it does not exist.
        A single Session for this class will be created, which will be used within this class/module.

        Returns:
            None: No return is expected
        """

    @abstractmethod
    async def load(self) -> None:
        """This method is executed when the module is loaded or reloaded.
        """

    @abstractmethod
    async def unload(self) -> None:
        """This method is executed when the module is unloaded or reloaded.
        """

    @abstractmethod
    async def cmd(self, data: list) -> None:
        """When recieving server messages.

        Args:
            data (list): The recieved message
        """

    @abstractmethod
    async def hcmds(self, user: str, channel: Optional[str], cmd: list[str], fullcmd: Optional[list[str]] = None) -> None:
        """These are the commands recieved from a client

        Args:
            user (str): The client
            channel (str|None): The channel if available
            cmd (list): The user command sent
            fullcmd (list, optional): The full server message. Defaults to [].
        """