from urllib import request
import requests
from dataclasses import dataclass
from datetime import datetime
from typing import Union, TYPE_CHECKING
from core.classes import user
import core.definition as df

if TYPE_CHECKING:
    from core.irc import Irc


class Weather():

    @dataclass
    class ModConfModel:
        active: bool = False

    def __init__(self, ircInstance: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = ircInstance

        # Add Loader Object to the module (Mandatory)
        self.Loader = ircInstance.Loader

        # Add server protocol Object to the module (Mandatory)
        self.Protocol = ircInstance.Protocol

        # Add Global Configuration to the module (Mandatory)
        self.Config = ircInstance.Config

        # Add Base object to the module (Mandatory)
        self.Base = ircInstance.Base

        # Add logs object to the module (Mandatory)
        self.Logs = ircInstance.Base.logs

        # Add User object to the module (Mandatory)
        self.User = ircInstance.User

        # Add Client object to the module (Mandatory)
        self.Client = ircInstance.Client

        # Add Channel object to the module (Mandatory)
        self.Channel = ircInstance.Channel

        # Add Reputation object to the module (Optional)
        self.Reputation = ircInstance.Reputation

        # Create module commands (Mandatory)
        self.Irc.build_command(0, self.module_name, 'meteo', 'Get the meteo of a current city')

        # Init the module (Mandatory)
        self.__init_module()

        # Log the module
        self.Logs.debug(f'-- Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Create you own tables if needed (Mandatory)
        self.__create_tables()

        # Load module configuration (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

        self.from_user = None
        self.from_channel = None

        return None

    def __create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """

        # table_autoop = '''CREATE TABLE IF NOT EXISTS defender_autoop (
        #     id INTEGER PRIMARY KEY AUTOINCREMENT,
        #     datetime TEXT,
        #     nickname TEXT,
        #     channel TEXT
        #     )
        # '''

        # self.Base.db_execute_query(table_autoop)
        # self.Base.db_execute_query(table_config)
        # self.Base.db_execute_query(table_trusted)
        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Variable qui va contenir les options de configuration du module Defender
            self.ModConfig = self.ModConfModel(active=True)

            # Sync the configuration with core configuration (Mandatory)
            self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def __update_configuration(self, param_key: str, param_value: str):

        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    def get_geo_information(self, city: str) -> tuple[str, str, float, float]:
        """_summary_

        Args:
            city (str): The city you want to get

        Returns:
            tuple[str, str, float, float]: Country Code, City Name Latitude, Longitude
        """
        api_key = 'fd36a3f3715c93f6770a13f5a34ae1e3'
        geo_api_url = "http://api.openweathermap.org/geo/1.0/direct"

        response = requests.get(
                    url=geo_api_url,
                    params={'q': city, 'limit': 1, 'appid': api_key}
                )

        geo_data = response.json()
        if not geo_data:
            return (None, None, 0, 0)

        country_code = geo_data[0]['country']
        city_name = geo_data[0]['name']
        latitude: float = geo_data[0]['lat']
        longitude: float = geo_data[0]['lon']

        return (country_code, city_name, latitude, longitude)

    def get_meteo_information(self, city: str, to_nickname: str) -> None:

        api_key = 'fd36a3f3715c93f6770a13f5a34ae1e3'
        meteo_api_url = "https://api.openweathermap.org/data/2.5/weather" #?lat={lat}&lon={lon}&appid={API key}

        country_code, city_name, latitude, longitude = self.get_geo_information(city=city)

        response_meteo = requests.get(
            url=meteo_api_url,
            params={'lat': latitude, 'lon': longitude, 'appid': api_key, 'units': "metric"}
        )

        meteo_data = response_meteo.json()

        if not meteo_data or city_name is None:
            self.Protocol.send_notice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=to_nickname, 
                                  msg=f"Impossible to find the meteo for [{city}]")
            return None

        temp_cur = meteo_data['main']['temp']
        temp_min = meteo_data['main']['temp_min']
        temp_max = meteo_data['main']['temp_max']

        if self.from_channel is None:
            self.Protocol.send_notice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=to_nickname, 
                                    msg=f"Weather of {city_name} located in {country_code} is:")
            self.Protocol.send_notice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=to_nickname, 
                                    msg=f"Current temperature: {temp_cur} °C")
            self.Protocol.send_notice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=to_nickname, 
                                    msg=f"Minimum temperature: {temp_min} °C")
            self.Protocol.send_notice(nick_from=self.Config.SERVICE_NICKNAME, nick_to=to_nickname, 
                                    msg=f"Maximum temperature: {temp_max} °C")
        else:
            self.Protocol.send_priv_msg(nick_from=self.Config.SERVICE_NICKNAME, channel=self.from_channel, 
                                    msg=f"Weather of {city_name} located in {country_code} is:")
            self.Protocol.send_priv_msg(nick_from=self.Config.SERVICE_NICKNAME, channel=self.from_channel, 
                                    msg=f"Current temperature: {temp_cur} °C")
            self.Protocol.send_priv_msg(nick_from=self.Config.SERVICE_NICKNAME, channel=self.from_channel, 
                                    msg=f"Minimum temperature: {temp_min} °C")
            self.Protocol.send_priv_msg(nick_from=self.Config.SERVICE_NICKNAME, channel=self.from_channel, 
                                    msg=f"Maximum temperature: {temp_max} °C")

        return None

    def unload(self, reloading: bool = False) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """
        if reloading:
            pass
        else:
            self.Protocol.send_quit(self.NICKSERV_UID, f'Stopping {self.module_name} module')

        return None

    def cmd(self, data: list[str]) -> None:
        try:
            service_id = self.Config.SERVICE_ID                 # Defender serveur id
            original_serv_response = list(data).copy()

            parsed_protocol = self.Protocol.parse_server_msg(data.copy())

            match parsed_protocol:

                case 'UID':
                    try:
                        pass

                    except IndexError as ie:
                        self.Logs.error(f'cmd reputation: index error: {ie}')

                case None:
                    self.Logs.debug(f"** TO BE HANDLE {original_serv_response} {__name__}")

        except KeyError as ke:
            self.Logs.error(f"{ke} / {original_serv_response} / length {str(len(original_serv_response))}")
        except IndexError as ie:
            self.Logs.error(f"{ie} / {original_serv_response} / length {str(len(original_serv_response))}")
        except Exception as err:
            self.Logs.error(f"General Error: {err}")

    def hcmds(self, user: str, channel: any, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        fromuser = user
        fromchannel = channel if self.Channel.Is_Channel(channel) else None
        self.from_channel = fromchannel
        self.from_user = fromuser
        dnickname = self.Config.SERVICE_NICKNAME            # Defender nickname
        dchanlog = self.Config.SERVICE_CHANLOG              # Defender chan log
        dumodes = self.Config.SERVICE_UMODES                # Les modes de Defender
        service_id = self.Config.SERVICE_ID                 # Defender serveur id

        match command:

            case 'meteo':
                try:
                    # meteo <CITY>
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.Config.SERVICE_NICKNAME} {command.upper()} METEO <City name>")
                        return None

                    city = str(' '.join(cmd[1:]))
                    to_nickname = fromuser

                    self.Base.create_thread(self.get_meteo_information, (city, to_nickname))

                except TypeError as te:
                    self.Logs.error(f"Type Error -> {te}")
                except ValueError as ve:
                    self.Logs.error(f"Value Error -> {ve}")

