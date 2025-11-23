from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Any
from core.classes.interfaces.imodule import IModule
import mods.clone.utils as utils
import mods.clone.threads as thds
import mods.clone.schemas as schemas
from mods.clone.clone_manager import CloneManager

if TYPE_CHECKING:
    from faker import Faker
    from core.loader import Loader

class Clone(IModule):

    @dataclass
    class ModConfModel(schemas.ModConfModel):
        ...

    MOD_HEADER: dict[str, str] = {
        'name':'Clone',
        'version':'1.0.0',
        'description':'Connect thousands of clones to your IRCD, by group. You can use them as security moderation.',
        'author':'Defender Team',
        'core_version':'Defender-6'
    }

    def __init__(self, context: 'Loader') -> None:
        super().__init__(context)
        self._mod_config: Optional[schemas.ModConfModel] = None

    @property
    def mod_config(self) -> ModConfModel:
        return self._mod_config

    async def create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module

        Returns:
            None: Aucun retour n'es attendu
        """

        table_channel = '''CREATE TABLE IF NOT EXISTS clone_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            nickname TEXT,
            username TEXT
            )
        '''

        # await self.ctx.Base.db_execute_query(table_channel)

        return None

    async def load(self) -> None:

        # Variable qui va contenir les options de configuration du module Defender
        self._mod_config: schemas.ModConfModel  = self.ModConfModel()

        # sync the database with local variable (Mandatory)
        await self.sync_db()

        self.stop = False
        self.Schemas = schemas
        self.Utils = utils
        self.Threads = thds
        self.Faker: Optional['Faker'] = self.Utils.create_faker_object('en_GB')
        self.Clone = CloneManager(self)
        metadata = self.ctx.Settings.get_cache('UID_CLONE_DB')

        if metadata is not None:
            self.Clone.UID_CLONE_DB = metadata
            self.ctx.Logs.debug(f"Cache Size = {self.ctx.Settings.get_cache_size()}")

        # Créer les nouvelles commandes du module
        self.ctx.Commands.build_command(1, self.module_name, 'clone', 'Connect, join, part, kill and say clones')

        await self.ctx.Channel.db_query_channel(action='add', module_name=self.module_name, channel_name=self.ctx.Config.CLONE_CHANNEL)
        await self.ctx.Irc.Protocol.send_sjoin(self.ctx.Config.CLONE_CHANNEL)
        await self.ctx.Irc.Protocol.send_set_mode('+o', nickname=self.ctx.Config.SERVICE_NICKNAME, channel_name=self.ctx.Config.CLONE_CHANNEL)
        await self.ctx.Irc.Protocol.send_set_mode('+nts', channel_name=self.ctx.Config.CLONE_CHANNEL)
        await self.ctx.Irc.Protocol.send_set_mode('+k', channel_name=self.ctx.Config.CLONE_CHANNEL, params=self.ctx.Config.CLONE_CHANNEL_PASSWORD)

    async def unload(self) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """
        # Store Clones DB into the global Settings to retrieve it after the reload.
        self.ctx.Settings.set_cache('UID_CLONE_DB', self.Clone.UID_CLONE_DB)

        await self.ctx.Channel.db_query_channel(action='del', module_name=self.module_name, channel_name=self.ctx.Config.CLONE_CHANNEL)
        await self.ctx.Irc.Protocol.send_set_mode('-nts', channel_name=self.ctx.Config.CLONE_CHANNEL)
        await self.ctx.Irc.Protocol.send_set_mode('-k', channel_name=self.ctx.Config.CLONE_CHANNEL)
        await self.ctx.Irc.Protocol.send_part_chan(self.ctx.Config.SERVICE_NICKNAME, self.ctx.Config.CLONE_CHANNEL)

        self.ctx.Commands.drop_command_by_module(self.module_name)

        return None

    async def cmd(self, data:list) -> None:
        try:
            if not data or len(data) < 2:
                return None

            cmd = data.copy() if isinstance(data, list) else list(data).copy()
            index, command = self.ctx.Irc.Protocol.get_ircd_protocol_poisition(cmd)
            if index == -1:
                return None

            match command:

                case 'PRIVMSG':
                    await self.Utils.handle_on_privmsg(self, cmd)
                    return None

                case 'QUIT':
                    return None

                case _:
                    return None

        except Exception as err:
            self.ctx.Logs.error(f'General Error: {err}', exc_info=True)
            return None

    async def hcmds(self, user: str, channel: Any, cmd: list, fullcmd: list = []) -> None:

        try:

            if len(cmd) < 1:
                return

            command = str(cmd[0]).lower()
            fromuser = user
            dnickname = self.ctx.Config.SERVICE_NICKNAME

            match command:

                case 'clone':

                    if len(cmd) < 2:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone connect NUMBER GROUP_NAME INTERVAL")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill [all | group_name | nickname]")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join [all | group_name | nickname] #channel")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part [all | group_name | nickname] #channel")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone list [group name]")
                        return None

                    option = str(cmd[1]).lower()

                    match option:

                        case 'connect':
                            try:
                                # clone connect 5 GroupName 3
                                self.stop = False
                                number_of_clones = int(cmd[2])
                                group = str(cmd[3]).lower()
                                connection_interval = int(cmd[4]) if len(cmd) == 5 else 0.2

                                self.ctx.Base.create_asynctask(
                                    func=self.Threads.coro_connect_clones(self, number_of_clones, group, False, connection_interval)
                                )

                            except IndexError:
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone connect [number of clone you want to connect] [Group] [freq]")
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Exemple /msg {dnickname} clone connect 6 Ambiance")

                        case 'kill':
                            try:
                                # clone kill [ALL | group name | nickname]
                                self.stop = True
                                option = str(cmd[2])

                                if option.lower() == 'all':
                                    self.ctx.Base.create_asynctask(func=self.Threads.thread_kill_clones(self))

                                elif self.Clone.group_exists(option):
                                    list_of_clones_in_group = self.Clone.get_clones_from_groupname(option)

                                    if len(list_of_clones_in_group) > 0:
                                        self.ctx.Logs.debug(f"[Clone Kill Group] - Killing {len(list_of_clones_in_group)} clones in the group {option}")

                                    for clone in list_of_clones_in_group:
                                        await self.ctx.Irc.Protocol.send_quit(clone.uid, "Now i am leaving irc but i'll come back soon ...", print_log=False)
                                        self.Clone.delete(clone.uid)

                                else:
                                    clone_obj = self.Clone.get_clone(option)
                                    if not clone_obj is None:
                                        await self.ctx.Irc.Protocol.send_quit(clone_obj.uid, 'Goood bye', print_log=False)
                                        self.Clone.delete(clone_obj.uid)

                            except IndexError:
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill [all | group name | nickname]")

                        case 'join':
                            try:
                                # clone join [all | group name | nickname] #channel
                                option = str(cmd[2])
                                clone_channel_to_join = str(cmd[3])

                                if option.lower() == 'all':

                                    for clone in self.Clone.UID_CLONE_DB:
                                        await self.ctx.Irc.Protocol.send_join_chan(uidornickname=clone.uid, channel=clone_channel_to_join, print_log=False)

                                elif self.Clone.group_exists(option):
                                    list_of_clones_in_group = self.Clone.get_clones_from_groupname(option)

                                    if len(list_of_clones_in_group) > 0:
                                        self.ctx.Logs.debug(f"[Clone Join Group] - Joining {len(list_of_clones_in_group)} clones from group {option} in the channel {clone_channel_to_join}")

                                    for clone in list_of_clones_in_group:
                                        await self.ctx.Irc.Protocol.send_join_chan(uidornickname=clone.nickname, channel=clone_channel_to_join, print_log=False)

                                else:
                                    if self.Clone.nickname_exists(option):
                                        clone_uid = self.Clone.get_clone(option).uid
                                        await self.ctx.Irc.Protocol.send_join_chan(uidornickname=clone_uid, channel=clone_channel_to_join, print_log=False)

                            except IndexError:
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join [all | group name | nickname] #channel")

                        case 'part':
                            try:
                                # clone part [all |  nickname] #channel
                                option = str(cmd[2])
                                clone_channel_to_part = str(cmd[3])

                                if option.lower() == 'all':

                                    for clone in self.Clone.UID_CLONE_DB:
                                        await self.ctx.Irc.Protocol.send_part_chan(uidornickname=clone.uid, channel=clone_channel_to_part, print_log=False)

                                elif self.Clone.group_exists(option):
                                    list_of_clones_in_group = self.Clone.get_clones_from_groupname(option)

                                    if len(list_of_clones_in_group) > 0:
                                        self.ctx.Logs.debug(f"[Clone Part Group] - Part {len(list_of_clones_in_group)} clones from group {option} from the channel {clone_channel_to_part}")

                                    for clone in list_of_clones_in_group:
                                        await self.ctx.Irc.Protocol.send_part_chan(uidornickname=clone.uid, channel=clone_channel_to_part, print_log=False)

                                else:
                                    if self.Clone.nickname_exists(option):
                                        clone_uid = self.Clone.get_uid(option)
                                        if not clone_uid is None:
                                            await self.ctx.Irc.Protocol.send_part_chan(uidornickname=clone_uid, channel=clone_channel_to_part, print_log=False)

                            except IndexError:
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part [all | group name | nickname] #channel")

                        case 'list':
                            try:
                                # Syntax. /msg defender clone list <group_name>
                                header = f"  {'Nickname':<12}| {'Real name':<25}| {'Group name':<15}| {'Connected':<35}"
                                line = "-"*67
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=header)
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  {line}")
                                group_name = cmd[2] if len(cmd) > 2 else None

                                if group_name is None:
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  Number of connected clones: {len(self.Clone.UID_CLONE_DB)}")
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  {line}")
                                    for clone_name in self.Clone.UID_CLONE_DB:
                                        await self.ctx.Irc.Protocol.send_notice(
                                            nick_from=dnickname, 
                                            nick_to=fromuser, 
                                            msg=f"  {clone_name.nickname:<12}| {clone_name.realname:<25}| {clone_name.group:<15}| {clone_name.connected:<35}")
                                else:
                                    if not self.Clone.group_exists(group_name):
                                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="This Group name doesn't exist!")
                                        return None
                                    clones = self.Clone.get_clones_from_groupname(group_name)
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  Number of connected clones: {len(clones)}")
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  {line}")
                                    for clone in clones:
                                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, 
                                                                msg=f"  {clone.nickname:<12}| {clone.realname:<25}| {clone.group:<15}| {clone.connected:<35}")
                            except IndexError:
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone list [group name]")

                        case 'say':
                            try:
                                # clone say clone_nickname #channel message
                                clone_name = str(cmd[2])
                                clone_channel = str(cmd[3]) if self.ctx.Channel.is_valid_channel(str(cmd[3])) else None

                                final_message = ' '.join(cmd[4:])

                                if clone_channel is None or not self.Clone.nickname_exists(clone_name):
                                    await self.ctx.Irc.Protocol.send_notice(
                                        nick_from=dnickname,
                                        nick_to=fromuser,
                                        msg=f"/msg {dnickname} clone say [clone_nickname] #channel message"
                                    )
                                    return None

                                if self.Clone.nickname_exists(clone_name):
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=clone_name, msg=final_message, channel=clone_channel)

                            except IndexError:
                                await self.ctx.Irc.Protocol.send_notice(
                                        nick_from=dnickname,
                                        nick_to=fromuser,
                                        msg=f"/msg {dnickname} clone say [clone_nickname] #channel message"
                                    )

                        case _:
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone connect NUMBER GROUP_NAME INTERVAL")
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill [all | group name | nickname]")
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join [all | group name | nickname] #channel")
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part [all | group name | nickname] #channel")
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone list [group name]")

        except Exception as err:
            self.ctx.Logs.error(f'General Error: {err}', exc_info=True)
