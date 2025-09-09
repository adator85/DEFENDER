from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.definition import MIrcdCommand
    from core.loader import Loader

class CommandHandler:
    
    DB_IRCDCOMMS: list['MIrcdCommand'] = []
    DB_SUBSCRIBE: list = []

    def __init__(self, loader: 'Loader'):
        self.__Logs = loader.Logs

    def register(self, ircd_command_model: 'MIrcdCommand') -> None:
        """Register a new command in the Handler

        Args:
            ircd_command_model (MIrcdCommand): The IRCD Command Object
        """
        ircd_command = self.get_registred_ircd_command(ircd_command_model.command_name)
        if ircd_command is None:
            self.__Logs.debug(f'[IRCD COMMAND HANDLER] New IRCD command ({ircd_command_model.command_name}) added to the handler.')
            self.DB_IRCDCOMMS.append(ircd_command_model)
            return None
        else:
            self.__Logs.debug(f'[IRCD COMMAND HANDLER] This IRCD command ({ircd_command.command_name}) already exist in the handler.')
    
    def get_registred_ircd_command(self, command_name: str) -> Optional['MIrcdCommand']:
        """Get the registred IRCD command model

        Returns:
            MIrcdCommand: The IRCD Command object
        """
        com = command_name.upper()
        for ircd_com in self.DB_IRCDCOMMS:
            if com == ircd_com.command_name.upper():
                return ircd_com
        
        return None

    def get_ircd_commands(self) -> list['MIrcdCommand']:
        """Get the list of IRCD Commands

        Returns:
            list[MIrcdCommand]: a list of all registred commands
        """
        return self.DB_IRCDCOMMS.copy()
