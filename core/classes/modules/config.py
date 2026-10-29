import yaml
from sys import exit
from typing import Any, TYPE_CHECKING
from core.definition import MConfig
from pathlib import Path

if TYPE_CHECKING:
    from core.loader import Loader

class Configuration:

    def __init__(self, loader: 'Loader'):
        
        self.Loader = loader
        self.configuration_model = self.__load_service_configuration_v2()
        loader.ServiceLogging.set_file_handler_level(self._config_model.DEBUG_LEVEL)
        loader.ServiceLogging.set_stdout_handler_level(self._config_model.DEBUG_LEVEL)
        loader.ServiceLogging.update_handler_format(self._config_model.DEBUG_HARD)

    @property
    def configuration_model(self) -> MConfig:
        return self._config_model
    
    @configuration_model.setter
    def configuration_model(self, conf_model: MConfig):
        self._config_model = conf_model

    def __load_config_file(self) -> dict[str, Any] | None:
        try:
            conf_filename = Path('config/configuration.yaml')
            with open(conf_filename, 'r') as conf:
                configuration: dict[str, dict[str, Any]] = yaml.safe_load(conf)
            
            return configuration.get('configuration', None)
        except FileNotFoundError as fe:
            self.Loader.Logs.error('FileNotFound: %s', fe)
            self.Loader.Logs.error('Configuration file not found please create config/configuration.yaml')
            exit("Configuration file not found please create config/configuration.yaml")

    def __load_service_configuration_v2(self) -> MConfig | None:
        try:
            _imported_yaml_file = self.__load_config_file()
            if _imported_yaml_file is None:
                self.Loader.Logs.error('Error While importing configuration file!', exc_info=True)
                raise Exception('Error While importing yaml configuration')

            _imported_yaml_attributes = set(_imported_yaml_file.keys())
            _config_attributes = set(MConfig().get_attributes())

            _keys_to_remove = _imported_yaml_attributes - _config_attributes
            for _key in _keys_to_remove:
                _imported_yaml_file.pop(_key, None)
                self.Loader.Logs.warning('[!] The key %s is not expected, '
                                         'it has been removed from the system ! '
                                         'please remove it from configuration.json file [!]',
                                         _key)

            # Force EN Language if not provided by the configuration!
            if _imported_yaml_file.get('LANG', None) is None:
                _imported_yaml_file['LANG'] = MConfig().LANG or 'EN'

            self.Loader.Logs.debug("[LOADING CONFIGURATION]: Loading configuration with %s parameters!",
                                   len(_imported_yaml_file))

            del (_imported_yaml_attributes,
                 _config_attributes,
                 _keys_to_remove)

            return MConfig(**_imported_yaml_file)

        except TypeError as te:
            self.Loader.Logs.error('TypeError: %s', te)
        except Exception as err:
            self.Loader.Logs.error('General Error: %s', err, exc_info=True)
