from typing import TYPE_CHECKING
from dataclasses import dataclass, fields

if TYPE_CHECKING:
    from core.irc import Irc

class Test():

    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """
        param_exemple1: str
        param_exemple2: int

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

        # Add Channel object to the module (Mandatory)
        self.Channel = ircInstance.Channel

        # Add Reputation object to the module (Optional)
        self.Reputation = ircInstance.Reputation

        # Create module commands (Mandatory)
        self.Irc.build_command(0, self.module_name, 'test-command', 'Execute a test command')
        self.Irc.build_command(1, self.module_name, 'test_level_1', 'Execute a level 1 test command')
        self.Irc.build_command(2, self.module_name, 'test_level_2', 'Execute a level 2 test command')
        self.Irc.build_command(3, self.module_name, 'test_level_3', 'Execute a level 3 test command')


        # Init the module
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Create you own tables (Mandatory)
        self.__create_tables()

        # Load module configuration and sync with core one (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

        return None

    def __create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """

        table_logs = '''CREATE TABLE IF NOT EXISTS test_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            )
        '''

        self.Base.db_execute_query(table_logs)
        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Build the default configuration model (Mandatory)
            self.ModConfig = self.ModConfModel(param_exemple1='param value 1', param_exemple2=1)

            # Sync the configuration with core configuration (Mandatory)
            self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def __update_configuration(self, param_key: str, param_value: str):
        """Update the local and core configuration

        Args:
            param_key (str): The parameter key
            param_value (str): The parameter value
        """
        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    def unload(self) -> None:

        return None

    def cmd(self, data:list) -> None:
        try:
            cmd = list(data).copy()

            return None
        except KeyError as ke:
            self.Logs.error(f"Key Error: {ke}")
        except IndexError as ie:
            self.Logs.error(f"{ie} / {cmd} / length {str(len(cmd))}")
        except Exception as err:
            self.Logs.error(f"General Error: {err}")

    def hcmds(self, user:str, channel: any, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        dnickname = self.Config.SERVICE_NICKNAME
        fromuser = user
        fromchannel = str(channel) if not channel is None else None

        match command:

            case 'test-command':
                try:

                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="This is a notice to the sender ...")
                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"This is private message to the sender ...", nick_to=fromuser)

                    if not fromchannel is None:
                        self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"This is private message to the sender ...", channel=fromchannel)

                    # How to update your module configuration
                    self.__update_configuration('param_exemple2', 7)

                    # Log if you want the result
                    self.Logs.debug(f"Test logs ready")

                except Exception as err:
                    self.Logs.error(f"Unknown Error: {err}")