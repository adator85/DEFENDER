from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.loader import Loader

class RPCCommand:
    def __init__(self, loader: 'Loader'):
        self._Loader = loader
        self._Command = loader.Commands
    
    def command_list(self, **kwargs) -> list[dict]:
        return [command.to_dict() for command in self._Command.DB_COMMANDS]
    
    def command_get_by_module(self, **kwargs) -> list[dict]:
        module_name = kwargs.get('module_name', None)
        if module_name is None:
            return []

        return [command.to_dict() for command in self._Command.DB_COMMANDS if command.module_name.lower() == module_name.lower()]

    def command_get_by_name(self, **kwargs) -> dict:
        command_name: str = kwargs.get('command_name', '')
        if not command_name:
            return dict()

        for command in self._Command.DB_COMMANDS:
            if command.command_name.lower() == command_name.lower():
                return command.to_dict()
        return dict()