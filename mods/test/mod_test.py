import asyncio
from typing import Any, TYPE_CHECKING, Optional
from core.classes.interfaces.imodule import IModule
from dataclasses import dataclass

if TYPE_CHECKING:
    from core.loader import Loader

class Test(IModule):

    @dataclass
    class ModConfModel:
        """The Model containing the module parameters (Mandatory)
        you can leave it without params.
        just use pass | if you leave it empty, in the load() method just init empty object ==> self.ModConfig = ModConfModel()
        """
        param_exemple1: str
        param_exemple2: int

    MOD_HEADER: dict[str, str] = {
        'name':'Test',
        'version':'1.0.0',
        'description':'The test module',
        'author':'Defender Team',
        'core_version':'Defender-6'
    }
    """Module Header (Mandatory)"""

    def __init__(self, uplink: 'Loader'):
        super().__init__(uplink)
        self._mod_config: Optional[Test.ModConfModel] = None

    def create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module

        Returns:
            None: Aucun retour n'es attendu
        """

        table_logs = '''CREATE TABLE IF NOT EXISTS test_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            )
        '''

        # self.ctx.Base.db_execute_query(table_logs)
        return None

    async def load(self) -> None:
        """### Load Module Configuration (Mandatory)
        """

        # Create module commands (Mandatory)
        self.ctx.Irc.build_command(0, self.module_name, 'test-command', 'Execute a test command')
        self.ctx.Irc.build_command(0, self.module_name, 'asyncio', 'Create a new asynchron task!')
        self.ctx.Irc.build_command(1, self.module_name, 'test_level_1', 'Execute a level 1 test command')
        self.ctx.Irc.build_command(2, self.module_name, 'test_level_2', 'Execute a level 2 test command')
        self.ctx.Irc.build_command(3, self.module_name, 'test_level_3', 'Execute a level 3 test command')

        # Build the default configuration model (Mandatory)
        self._mod_config = self.ModConfModel(param_exemple1='str', param_exemple2=1)

        # sync the database with local variable (Mandatory)
        await self.sync_db()

        if self.mod_config.param_exemple2 == 1:
            await self.ctx.Irc.Protocol.send_priv_msg(self.ctx.Config.SERVICE_NICKNAME, "Param activated", self.ctx.Config.SERVICE_CHANLOG)

    @property
    def mod_config(self) -> ModConfModel:
        return self._mod_config

    def unload(self) -> None:
        """### This method is called when you unload, or you reload the module (Mandatory)"""
        self.ctx.Commands.drop_command_by_module(self.module_name)
        return None

    def cmd(self, data: list[str]) -> None:
        """All messages coming from the IRCD server will be handled using this method (Mandatory)

        Args:
            data (list): Messages coming from the IRCD server.
        """
        cmd = list(data).copy()
        try:
            return None
        except Exception as err:
            self.ctx.Logs.error(f"General Error: {err}")

    async def asyncio_func(self) -> None:
        self.ctx.Logs.debug(f"Starting async method in a task: {self.__class__.__name__}")
        await asyncio.sleep(2)
        self.ctx.Logs.debug(f"End of the task: {self.__class__.__name__}")

    async def hcmds(self, user: str, channel: Any, cmd: list, fullcmd: Optional[list] = None) -> None:
        """All messages coming from the user commands (Mandatory)

        Args:
            user (str): The user who send the request.
            channel (Any): The channel from where is coming the message (could be None).
            cmd (list): The messages coming from the IRCD server.
            fullcmd (list, optional): The full messages coming from the IRCD server. Defaults to [].
        """
        u = self.ctx.User.get_user(user)
        c = self.ctx.Channel.get_channel(channel) if self.ctx.Channel.is_valid_channel(channel) else None
        if u is None:
            return None

        command = str(cmd[0]).lower()
        dnickname = self.ctx.Config.SERVICE_NICKNAME

        match command:
            
            case 'asyncio':
                self.ctx.Base.create_asynctask(self.asyncio_func())
                return None

            case 'test-command':
                try:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=u.nickname, msg="This is a notice to the sender ...")
                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"This is private message to the sender ...", nick_to=u.nickname)

                    if c is not None:
                        await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"This is private message to the sender ...", channel=c.name)

                    # How to update your module configuration
                    self.update_configuration('param_exemple2', 7)
                    self.update_configuration('param_exemple1', 'my_value')

                    # Log if you want the result
                    self.ctx.Logs.debug(f"Test logs ready")
                    return None

                except Exception as err:
                    self.ctx.Logs.error(f"Unknown Error: {err}")
                    return None

            case _:
                return None