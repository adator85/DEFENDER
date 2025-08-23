from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass
import mods.command.utils as utils

if TYPE_CHECKING:
    from core.irc import Irc
    from core.definition import MUser
    from sqlalchemy import CursorResult, Row, Sequence

class Command:

    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """
        pass

    def __init__(self, ircInstance: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = ircInstance

        # Add Loader Object to the module (Mandatory)
        self.Loader = ircInstance.Loader

        # Add Protocol object to the module (Mandatory)
        self.Protocol = ircInstance.Protocol

        # Add Global Configuration to the module (Mandatory)
        self.Config = ircInstance.Config

        # Add Base object to the module (Mandatory)
        self.Base = ircInstance.Base

        # Add main Utils to the module
        self.MainUtils = ircInstance.Utils

        # Add logs object to the module (Mandatory)
        self.Logs = ircInstance.Loader.Logs

        # Add User object to the module (Mandatory)
        self.User = ircInstance.User

        # Add Client object to the module (Mandatory)
        self.Client = ircInstance.Client

        # Add Channel object to the module (Mandatory)
        self.Channel = ircInstance.Channel

        # Module Utils
        self.mod_utils = utils

        self.Irc.build_command(1, self.module_name, 'join', 'Join a channel')
        self.Irc.build_command(1, self.module_name, 'assign', 'Assign a user to a role or task')
        self.Irc.build_command(1, self.module_name, 'part', 'Leave a channel')
        self.Irc.build_command(1, self.module_name, 'unassign', 'Remove a user from a role or task')
        self.Irc.build_command(1, self.module_name, 'owner', 'Give channel ownership to a user')
        self.Irc.build_command(1, self.module_name, 'deowner', 'Remove channel ownership from a user')
        self.Irc.build_command(1, self.module_name, 'protect', 'Protect a user from being kicked')
        self.Irc.build_command(1, self.module_name, 'deprotect', 'Remove protection from a user')
        self.Irc.build_command(1, self.module_name, 'op', 'Grant operator privileges to a user')
        self.Irc.build_command(1, self.module_name, 'deop', 'Remove operator privileges from a user')
        self.Irc.build_command(1, self.module_name, 'halfop', 'Grant half-operator privileges to a user')
        self.Irc.build_command(1, self.module_name, 'dehalfop', 'Remove half-operator privileges from a user')
        self.Irc.build_command(1, self.module_name, 'voice', 'Grant voice privileges to a user')
        self.Irc.build_command(1, self.module_name, 'devoice', 'Remove voice privileges from a user')
        self.Irc.build_command(1, self.module_name, 'topic', 'Change the topic of a channel')
        self.Irc.build_command(2, self.module_name, 'opall', 'Grant operator privileges to all users')
        self.Irc.build_command(2, self.module_name, 'deopall', 'Remove operator privileges from all users')
        self.Irc.build_command(2, self.module_name, 'devoiceall', 'Remove voice privileges from all users')
        self.Irc.build_command(2, self.module_name, 'voiceall', 'Grant voice privileges to all users')
        self.Irc.build_command(2, self.module_name, 'ban', 'Ban a user from a channel')
        self.Irc.build_command(2, self.module_name, 'automode', 'Automatically set user modes upon join')
        self.Irc.build_command(2, self.module_name, 'unban', 'Remove a ban from a user')
        self.Irc.build_command(2, self.module_name, 'kick', 'Kick a user from a channel')
        self.Irc.build_command(2, self.module_name, 'kickban', 'Kick and ban a user from a channel')
        self.Irc.build_command(2, self.module_name, 'umode', 'Set user mode')
        self.Irc.build_command(2, self.module_name, 'mode', 'Set channel mode')
        self.Irc.build_command(2, self.module_name, 'get_mode', 'Retrieve current channel mode')
        self.Irc.build_command(2, self.module_name, 'svsjoin', 'Force a user to join a channel')
        self.Irc.build_command(2, self.module_name, 'svspart', 'Force a user to leave a channel')
        self.Irc.build_command(2, self.module_name, 'svsnick', 'Force a user to change their nickname')
        self.Irc.build_command(2, self.module_name, 'wallops', 'Send a message to all operators')
        self.Irc.build_command(2, self.module_name, 'globops', 'Send a global operator message')
        self.Irc.build_command(2, self.module_name, 'gnotice', 'Send a global notice')
        self.Irc.build_command(2, self.module_name, 'whois', 'Get information about a user')
        self.Irc.build_command(2, self.module_name, 'names', 'List users in a channel')
        self.Irc.build_command(2, self.module_name, 'invite', 'Invite a user to a channel')
        self.Irc.build_command(2, self.module_name, 'inviteme', 'Invite yourself to a channel')
        self.Irc.build_command(2, self.module_name, 'sajoin', 'Force yourself into a channel')
        self.Irc.build_command(2, self.module_name, 'sapart', 'Force yourself to leave a channel')
        self.Irc.build_command(2, self.module_name, 'kill', 'Disconnect a user from the server')
        self.Irc.build_command(2, self.module_name, 'gline', 'Ban a user from the entire server')
        self.Irc.build_command(2, self.module_name, 'ungline', 'Remove a global server ban')
        self.Irc.build_command(2, self.module_name, 'kline', 'Ban a user based on their hostname')
        self.Irc.build_command(2, self.module_name, 'unkline', 'Remove a K-line ban')
        self.Irc.build_command(2, self.module_name, 'shun', 'Prevent a user from sending messages')
        self.Irc.build_command(2, self.module_name, 'unshun', 'Remove a shun from a user')
        self.Irc.build_command(2, self.module_name, 'glinelist', 'List all global bans')
        self.Irc.build_command(2, self.module_name, 'shunlist', 'List all shunned users')
        self.Irc.build_command(2, self.module_name, 'klinelist', 'List all K-line bans')
        self.Irc.build_command(3, self.module_name, 'map', 'Show the server network map')

        # Init the module
        self.__init_module()

        # Log the module
        self.Logs.debug(f'-- Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Create you own tables (Mandatory)
        self.__create_tables()

        # Load module configuration and sync with core one (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

        self.user_to_notice: str = ''
        self.show_219: bool = True

        return None

    def __create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

        Returns:
            None: Aucun retour n'es attendu
        """

        table_automode = '''CREATE TABLE IF NOT EXISTS command_automode (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_on TEXT,
            updated_on TEXT,
            nickname TEXT,
            channel TEXT,
            mode TEXT
            )
        '''

        self.Base.db_execute_query(table_automode)
        return None

    def __load_module_configuration(self) -> None:
        """### Load Module Configuration
        """
        try:
            # Build the default configuration model (Mandatory)
            self.ModConfig = self.ModConfModel()

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

    def cmd(self, data: list[str]) -> None:
        try:
            # service_id = self.Config.SERVICE_ID
            dnickname = self.Config.SERVICE_NICKNAME
            # dchanlog = self.Config.SERVICE_CHANLOG
            red = self.Config.COLORS.red
            green = self.Config.COLORS.green
            bold = self.Config.COLORS.bold
            nogc = self.Config.COLORS.nogc
            cmd = list(data).copy()

            if len(cmd) < 2:
                return None

            match cmd[1]:
                # [':irc.deb.biz.st', '403', 'Dev-PyDefender', '#Z', ':No', 'such', 'channel']
                case '403' | '401':
                    try:
                        message = ' '.join(cmd[3:])
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=self.user_to_notice,
                            msg=f"[{red}ERROR MSG{nogc}] {message}"
                        )
                        self.Logs.error(f"{cmd[1]} - {message}")
                    except KeyError as ke:
                        self.Logs.error(ke)
                    except Exception as err:
                        self.Logs.warning(f'Unknown Error: {str(err)}')

                case '006' | '018':
                    try:
                        # [':irc.deb.biz.st', '006', 'Dev-PyDefender', ':`-services.deb.biz.st', '------', '|', 'Users:', '9', '(47.37%)', '[00B]']
                        # [':irc.deb.biz.st', '018', 'Dev-PyDefender', ':4', 'servers', 'and', '19', 'users,', 'average', '4.75', 'users', 'per', 'server']
                        message = ' '.join(cmd[3:])
                        self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=self.user_to_notice,
                            msg=f"[{green}SERVER MSG{nogc}] {message}"
                        )
                    except KeyError as ke:
                        self.Logs.error(ke)
                    except Exception as err:
                        self.Logs.warning(f'Unknown Error: {str(err)}')

                case '219':
                    try:
                        # [':irc.deb.biz.st', '219', 'Dev-PyDefender', 's', ':End', 'of', '/STATS', 'report']
                        if not self.show_219:
                            # If there is a result in 223 then stop here
                            self.show_219 = True
                            return None

                        type_of_stats = str(cmd[3])

                        match type_of_stats:
                            case 's':
                                self.Protocol.send_notice(nick_from=dnickname,nick_to=self.user_to_notice, msg="No shun")
                            case 'G':
                                self.Protocol.send_notice(nick_from=dnickname,nick_to=self.user_to_notice, msg="No gline")
                            case 'k':
                                self.Protocol.send_notice(nick_from=dnickname,nick_to=self.user_to_notice, msg="No kline")

                    except KeyError as ke:
                        self.Logs.error(ke)
                    except Exception as err:
                        self.Logs.warning(f'Unknown Error: {str(err)}')

                case '223':
                    try:
                        # [':irc.deb.biz.st', '223', 'Dev-PyDefender', 'G', '*@162.142.125.217', '67624', '18776', 'irc.deb.biz.st', ':Proxy/Drone', 'detected.', 'Check', 'https://dronebl.org/lookup?ip=162.142.125.217', 'for', 'details.']
                        self.show_219 = False
                        host = str(cmd[4])
                        author = str(cmd[7])
                        reason = ' '.join(cmd[8:])

                        self.Protocol.send_notice(nick_from=dnickname,nick_to=self.user_to_notice,
                                                msg=f"{bold}Author{nogc}: {author} - {bold}Host{nogc}: {host} - {bold}Reason{nogc}: {reason}"
                                                )

                    except KeyError as ke:
                        self.Logs.error(ke)
                    except Exception as err:
                        self.Logs.warning(f'Unknown Error: {str(err)}')

                case _:
                    pass

            if len(cmd) < 3:
                return None

            match cmd[2]:

                case 'SJOIN':
                    # ['@msgid=yldTlbwAGbzCGUcCIHi3ku;time=2024-11-11T17:56:24.297Z', ':001', 'SJOIN', '1728815963', '#znc', ':001LQ0L0C']
                    # Check if the user has an automode
                    try:

                        if len(cmd) < 6:
                            return None

                        user_uid = self.User.clean_uid(cmd[5])
                        userObj: MUser = self.User.get_user(user_uid)
                        channel_name = cmd[4] if self.Channel.is_valid_channel(cmd[4]) else None
                        client_obj = self.Client.get_Client(user_uid)
                        nickname = userObj.nickname if userObj is not None else None

                        if client_obj is not None:
                            nickname = client_obj.account

                        if userObj is None:
                            return None

                        if 'r' not in userObj.umodes and 'o' not in userObj.umodes and not self.Client.is_exist(userObj.uid):
                            return None

                        db_data: dict[str, str] = {"nickname": nickname.lower(), "channel": channel_name.lower()}
                        db_query = self.Base.db_execute_query("SELECT id, mode FROM command_automode WHERE LOWER(nickname) = :nickname AND LOWER(channel) = :channel", db_data)
                        db_result = db_query.fetchone()
                        if db_result:
                            id, mode = db_result
                            self.Protocol.send2socket(f":{self.Config.SERVICE_ID} MODE {channel_name} {mode} {userObj.nickname}")

                    except KeyError as ke:
                        self.Logs.error(f"Key Error: {err}")

        except Exception as err:
            self.Logs.error(f"General Error: {err}")

    def hcmds(self, uidornickname: str, channel_name: Optional[str], cmd: list, fullcmd: list = []):

        command = str(cmd[0]).lower()
        dnickname = self.Config.SERVICE_NICKNAME
        service_id = self.Config.SERVICE_ID
        dchanlog = self.Config.SERVICE_CHANLOG
        self.user_to_notice = uidornickname
        fromuser = uidornickname
        fromchannel = channel_name

        match command:

            case 'automode':
                try:
                    self.mod_utils.set_automode(self, cmd, fromuser)
                except IndexError:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} SET [nickname] [+/-mode] [#channel]")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} LIST")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"[AUTOMODES AVAILABLE] are {' / '.join(self.Loader.Settings.PROTOCTL_PREFIX)}")
                except Exception as err:
                    self.Logs.error(f"General Error: {err}")

            case 'deopall':
                try:
                    self.mod_utils.set_deopall(self, fromchannel)
                except Exception as err:
                    self.Logs.error(f'Unknown Error: {str(err)}')

            case 'devoiceall':
                try:
                    self.mod_utils.set_devoiceall(self, fromchannel)
                except Exception as err:
                    self.Logs.error(f'Unknown Error: {str(err)}')

            case 'voiceall':
                try:
                    self.mod_utils.set_mode_to_all(self, fromchannel, '+', 'v')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'opall':
                try:
                    self.mod_utils.set_mode_to_all(self, fromchannel, '+', 'o')
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'op':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+o')
                except IndexError as e:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} op [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'deop':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-o')
                except IndexError as e:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} deop [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'owner':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+q')

                except IndexError as e:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} owner [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'deowner':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-q')

                except IndexError as e:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} deowner [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'protect':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+a')

                except IndexError as e:
                    self.Logs.warning(f'_hcmd DEOWNER: {str(e)}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'deprotect':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-a')

                except IndexError as e:
                    self.Logs.warning(f'_hcmd DEOWNER: {str(e)}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'halfop':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+h')

                except IndexError as e:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'dehalfop':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-h')

                except IndexError as e:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} dehalfop [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'voice':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+v')
                except IndexError as e:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} voice [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'devoice':
                try:
                    self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-v')
                except IndexError as e:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} devoice [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'ban':
                try:
                    self.mod_utils.set_ban(self, cmd, '+', fromuser)
                except IndexError as e:
                    self.Logs.warning(f'_hcmd BAN: {str(e)}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'unban':
                try:
                    self.mod_utils.set_ban(self, cmd, '-', fromuser)
                except IndexError as e:
                    self.Logs.warning(f'_hcmd UNBAN: {str(e)}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'kick':
                try:
                    self.mod_utils.set_kick(self, cmd, fromuser)
                except IndexError as e:
                    self.Logs.warning(f'_hcmd KICK: {str(e)}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME] [REASON]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'kickban':
                try:
                    self.mod_utils.set_kickban(self, cmd, fromuser)
                except IndexError as e:
                    self.Logs.warning(f'_hcmd KICKBAN: {str(e)}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME] [REASON]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'join' | 'assign':
                try:
                    self.mod_utils.set_assign_channel_to_service(self, cmd, fromuser)
                except IndexError as ie:
                    self.Logs.debug(f'{ie}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'part' | 'unassign':
                try:
                    # Syntax. !part #channel
                    self.mod_utils.set_unassign_channel_to_service(self, cmd, fromuser)
                except IndexError as ie:
                    self.Logs.debug(f'{ie}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON]")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'topic':
                try:
                    if len(cmd) == 1:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} TOPIC #channel THE_TOPIC_MESSAGE")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} TOPIC #channel THE_TOPIC_MESSAGE")
                        return None

                    chan = str(cmd[1])
                    if not self.Channel.is_valid_channel(chan):
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="The channel must start with #")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} TOPIC #channel THE_TOPIC_MESSAGE")
                        return None

                    topic_msg = ' '.join(cmd[2:]).strip()

                    if topic_msg:
                        self.Protocol.send2socket(f':{dnickname} TOPIC {chan} :{topic_msg}')
                    else:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You need to specify the topic")

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'wallops':
                try:
                    if len(cmd) == 1:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} WALLOPS THE_WALLOPS_MESSAGE")
                        return None

                    wallops_msg = ' '.join(cmd[1:]).strip()

                    if wallops_msg:
                        self.Protocol.send2socket(f':{dnickname} WALLOPS {wallops_msg} ({dnickname})')
                    else:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You need to specify the wallops message")

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'globops':
                try:
                    if len(cmd) == 1:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} GLOBOPS THE_GLOBOPS_MESSAGE")
                        return None

                    globops_msg = ' '.join(cmd[1:]).strip()

                    if globops_msg:
                        self.Protocol.send2socket(f':{dnickname} GLOBOPS {globops_msg} ({dnickname})')
                    else:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You need to specify the globops message")

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'gnotice':
                try:
                    if len(cmd) == 1:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} THE_GLOBAL_NOTICE_MESSAGE")
                        return None

                    gnotice_msg = ' '.join(cmd[1:]).strip()

                    if gnotice_msg:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to='$*.*', msg=f"[{self.Config.COLORS.red}GLOBAL NOTICE{self.Config.COLORS.nogc}] {gnotice_msg}")
                    else:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You need to specify the global notice message")

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'whois':
                try:
                    self.user_to_notice = fromuser
                    if len(cmd) == 1:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME")
                        return None

                    nickname = str(cmd[1])

                    if self.User.get_nickname(nickname) is None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Nickname not found !")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME")
                        return None

                    self.Protocol.send2socket(f':{dnickname} WHOIS {nickname}')

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'names':
                try:
                    if len(cmd) == 1:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} #CHANNEL")
                        return None

                    chan = str(cmd[1])

                    if not self.Channel.is_valid_channel(chan):
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="The channel must start with #")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} #channel")
                        return None

                    self.Protocol.send2socket(f':{dnickname} NAMES {chan}')

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'invite':
                try:
                    if len(cmd) < 3:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME #CHANNEL")
                        return None

                    nickname = str(cmd[1])
                    chan = str(cmd[2])

                    if not self.Channel.is_valid_channel(chan):
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="The channel must start with #")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME #CHANNEL")
                        return None

                    if self.User.get_nickname(nickname) is None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Nickname not found !")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME #CHANNEL")
                        return None

                    self.Protocol.send2socket(f':{dnickname} INVITE {nickname} {chan}')

                except KeyError as ke:
                    self.Logs.error(f"KeyError: {ke}")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'inviteme':
                try:
                    if len(cmd) == 0:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()}")
                        return None

                    self.Protocol.send2socket(f':{dnickname} INVITE {fromuser} {self.Config.SERVICE_CHANLOG}')

                except KeyError as ke:
                    self.Logs.error(f"KeyError: {ke}")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'map':
                try:
                    self.user_to_notice = fromuser
                    self.Protocol.send2socket(f':{dnickname} MAP')

                except KeyError as ke:
                    self.Logs.error(f"KeyError: {ke}")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'umode':
                try:
                    # .umode nickname +mode
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [NICKNAME] [+/-]mode")
                        return None

                    nickname = str(cmd[1])
                    umode = str(cmd[2])

                    self.Protocol.send_svsmode(nickname=nickname, user_mode=umode)
                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'mode':
                # .mode #channel +/-mode
                # .mode +/-mode
                try:

                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#CHANNEL] [+/-]mode")
                        return None

                    if fromchannel is None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#CHANNEL] [+/-]mode")
                        return None

                    if len(cmd) == 2:
                        channel_mode = cmd[1]
                        if self.Channel.is_valid_channel(fromchannel):
                            self.Protocol.send2socket(f":{dnickname} MODE {fromchannel} {channel_mode}")
                        else:
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : Channel [{fromchannel}] is not correct should start with #")
                        return None

                    if len(cmd) == 3:
                        provided_channel = cmd[1]
                        channel_mode = cmd[2]
                        self.Protocol.send2socket(f":{service_id} MODE {provided_channel} {channel_mode}")
                        return None

                except IndexError as e:
                    self.Logs.warning(f'_hcmd OP: {str(e)}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#CHANNEL] [+/-]mode")
                except Exception as err:
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'get_mode':
                try:
                    self.Protocol.send2socket(f'MODE {fromchannel}')
                except Exception as err:
                    self.Logs.error(f"General Error {err}")

            case 'svsjoin':
                try:
                    # SVSJOIN <nick> <channel>[,<channel2>..] [key1[,key2[..]]]
                    if len(cmd) < 4:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSJOIN <nick> <channel>[,<channel2>..] [key1[,key2[..]]]")
                        return None

                    nickname = str(cmd[1])
                    channels = str(cmd[2]).split(',')
                    keys = str(cmd[3]).split(',')

                    self.Protocol.send_svsjoin(nickname, channels, keys)
                except IndexError as ke:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSJOIN <nick> <channel>[,<channel2>..] [key1[,key2[..]]]")
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSJOIN <nick> <channel>[,<channel2>..] [key1[,key2[..]]]")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'svspart':
                try:
                    # SVSPART <nick> <channel>[,<channel2>..] [<comment>]
                    if len(cmd) < 4:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSPART <nick> <channel>[,<channel2>..] [<comment>]")
                        return None

                    nickname = str(cmd[1])
                    channels = str(cmd[2]).split(',')
                    reason = ' '.join(cmd[3:])

                    self.Protocol.send_svspart(nickname, channels, reason)
                except IndexError as ke:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSPART <nick> <channel>[,<channel2>..] [<comment>]")
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSPART <nick> <channel>[,<channel2>..] [<comment>]")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'svsnick':
                try:
                    # .svsnick nickname newnickname
                    nickname = str(cmd[1])
                    newnickname = str(cmd[2])
                    unixtime = self.MainUtils.get_unixtime()

                    if self.User.get_nickname(nickname) is None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" This nickname do not exist")
                        return None

                    if len(cmd) != 3:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname newnickname")
                        return None

                    self.Protocol.send2socket(f':{self.Config.SERVEUR_ID} SVSNICK {nickname} {newnickname} {unixtime}')

                except IndexError as ke:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname newnickname")
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname newnickname")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'sajoin':
                try:
                    # .sajoin nickname #channel
                    nickname = str(cmd[1])
                    channel = str(cmd[2])
                    if len(cmd) < 3:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname #channel")
                        return None

                    self.Protocol.send_sajoin(nick_to_sajoin=nickname, channel_name=channel)

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname #channel")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'sapart':
                try:
                    # .sapart nickname #channel
                    if len(cmd) < 3:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname #channel")
                        return None

                    nickname = str(cmd[1])
                    channel = str(cmd[2])

                    self.Protocol.send_sapart(nick_to_sapart=nickname, channel_name=channel)
                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname #channel")
                    self.Logs.error(f'Unknown Error: {str(err)}')

            case 'kill':
                try:
                    # 'kill', 'gline', 'ungline', 'shun', 'unshun'
                    # .kill nickname reason
                    if len(cmd) < 3:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname reason")
                        return None

                    nickname = str(cmd[1])
                    kill_reason = ' '.join(cmd[2:])

                    self.Protocol.send2socket(f":{service_id} KILL {nickname} {kill_reason} ({self.Config.COLORS.red}{dnickname}{self.Config.COLORS.nogc})")
                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSNICK nickname newnickname")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'gline':
                try:
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .gline [nickname] [host] [reason]
                    if len(cmd) < 4:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])
                    set_at_timestamp = self.MainUtils.get_unixtime()
                    expire_time = (60 * 60 * 24) + set_at_timestamp
                    gline_reason = ' '.join(cmd[3:])

                    if nickname == '*' and hostname == '*':
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" You want to close the server ? i would recommand ./unrealircd stop :)")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    self.Protocol.send_gline(nickname=nickname, hostname=hostname, set_by=dnickname, expire_timestamp=expire_time, set_at_timestamp=set_at_timestamp, reason=gline_reason)

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'ungline':
                try:
                    # 'shun', 'unshun'
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .ungline nickname host
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])

                    # self.Protocol.send2socket(f":{self.Config.SERVEUR_ID} TKL - G {nickname} {hostname} {dnickname}")
                    self.Protocol.send_ungline(nickname=nickname, hostname=hostname)

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'kline':
                try:
                    # TKL + k user host set_by expire_timestamp set_at_timestamp :reason
                    # .gline [nickname] [host] [reason]
                    if len(cmd) < 4:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])
                    set_at_timestamp = self.MainUtils.get_unixtime()
                    expire_time = (60 * 60 * 24) + set_at_timestamp
                    gline_reason = ' '.join(cmd[3:])

                    if nickname == '*' and hostname == '*':
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" You want to close the server ? i would recommand ./unrealircd stop :)")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    self.Protocol.send_kline(nickname=nickname, hostname=hostname, set_by=dnickname, expire_timestamp=expire_time, set_at_timestamp=set_at_timestamp, reason=gline_reason)

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'unkline':
                try:
                    # 'shun', 'unshun'
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .ungline nickname host
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])

                    self.Protocol.send_unkline(nickname=nickname, hostname=hostname)

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'shun':
                try:
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .shun [nickname] [host] [reason]

                    if len(cmd) < 4:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])
                    set_at_timestamp = self.MainUtils.get_unixtime()
                    expire_time = (60 * 60 * 24) + set_at_timestamp
                    shun_reason = ' '.join(cmd[3:])

                    if nickname == '*' and hostname == '*':
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" You want to close the server ? i would recommand ./unrealircd stop :)")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    self.Protocol.send2socket(f":{self.Config.SERVEUR_ID} TKL + s {nickname} {hostname} {dnickname} {expire_time} {set_at_timestamp} :{shun_reason}")
                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'unshun':
                try:
                    # 'shun', 'unshun'
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .unshun nickname host
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])

                    self.Protocol.send2socket(f":{self.Config.SERVEUR_ID} TKL - s {nickname} {hostname} {dnickname}")

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'glinelist':
                try:
                    self.user_to_notice = fromuser
                    self.Protocol.send2socket(f":{self.Config.SERVICE_ID} STATS G")

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()}")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'shunlist':
                try:
                    self.user_to_notice = fromuser
                    self.Protocol.send2socket(f":{self.Config.SERVICE_ID} STATS s")

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()}")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case 'klinelist':
                try:
                    self.user_to_notice = fromuser
                    self.Protocol.send2socket(f":{self.Config.SERVICE_ID} STATS k")

                except KeyError as ke:
                    self.Logs.error(ke)
                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()}")
                    self.Logs.warning(f'Unknown Error: {str(err)}')

            case _:
                pass
