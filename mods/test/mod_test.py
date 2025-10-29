from core.classes.interfaces.imodule import IModule
from dataclasses import dataclass

class Test(IModule):

    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """
        param_exemple1: str
        param_exemple2: int

    def load_module_configuration(self) -> None:
        """### Load Module Configuration
        """

        # Create module commands (Mandatory)
        self.Irc.build_command(0, self.module_name, 'test-command', 'Execute a test command')
        self.Irc.build_command(1, self.module_name, 'test_level_1', 'Execute a level 1 test command')
        self.Irc.build_command(2, self.module_name, 'test_level_2', 'Execute a level 2 test command')
        self.Irc.build_command(3, self.module_name, 'test_level_3', 'Execute a level 3 test command')

        # Build the default configuration model (Mandatory)
        self.ModConfig = self.ModConfModel(param_exemple1='str', param_exemple2=1)

        return None

    def create_tables(self) -> None:
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

        # self.Base.db_execute_query(table_logs)
        return None

    def unload(self) -> None:
        self.Irc.Commands.drop_command_by_module(self.module_name)
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
                    self.update_configuration('param_exemple2', 7)
                    self.update_configuration('param_exemple1', 'my_value')

                    # Log if you want the result
                    self.Logs.debug(f"Test logs ready")

                except Exception as err:
                    self.Logs.error(f"Unknown Error: {err}")