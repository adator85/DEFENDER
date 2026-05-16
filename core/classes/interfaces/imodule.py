from abc import ABC, abstractmethod
import asyncio
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
        self.ctx.Logs.debug(f'Loading Module {self.module_name} {id(self)} ...')

        # Is module compliant
        self.__loaded = False

    def __del__(self):
        self.ctx.Logs.info(f"[I-MODULE] Module {self.__class__.__name__} ({id(self)}) has been cleaned-up!")

    async def sync_db(self) -> None:
        # Sync the configuration with core configuration (Mandatory)
        await self.ctx.Base.db_sync_core_config(self.module_name, self.mod_config)
        self.is_loaded = True
        return None

    async def cleanup(self) -> None:
        for nom in dir(self):
            if isinstance(getattr(self, nom), self.ctx.Definition.DTask):
                _dtask = getattr(self, nom)
                # print(f"  • {nom} - {type(getattr(self, nom))}")
                try:
                    await asyncio.wait_for(_dtask.task, timeout=5)
                    self.ctx.DAsyncio.running_iotasks.remove(_dtask)
                    self.ctx.Logs.debug(f"[I-MODULE CLEANUP] The module {self.__class__.__name__} has been cleaned up")
                    # print(f"{task_name} has been removed!")
                except asyncio.exceptions.TimeoutError:
                    print("Error Timeout!")

    async def update_configuration(self, param_key: str, param_value: Union[str, int]) -> None:
        """Update the local and core configuration

        Args:
            param_key (str): The parameter key
            param_value (str): The parameter value
        """
        await self.ctx.Base.db_update_core_config(self.module_name, self.mod_config, param_key, param_value)

    @property
    def is_loaded(self) -> bool:
        return self.__loaded
    
    @is_loaded.setter
    def is_loaded(self, loaded: bool) -> None:
        self.__loaded = loaded

    @property
    @abstractmethod
    def mod_config(self) -> ModConfModel:
        """
        The module configuration model
        """

    @abstractmethod
    async def create_tables(self) -> None:
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
    async def hcmds(self, user: str, channel: Optional[str], cmd: list[str], fullcmd: Optional[list[str]]) -> None:
        """These are the commands recieved from a client

        Args:
            user (str): The client
            channel (str|None): The channel if available
            cmd (list): The user command sent
            fullcmd (list, optional): The full server message. Defaults to [].
        """