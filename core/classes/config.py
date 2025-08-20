from json import load
from sys import exit
from os import sep
from typing import Union
from core.definition import MConfig
from logging import Logger


class Configuration:

    def __init__(self, logs: Logger) -> None:
        self.Logs = logs
        self.ConfigObject: MConfig = self.__load_service_configuration()
        return None

    def __load_json_service_configuration(self):
        try:
            conf_filename = f'config{sep}configuration.json'
            with open(conf_filename, 'r') as configuration_data:
                configuration:dict[str, Union[str, int, list, dict]] = load(configuration_data)

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

            ConfigObject: MConfig = MConfig(
                **import_config
            )

            return ConfigObject

        except TypeError as te:
            self.Logs.error(te)