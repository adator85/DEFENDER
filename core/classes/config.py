import sys
import yaml
from json import load
from sys import exit
from os import sep
from typing import Any, Optional, Union, TYPE_CHECKING
from core.definition import MConfig

if TYPE_CHECKING:
    from core.loader import Loader

class Configuration:

    def __init__(self, loader: 'Loader') -> None:
        
        self.Loader = loader
        self.Logs = loader.Logs
        self.configuration_model = self.__load_service_configuration()
        loader.ServiceLogging.set_file_handler_level(self._config_model.DEBUG_LEVEL)
        loader.ServiceLogging.set_stdout_handler_level(self._config_model.DEBUG_LEVEL)
        loader.ServiceLogging.update_handler_format(self._config_model.DEBUG_HARD)
        return None

    @property
    def configuration_model(self) -> MConfig:
        return self._config_model
    
    @configuration_model.setter
    def configuration_model(self, conf_model: MConfig):
        self._config_model = conf_model

    def __load_config_file(self) -> Optional[dict[str, Any]]:
        try:
            conf_filename = f'config{sep}configuration.yaml'
            with open(conf_filename, 'r') as conf:
                configuration: dict[str, dict[str, Any]] = yaml.safe_load(conf)
            
            return configuration.get('configuration', None)
        except FileNotFoundError as fe:
            self.Logs.error(f'FileNotFound: {fe}')
            self.Logs.error('Configuration file not found please create config/configuration.yaml')
            exit("Configuration file not found please create config/configuration.yaml")

    def __load_service_configuration(self) -> MConfig:
        try:
            import_config = self.__load_config_file()
            if import_config is None:
                self.Logs.error("Error While importing configuration file!", exc_info=True)
                raise Exception("Error While importing yaml configuration")

            list_key_to_remove: list[str] = [key_to_del for key_to_del in import_config if key_to_del not in MConfig().get_attributes()]
            for key_to_remove in list_key_to_remove:
                import_config.pop(key_to_remove, None)
                self.Logs.warning(f"[!] The key {key_to_remove} is not expected, it has been removed from the system ! please remove it from configuration.json file [!]")

            self.Logs.debug(f"[LOADING CONFIGURATION]: Loading configuration with {len(import_config)} parameters!")
            return MConfig(**import_config)

        except TypeError as te:
            self.Logs.error(te)