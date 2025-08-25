from typing import TYPE_CHECKING, Optional, Any
import mods.clone.utils as utils
import mods.clone.threads as thds
import mods.clone.schemas as schemas
from mods.clone.clone_manager import CloneManager

if TYPE_CHECKING:
    from core.irc import Irc
    from faker import Faker

class Clone:

    def __init__(self, irc_instance: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = irc_instance

        # Add Irc Protocol Object to the module (Mandatory)
        self.Protocol = irc_instance.Protocol

        # Add Global Configuration to the module (Mandatory)
        self.Config = irc_instance.Config

        # Add Base object to the module (Mandatory)
        self.Base = irc_instance.Base

        # Add logs object to the module (Mandatory)
        self.Logs = irc_instance.Loader.Logs

        # Add User object to the module (Mandatory)
        self.User = irc_instance.User

        # Add Channel object to the module (Mandatory)
        self.Channel = irc_instance.Channel
        
        # Add global definitions
        self.Definition = irc_instance.Loader.Definition

        # The Global Settings
        self.Settings = irc_instance.Loader.Settings

        self.Schemas = schemas

        self.Utils = utils

        self.Threads = thds

        self.Faker: Optional['Faker'] = self.Utils.create_faker_object('en_GB')

        self.Clone = CloneManager(self)

        metadata = self.Settings.get_cache('UID_CLONE_DB')

        if metadata is not None:
            self.Clone.UID_CLONE_DB = metadata
            self.Logs.debug(f"Cache Size = {self.Settings.get_cache_size()}")

        # Créer les nouvelles commandes du module
        self.Irc.build_command(1, self.module_name, 'clone', 'Connect, join, part, kill and say clones')

        # Init the module (Mandatory)
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Créer les tables necessaire a votre module (ce n'es pas obligatoire)
        self.__create_tables()

        self.stop = False

        # Load module configuration (Mandatory)
        self.__load_module_configuration()

        self.Channel.db_query_channel(action='add', module_name=self.module_name, channel_name=self.Config.CLONE_CHANNEL)
        self.Protocol.send_join_chan(self.Config.SERVICE_NICKNAME, self.Config.CLONE_CHANNEL)

        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} SAMODE {self.Config.CLONE_CHANNEL} +o {self.Config.SERVICE_NICKNAME}")
        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} +nts")
        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} +k {self.Config.CLONE_CHANNEL_PASSWORD}")

    def __create_tables(self) -> None:
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

        # self.Base.db_execute_query(table_channel)

        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Variable qui va contenir les options de configuration du module Defender
            self.ModConfig = self.Schemas.ModConfModel()

            # Sync the configuration with core configuration (Mandatory)
            # self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def unload(self) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """
        # Store Clones DB into the global Settings to retrieve it after the reload.
        self.Settings.set_cache('UID_CLONE_DB', self.Clone.UID_CLONE_DB)

        self.Channel.db_query_channel(action='del', module_name=self.module_name, channel_name=self.Config.CLONE_CHANNEL)
        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} -nts")
        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} -k {self.Config.CLONE_CHANNEL_PASSWORD}")
        self.Protocol.send_part_chan(self.Config.SERVICE_NICKNAME, self.Config.CLONE_CHANNEL)

        self.Irc.Commands.drop_command_by_module(self.module_name)

        return None

    def cmd(self, data:list) -> None:
        try:
            if not data or len(data) < 2:
                return None

            cmd = data.copy() if isinstance(data, list) else list(data).copy()
            index, command = self.Irc.Protocol.get_ircd_protocol_poisition(cmd)
            if index == -1:
                return None

            match command:

                case 'PRIVMSG':
                    return self.Utils.handle_on_privmsg(self, cmd)

                case 'QUIT':
                    return None

                case _:
                    return None

        except Exception as err:
            self.Logs.error(f'General Error: {err}', exc_info=True)
            return None

    def hcmds(self, user: str, channel: Any, cmd: list, fullcmd: list = []) -> None:

        try:

            if len(cmd) < 1:
                return

            command = str(cmd[0]).lower()
            fromuser = user
            dnickname = self.Config.SERVICE_NICKNAME

            match command:

                case 'clone':

                    if len(cmd) == 1:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone connect NUMBER GROUP_NAME INTERVAL")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill [all | group_name | nickname]")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join [all | group_name | nickname] #channel")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part [all | group_name | nickname] #channel")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone list [group name]")
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

                                self.Base.create_thread(
                                    func=self.Threads.thread_connect_clones,
                                    func_args=(self, number_of_clones, group, False, connection_interval)
                                )

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone connect [number of clone you want to connect] [Group]")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Exemple /msg {dnickname} clone connect 6 Ambiance")

                        case 'kill':
                            try:
                                # clone kill [ALL | group name | nickname]
                                self.stop = True
                                option = str(cmd[2])

                                if option.lower() == 'all':
                                    self.Base.create_thread(func=self.Threads.thread_kill_clones, func_args=(self, ))

                                elif self.Clone.group_exists(option):
                                    list_of_clones_in_group = self.Clone.get_clones_from_groupname(option)

                                    if len(list_of_clones_in_group) > 0:
                                        self.Logs.debug(f"[Clone Kill Group] - Killing {len(list_of_clones_in_group)} clones in the group {option}")

                                    for clone in list_of_clones_in_group:
                                        self.Protocol.send_quit(clone.uid, "Now i am leaving irc but i'll come back soon ...", print_log=False)
                                        self.Clone.delete(clone.uid)

                                else:
                                    clone_obj = self.Clone.get_clone(option)
                                    if not clone_obj is None:
                                        self.Protocol.send_quit(clone_obj.uid, 'Goood bye', print_log=False)
                                        self.Clone.delete(clone_obj.uid)

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill all")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill clone_nickname")

                        case 'join':
                            try:
                                # clone join [all | group name | nickname] #channel
                                option = str(cmd[2])
                                clone_channel_to_join = str(cmd[3])

                                if option.lower() == 'all':

                                    for clone in self.Clone.UID_CLONE_DB:
                                        self.Protocol.send_join_chan(uidornickname=clone.uid, channel=clone_channel_to_join, print_log=False)

                                elif self.Clone.group_exists(option):
                                    list_of_clones_in_group = self.Clone.get_clones_from_groupname(option)

                                    if len(list_of_clones_in_group) > 0:
                                        self.Logs.debug(f"[Clone Join Group] - Joining {len(list_of_clones_in_group)} clones from group {option} in the channel {clone_channel_to_join}")

                                    for clone in list_of_clones_in_group:
                                        self.Protocol.send_join_chan(uidornickname=clone.nickname, channel=clone_channel_to_join, print_log=False)

                                else:
                                    if self.Clone.nickname_exists(option):
                                        clone_uid = self.Clone.get_clone(option).uid
                                        self.Protocol.send_join_chan(uidornickname=clone_uid, channel=clone_channel_to_join, print_log=False)

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join all #channel")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join clone_nickname #channel")

                        case 'part':
                            try:
                                # clone part [all |  nickname] #channel
                                option = str(cmd[2])
                                clone_channel_to_part = str(cmd[3])

                                if option.lower() == 'all':

                                    for clone in self.Clone.UID_CLONE_DB:
                                        self.Protocol.send_part_chan(uidornickname=clone.uid, channel=clone_channel_to_part, print_log=False)

                                elif self.Clone.group_exists(option):
                                    list_of_clones_in_group = self.Clone.get_clones_from_groupname(option)

                                    if len(list_of_clones_in_group) > 0:
                                        self.Logs.debug(f"[Clone Part Group] - Part {len(list_of_clones_in_group)} clones from group {option} from the channel {clone_channel_to_part}")

                                    for clone in list_of_clones_in_group:
                                        self.Protocol.send_part_chan(uidornickname=clone.uid, channel=clone_channel_to_part, print_log=False)

                                else:
                                    if self.Clone.nickname_exists(option):
                                        clone_uid = self.Clone.get_uid(option)
                                        if not clone_uid is None:
                                            self.Protocol.send_part_chan(uidornickname=clone_uid, channel=clone_channel_to_part, print_log=False)

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part all #channel")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part clone_nickname #channel")

                        case 'list':
                            try:
                                # Syntax. /msg defender clone list <group_name>
                                header = f"  {'Nickname':<12}| {'Real name':<25}| {'Group name':<15}| {'Connected':<35}"
                                line = "-"*67
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=header)
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  {line}")
                                group_name = cmd[2] if len(cmd) > 2 else None

                                if group_name is None:
                                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  Number of connected clones: {len(self.Clone.UID_CLONE_DB)}")
                                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  {line}")
                                    for clone_name in self.Clone.UID_CLONE_DB:
                                        self.Protocol.send_notice(
                                            nick_from=dnickname, 
                                            nick_to=fromuser, 
                                            msg=f"  {clone_name.nickname:<12}| {clone_name.realname:<25}| {clone_name.group:<15}| {clone_name.connected:<35}")
                                else:
                                    if not self.Clone.group_exists(group_name):
                                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="This Group name doesn't exist!")
                                        return None
                                    clones = self.Clone.get_clones_from_groupname(group_name)
                                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  Number of connected clones: {len(clones)}")
                                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"  {line}")
                                    for clone in clones:
                                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, 
                                                                msg=f"  {clone.nickname:<12}| {clone.realname:<25}| {clone.group:<15}| {clone.connected:<35}")
                            except Exception as err:
                                self.Logs.error(f'{err}')

                        case 'say':
                            try:
                                # clone say clone_nickname #channel message
                                clone_name = str(cmd[2])
                                clone_channel = str(cmd[3]) if self.Channel.is_valid_channel(str(cmd[3])) else None

                                final_message = ' '.join(cmd[4:])

                                if clone_channel is None or not self.Clone.nickname_exists(clone_name):
                                    self.Protocol.send_notice(
                                        nick_from=dnickname,
                                        nick_to=fromuser,
                                        msg=f"/msg {dnickname} clone say [clone_nickname] #channel message"
                                    )
                                    return None

                                if self.Clone.nickname_exists(clone_name):
                                    self.Protocol.send_priv_msg(nick_from=clone_name, msg=final_message, channel=clone_channel)

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(
                                        nick_from=dnickname,
                                        nick_to=fromuser,
                                        msg=f"/msg {dnickname} clone say [clone_nickname] #channel message"
                                    )

                        case _:
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone connect NUMBER GROUP_NAME INTERVAL")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill [all | group name | nickname]")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join [all | group name | nickname] #channel")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part [all | group name | nickname] #channel")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone list [group name]")

        except IndexError as ie:
            self.Logs.error(f'Index Error: {ie}')
        except Exception as err:
            self.Logs.error(f'General Error: {err}')
