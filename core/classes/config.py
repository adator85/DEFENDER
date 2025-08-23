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
        self._config_model: MConfig = self.__load_service_configuration()
        loader.ServiceLogging.set_file_handler_level(self._config_model.DEBUG_LEVEL)
        loader.ServiceLogging.set_stdout_handler_level(self._config_model.DEBUG_LEVEL)
        loader.ServiceLogging.update_handler_format(self._config_model.DEBUG_HARD)
        return None

    def get_config_model(self) -> MConfig:
        return self._config_model

    def __load_json_service_configuration(self) -> Optional[dict[str, Any]]:
        try:
            conf_filename = f'config{sep}configuration.json'
            with open(conf_filename, 'r') as configuration_data:
                configuration: dict[str, Union[str, int, list, dict]] = load(configuration_data)

            return configuration

        except FileNotFoundError as fe:
            self.Logs.error(f'FileNotFound: {fe}')
            self.Logs.error('Configuration file not found please create config/configuration.json')
            exit(0)
        except KeyError as ke:
            self.Logs.error(f'Key Error: {ke}')
            self.Logs.error('The key must be defined in core/configuration.json')

    def __load_service_configuration(self) -> MConfig:
        try:
            import_config = self.__load_json_service_configuration()

            Model_keys = MConfig().to_dict()
            model_key_list: list = []
            json_config_key_list: list = []

            for key in Model_keys:
                model_key_list.append(key)

            for key in import_config:
                json_config_key_list.append(key)

            for json_conf in json_config_key_list:
                if not json_conf in model_key_list:
                    import_config.pop(json_conf, None)
                    self.Logs.warning(f"[!] The key {json_conf} is not expected, it has been removed from the system ! please remove it from configuration.json file [!]")

            self.Logs.debug(f"[LOADING CONFIGURATION]: Loading configuration with {len(import_config)} parameters!")
            return MConfig(**import_config)

        except TypeError as te:
            self.Logs.error(te)