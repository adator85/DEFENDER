from typing import TYPE_CHECKING, Optional
from core.definition import MCommand

if TYPE_CHECKING:
    from core.loader import Loader

class Command:

    DB_COMMANDS: list['MCommand'] = []

    def __init__(self, loader: 'Loader'):
        self.Base = loader.Base

    def build(self, new_command_obj: MCommand) -> bool:

        command = self.get_command(new_command_obj.command_name, new_command_obj.module_name)
        if command is None:
            self.DB_COMMANDS.append(new_command_obj)
            return True
        
        # Update command if it exist
        # Removing the object
        if self.drop_command(command.command_name, command.module_name):
            # Add the new object
            self.DB_COMMANDS.append(new_command_obj)
            return True
        
        return False
    
    def get_command(self, command_name: str, module_name: str) -> Optional[MCommand]:

        for command in self.DB_COMMANDS:
            if command.command_name.lower() == command_name and command.module_name == module_name:
                return command

        return None
    
    def drop_command(self, command_name: str, module_name: str) -> bool:

        cmd = self.get_command(command_name, module_name)
        if cmd is not None:
            self.DB_COMMANDS.remove(cmd)
            return True
        
        return False

    def get_ordered_commands(self) -> list[MCommand]:
        return sorted(self.DB_COMMANDS, key=lambda c: (c.command_level, c.module_name))
    
    def get_commands_by_level(self, level: int = 0) -> Optional[list[MCommand]]:

        cmd_list = self.get_ordered_commands()
        new_list: list[MCommand] = []

        for cmd in cmd_list:
            if cmd.command_level <= level:
                new_list.append(cmd)
        
        return new_list