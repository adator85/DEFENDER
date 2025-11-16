from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.loader import Loader

class RPCCommand:
    def __init__(self, loader: 'Loader'):
        self._Loader = loader
        self._Command = loader.Commands
    
    def command_list(self) -> list[dict]:
        return [command.to_dict() for command in self._Command.DB_COMMANDS]
    
    def command_get_by_module(self, module_name: str) -> list[dict]:
        return [command.to_dict() for command in self._Command.DB_COMMANDS if command.module_name.lower() == module_name.lower()]

    def command_get_by_name(self, command_name: str) -> dict:
        for command in self._Command.DB_COMMANDS:
            if command.command_name.lower() == command_name.lower():
                return command.to_dict()
        return {}