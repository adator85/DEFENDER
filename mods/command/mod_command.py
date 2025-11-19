from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass
from core.classes.interfaces.imodule import IModule
import mods.command.utils as utils

if TYPE_CHECKING:
    from core.definition import MUser
    from core.loader import Loader

class Command(IModule):

    @dataclass
    class ModConfModel:
        """The Model containing the module parameters
        """
        pass

    MOD_HEADER: dict[str, str] = {
        'name':'Command',
        'version':'1.0.0',
        'description':'Module contains all IRC commands',
        'author':'Defender Team',
        'core_version':'Defender-6'
    }

    def __init__(self, uplink: 'Loader'):
        super().__init__(uplink)
        self._mod_config: Optional[Command.ModConfModel] = self.ModConfModel()
    
    @property
    def mod_config(self) -> ModConfModel:
        return self._mod_config

    def create_tables(self) -> None:
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

        self.ctx.Base.db_execute_query(table_automode)
        return None

    def load(self) -> None:
        # Module Utils
        self.mod_utils = utils
        self.user_to_notice: str = ''
        self.show_219: bool = True

        # Register new commands into the protocol
        new_cmds = {'403', '401', '006', '018', '219', '223'}
        for c in new_cmds:
            self.ctx.Irc.Protocol.known_protocol.add(c)

        self.ctx.Irc.build_command(2, self.module_name, 'join', 'Join a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'assign', 'Assign a user to a role or task')
        self.ctx.Irc.build_command(2, self.module_name, 'part', 'Leave a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'unassign', 'Remove a user from a role or task')
        self.ctx.Irc.build_command(2, self.module_name, 'owner', 'Give channel ownership to a user')
        self.ctx.Irc.build_command(2, self.module_name, 'deowner', 'Remove channel ownership from a user')
        self.ctx.Irc.build_command(2, self.module_name, 'protect', 'Protect a user from being kicked')
        self.ctx.Irc.build_command(2, self.module_name, 'deprotect', 'Remove protection from a user')
        self.ctx.Irc.build_command(2, self.module_name, 'op', 'Grant operator privileges to a user')
        self.ctx.Irc.build_command(2, self.module_name, 'deop', 'Remove operator privileges from a user')
        self.ctx.Irc.build_command(1, self.module_name, 'halfop', 'Grant half-operator privileges to a user')
        self.ctx.Irc.build_command(1, self.module_name, 'dehalfop', 'Remove half-operator privileges from a user')
        self.ctx.Irc.build_command(1, self.module_name, 'voice', 'Grant voice privileges to a user')
        self.ctx.Irc.build_command(1, self.module_name, 'devoice', 'Remove voice privileges from a user')
        self.ctx.Irc.build_command(1, self.module_name, 'topic', 'Change the topic of a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'opall', 'Grant operator privileges to all users')
        self.ctx.Irc.build_command(2, self.module_name, 'deopall', 'Remove operator privileges from all users')
        self.ctx.Irc.build_command(2, self.module_name, 'devoiceall', 'Remove voice privileges from all users')
        self.ctx.Irc.build_command(2, self.module_name, 'voiceall', 'Grant voice privileges to all users')
        self.ctx.Irc.build_command(2, self.module_name, 'ban', 'Ban a user from a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'automode', 'Automatically set user modes upon join')
        self.ctx.Irc.build_command(2, self.module_name, 'unban', 'Remove a ban from a user')
        self.ctx.Irc.build_command(2, self.module_name, 'kick', 'Kick a user from a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'kickban', 'Kick and ban a user from a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'umode', 'Set user mode')
        self.ctx.Irc.build_command(2, self.module_name, 'mode', 'Set channel mode')
        self.ctx.Irc.build_command(2, self.module_name, 'get_mode', 'Retrieve current channel mode')
        self.ctx.Irc.build_command(2, self.module_name, 'svsjoin', 'Force a user to join a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'svspart', 'Force a user to leave a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'svsnick', 'Force a user to change their nickname')
        self.ctx.Irc.build_command(2, self.module_name, 'wallops', 'Send a message to all operators')
        self.ctx.Irc.build_command(2, self.module_name, 'globops', 'Send a global operator message')
        self.ctx.Irc.build_command(2, self.module_name, 'gnotice', 'Send a global notice')
        self.ctx.Irc.build_command(2, self.module_name, 'whois', 'Get information about a user')
        self.ctx.Irc.build_command(2, self.module_name, 'names', 'List users in a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'invite', 'Invite a user to a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'inviteme', 'Invite yourself to a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'sajoin', 'Force yourself into a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'sapart', 'Force yourself to leave a channel')
        self.ctx.Irc.build_command(2, self.module_name, 'kill', 'Disconnect a user from the server')
        self.ctx.Irc.build_command(2, self.module_name, 'gline', 'Ban a user from the entire server')
        self.ctx.Irc.build_command(2, self.module_name, 'ungline', 'Remove a global server ban')
        self.ctx.Irc.build_command(2, self.module_name, 'kline', 'Ban a user based on their hostname')
        self.ctx.Irc.build_command(2, self.module_name, 'unkline', 'Remove a K-line ban')
        self.ctx.Irc.build_command(2, self.module_name, 'shun', 'Prevent a user from sending messages')
        self.ctx.Irc.build_command(2, self.module_name, 'unshun', 'Remove a shun from a user')
        self.ctx.Irc.build_command(2, self.module_name, 'glinelist', 'List all global bans')
        self.ctx.Irc.build_command(2, self.module_name, 'shunlist', 'List all shunned users')
        self.ctx.Irc.build_command(2, self.module_name, 'klinelist', 'List all K-line bans')
        self.ctx.Irc.build_command(3, self.module_name, 'map', 'Show the server network map')

    def unload(self) -> None:
        self.ctx.Commands.drop_command_by_module(self.module_name)
        return None

    async def cmd(self, data: list[str]) -> None:
        try:
            # service_id = self.ctx.Config.SERVICE_ID
            dnickname = self.ctx.Config.SERVICE_NICKNAME
            # dchanlog = self.ctx.Config.SERVICE_CHANLOG
            red = self.ctx.Config.COLORS.red
            green = self.ctx.Config.COLORS.green
            bold = self.ctx.Config.COLORS.bold
            nogc = self.ctx.Config.COLORS.nogc
            cmd = list(data).copy()

            pos, parsed_cmd = self.ctx.Irc.Protocol.get_ircd_protocol_poisition(cmd=cmd, log=True)

            if pos == -1:
                return None

            match parsed_cmd:
                # [':irc.deb.biz.st', '403', 'Dev-PyDefender', '#Z', ':No', 'such', 'channel']
                case '403' | '401':
                    try:
                        message = ' '.join(cmd[3:])
                        await self.ctx.Irc.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=self.user_to_notice,
                            msg=f"[{red}ERROR MSG{nogc}] {message}"
                        )
                        self.ctx.Logs.error(f"{cmd[1]} - {message}")
                    except KeyError as ke:
                        self.ctx.Logs.error(ke)
                    except Exception as err:
                        self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

                case '006' | '018':
                    try:
                        # [':irc.deb.biz.st', '006', 'Dev-PyDefender', ':`-services.deb.biz.st', '------', '|', 'Users:', '9', '(47.37%)', '[00B]']
                        # [':irc.deb.biz.st', '018', 'Dev-PyDefender', ':4', 'servers', 'and', '19', 'users,', 'average', '4.75', 'users', 'per', 'server']
                        message = ' '.join(cmd[3:])
                        await self.ctx.Irc.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=self.user_to_notice,
                            msg=f"[{green}SERVER MSG{nogc}] {message}"
                        )
                    except KeyError as ke:
                        self.ctx.Logs.error(ke)
                    except Exception as err:
                        self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

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
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,nick_to=self.user_to_notice, msg="No shun")
                            case 'G':
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,nick_to=self.user_to_notice, msg="No gline")
                            case 'k':
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,nick_to=self.user_to_notice, msg="No kline")

                    except KeyError as ke:
                        self.ctx.Logs.error(ke)
                    except Exception as err:
                        self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

                case '223':
                    try:
                        # [':irc.deb.biz.st', '223', 'Dev-PyDefender', 'G', '*@162.142.125.217', '67624', '18776', 'irc.deb.biz.st', ':Proxy/Drone', 'detected.', 'Check', 'https://dronebl.org/lookup?ip=162.142.125.217', 'for', 'details.']
                        self.show_219 = False
                        host = str(cmd[4])
                        author = str(cmd[7])
                        reason = ' '.join(cmd[8:])

                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,nick_to=self.user_to_notice,
                                                msg=f"{bold}Author{nogc}: {author} - {bold}Host{nogc}: {host} - {bold}Reason{nogc}: {reason}"
                                                )

                    except KeyError as ke:
                        self.ctx.Logs.error(ke)
                    except Exception as err:
                        self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

                case 'SJOIN':
                    # ['@msgid=yldTlbwAGbzCGUcCIHi3ku;time=2024-11-11T17:56:24.297Z', ':001', 'SJOIN', '1728815963', '#znc', ':001LQ0L0C']
                    # Check if the user has an automode
                    try:
                        user_uid = self.ctx.User.clean_uid(cmd[5])
                        userObj: MUser = self.ctx.User.get_user(user_uid)
                        channel_name = cmd[4] if self.ctx.Channel.is_valid_channel(cmd[4]) else None
                        client_obj = self.ctx.Client.get_Client(user_uid)
                        nickname = userObj.nickname if userObj is not None else None

                        if client_obj is not None:
                            nickname = client_obj.account

                        if userObj is None:
                            return None

                        if 'r' not in userObj.umodes and 'o' not in userObj.umodes and not self.ctx.Client.is_exist(userObj.uid):
                            return None

                        db_data: dict[str, str] = {"nickname": nickname.lower(), "channel": channel_name.lower()}
                        db_query = await self.ctx.Base.db_execute_query("SELECT id, mode FROM command_automode WHERE LOWER(nickname) = :nickname AND LOWER(channel) = :channel", db_data)
                        db_result = db_query.fetchone()
                        if db_result:
                            id, mode = db_result
                            await self.ctx.Irc.Protocol.send2socket(f":{self.ctx.Config.SERVICE_ID} MODE {channel_name} {mode} {userObj.nickname}")

                    except KeyError as ke:
                        self.ctx.Logs.error(f"Key Error: {err}")

                case _:
                    pass

        except Exception as err:
            self.ctx.Logs.error(f"General Error: {err}", exc_info=True)

    async def hcmds(self, uidornickname: str, channel_name: Optional[str], cmd: list, fullcmd: list = []):

        command = str(cmd[0]).lower()
        dnickname = self.ctx.Config.SERVICE_NICKNAME
        service_id = self.ctx.Config.SERVICE_ID
        dchanlog = self.ctx.Config.SERVICE_CHANLOG
        self.user_to_notice = uidornickname
        fromuser = uidornickname
        fromchannel = channel_name

        match command:

            case 'automode':
                try:
                    await self.mod_utils.set_automode(self, cmd, fromuser)
                except IndexError:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} SET [nickname] [+/-mode] [#channel]")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} LIST")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"[AUTOMODES AVAILABLE] are {' / '.join(self.ctx.Settings.PROTOCTL_PREFIX)}")
                except Exception as err:
                    self.ctx.Logs.error(f"General Error: {err}")

            case 'deopall':
                try:
                    await self.mod_utils.set_deopall(self, fromchannel)
                except Exception as err:
                    self.ctx.Logs.error(f'Unknown Error: {str(err)}')

            case 'devoiceall':
                try:
                    await self.mod_utils.set_devoiceall(self, fromchannel)
                except Exception as err:
                    self.ctx.Logs.error(f'Unknown Error: {str(err)}')

            case 'voiceall':
                try:
                    await self.mod_utils.set_mode_to_all(self, fromchannel, '+', 'v')
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'opall':
                try:
                    await self.mod_utils.set_mode_to_all(self, fromchannel, '+', 'o')
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'op':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+o')
                except IndexError as e:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} op [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'deop':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-o')
                except IndexError as e:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} deop [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'owner':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+q')

                except IndexError as e:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} owner [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'deowner':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-q')

                except IndexError as e:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} deowner [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'protect':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+a')

                except IndexError as e:
                    self.ctx.Logs.warning(f'_hcmd DEOWNER: {str(e)}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'deprotect':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-a')

                except IndexError as e:
                    self.ctx.Logs.warning(f'_hcmd DEOWNER: {str(e)}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'halfop':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+h')

                except IndexError as e:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'dehalfop':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-h')

                except IndexError as e:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} dehalfop [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'voice':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '+v')
                except IndexError as e:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} voice [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'devoice':
                try:
                    await self.mod_utils.set_operation(self, cmd, fromchannel, fromuser, '-v')
                except IndexError as e:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} devoice [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'ban':
                try:
                    await self.mod_utils.set_ban(self, cmd, '+', fromuser)
                except IndexError as e:
                    self.ctx.Logs.warning(f'_hcmd BAN: {str(e)}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'unban':
                try:
                    await self.mod_utils.set_ban(self, cmd, '-', fromuser)
                except IndexError as e:
                    self.ctx.Logs.warning(f'_hcmd UNBAN: {str(e)}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'kick':
                try:
                    await self.mod_utils.set_kick(self, cmd, fromuser)
                except IndexError as e:
                    self.ctx.Logs.warning(f'_hcmd KICK: {str(e)}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME] [REASON]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'kickban':
                try:
                    await self.mod_utils.set_kickban(self, cmd, fromuser)
                except IndexError as e:
                    self.ctx.Logs.warning(f'_hcmd KICKBAN: {str(e)}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME] [REASON]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'join' | 'assign':
                try:
                    await self.mod_utils.set_assign_channel_to_service(self, cmd, fromuser)
                except IndexError as ie:
                    self.ctx.Logs.debug(f'{ie}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'part' | 'unassign':
                try:
                    # Syntax. !part #channel
                    await self.mod_utils.set_unassign_channel_to_service(self, cmd, fromuser)
                except IndexError as ie:
                    self.ctx.Logs.debug(f'{ie}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON]")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'topic':
                try:
                    if len(cmd) == 1:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} TOPIC #channel THE_TOPIC_MESSAGE")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} TOPIC #channel THE_TOPIC_MESSAGE")
                        return None

                    chan = str(cmd[1])
                    if not self.ctx.Channel.is_valid_channel(chan):
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="The channel must start with #")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} TOPIC #channel THE_TOPIC_MESSAGE")
                        return None

                    topic_msg = ' '.join(cmd[2:]).strip()

                    if topic_msg:
                        await self.ctx.Irc.Protocol.send2socket(f':{dnickname} TOPIC {chan} :{topic_msg}')
                    else:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You need to specify the topic")

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'wallops':
                try:
                    if len(cmd) == 1:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} WALLOPS THE_WALLOPS_MESSAGE")
                        return None

                    wallops_msg = ' '.join(cmd[1:]).strip()

                    if wallops_msg:
                        await self.ctx.Irc.Protocol.send2socket(f':{dnickname} WALLOPS {wallops_msg} ({dnickname})')
                    else:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You need to specify the wallops message")

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'globops':
                try:
                    if len(cmd) == 1:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} GLOBOPS THE_GLOBOPS_MESSAGE")
                        return None

                    globops_msg = ' '.join(cmd[1:]).strip()

                    if globops_msg:
                        await self.ctx.Irc.Protocol.send2socket(f':{dnickname} GLOBOPS {globops_msg} ({dnickname})')
                    else:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You need to specify the globops message")

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'gnotice':
                try:
                    if len(cmd) == 1:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} THE_GLOBAL_NOTICE_MESSAGE")
                        return None

                    gnotice_msg = ' '.join(cmd[1:]).strip()

                    if gnotice_msg:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to='$*.*', msg=f"[{self.ctx.Config.COLORS.red}GLOBAL NOTICE{self.ctx.Config.COLORS.nogc}] {gnotice_msg}")
                    else:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You need to specify the global notice message")

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'whois':
                try:
                    self.user_to_notice = fromuser
                    if len(cmd) == 1:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME")
                        return None

                    nickname = str(cmd[1])

                    if self.ctx.User.get_nickname(nickname) is None:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Nickname not found !")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME")
                        return None

                    await self.ctx.Irc.Protocol.send2socket(f':{dnickname} WHOIS {nickname}')

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'names':
                try:
                    if len(cmd) == 1:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} #CHANNEL")
                        return None

                    chan = str(cmd[1])

                    if not self.ctx.Channel.is_valid_channel(chan):
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="The channel must start with #")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} #channel")
                        return None

                    await self.ctx.Irc.Protocol.send2socket(f':{dnickname} NAMES {chan}')

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'invite':
                try:
                    if len(cmd) < 3:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME #CHANNEL")
                        return None

                    nickname = str(cmd[1])
                    chan = str(cmd[2])

                    if not self.ctx.Channel.is_valid_channel(chan):
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="The channel must start with #")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME #CHANNEL")
                        return None

                    if self.ctx.User.get_nickname(nickname) is None:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Nickname not found !")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()} NICKNAME #CHANNEL")
                        return None

                    await self.ctx.Irc.Protocol.send2socket(f':{dnickname} INVITE {nickname} {chan}')

                except KeyError as ke:
                    self.ctx.Logs.error(f"KeyError: {ke}")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'inviteme':
                try:
                    if len(cmd) == 0:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {str(cmd[0]).upper()}")
                        return None

                    await self.ctx.Irc.Protocol.send2socket(f':{dnickname} INVITE {fromuser} {self.ctx.Config.SERVICE_CHANLOG}')

                except KeyError as ke:
                    self.ctx.Logs.error(f"KeyError: {ke}")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'map':
                try:
                    self.user_to_notice = fromuser
                    await self.ctx.Irc.Protocol.send2socket(f':{dnickname} MAP')

                except KeyError as ke:
                    self.ctx.Logs.error(f"KeyError: {ke}")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'umode':
                try:
                    # .umode nickname +mode
                    if len(cmd) < 2:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [NICKNAME] [+/-]mode")
                        return None

                    nickname = str(cmd[1])
                    umode = str(cmd[2])

                    await self.ctx.Irc.Protocol.send_svsmode(nickname=nickname, user_mode=umode)
                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'mode':
                # .mode #channel +/-mode
                # .mode +/-mode
                try:

                    if len(cmd) < 2:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#CHANNEL] [+/-]mode")
                        return None

                    if fromchannel is None:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#CHANNEL] [+/-]mode")
                        return None

                    if len(cmd) == 2:
                        channel_mode = cmd[1]
                        if self.ctx.Channel.is_valid_channel(fromchannel):
                            await self.ctx.Irc.Protocol.send2socket(f":{dnickname} MODE {fromchannel} {channel_mode}")
                        else:
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : Channel [{fromchannel}] is not correct should start with #")
                        return None

                    if len(cmd) == 3:
                        provided_channel = cmd[1]
                        channel_mode = cmd[2]
                        await self.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {provided_channel} {channel_mode}")
                        return None

                except IndexError as e:
                    self.ctx.Logs.warning(f'_hcmd OP: {str(e)}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} {command.upper()} [#CHANNEL] [+/-]mode")
                except Exception as err:
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'get_mode':
                try:
                    await self.ctx.Irc.Protocol.send2socket(f'MODE {fromchannel}')
                except Exception as err:
                    self.ctx.Logs.error(f"General Error {err}")

            case 'svsjoin':
                try:
                    # SVSJOIN <nick> <channel>[,<channel2>..] [key1[,key2[..]]]
                    if len(cmd) < 4:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSJOIN <nick> <channel>[,<channel2>..] [key1[,key2[..]]]")
                        return None

                    nickname = str(cmd[1])
                    channels = str(cmd[2]).split(',')
                    keys = str(cmd[3]).split(',')

                    await self.ctx.Irc.Protocol.send_svsjoin(nickname, channels, keys)
                except IndexError as ke:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSJOIN <nick> <channel>[,<channel2>..] [key1[,key2[..]]]")
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSJOIN <nick> <channel>[,<channel2>..] [key1[,key2[..]]]")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'svspart':
                try:
                    # SVSPART <nick> <channel>[,<channel2>..] [<comment>]
                    if len(cmd) < 4:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSPART <nick> <channel>[,<channel2>..] [<comment>]")
                        return None

                    nickname = str(cmd[1])
                    channels = str(cmd[2]).split(',')
                    reason = ' '.join(cmd[3:])

                    await self.ctx.Irc.Protocol.send_svspart(nickname, channels, reason)
                except IndexError as ke:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSPART <nick> <channel>[,<channel2>..] [<comment>]")
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSPART <nick> <channel>[,<channel2>..] [<comment>]")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'svsnick':
                try:
                    # .svsnick nickname newnickname
                    nickname = str(cmd[1])
                    newnickname = str(cmd[2])
                    unixtime = self.ctx.Utils.get_unixtime()

                    if self.ctx.User.get_nickname(nickname) is None:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" This nickname do not exist")
                        return None

                    if len(cmd) != 3:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname newnickname")
                        return None

                    await self.ctx.Irc.Protocol.send2socket(f':{self.ctx.Config.SERVEUR_ID} SVSNICK {nickname} {newnickname} {unixtime}')

                except IndexError as ke:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname newnickname")
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname newnickname")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'sajoin':
                try:
                    # .sajoin nickname #channel
                    nickname = str(cmd[1])
                    channel = str(cmd[2])
                    if len(cmd) < 3:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname #channel")
                        return None

                    await self.ctx.Irc.Protocol.send_sajoin(nick_to_sajoin=nickname, channel_name=channel)

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname #channel")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'sapart':
                try:
                    # .sapart nickname #channel
                    if len(cmd) < 3:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname #channel")
                        return None

                    nickname = str(cmd[1])
                    channel = str(cmd[2])

                    await self.ctx.Irc.Protocol.send_sapart(nick_to_sapart=nickname, channel_name=channel)
                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname #channel")
                    self.ctx.Logs.error(f'Unknown Error: {str(err)}')

            case 'kill':
                try:
                    # 'kill', 'gline', 'ungline', 'shun', 'unshun'
                    # .kill nickname reason
                    if len(cmd) < 3:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname reason")
                        return None

                    nickname = str(cmd[1])
                    kill_reason = ' '.join(cmd[2:])

                    await self.ctx.Irc.Protocol.send2socket(f":{service_id} KILL {nickname} {kill_reason} ({self.ctx.Config.COLORS.red}{dnickname}{self.ctx.Config.COLORS.nogc})")
                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} SVSNICK nickname newnickname")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'gline':
                try:
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .gline [nickname] [host] [reason]
                    if len(cmd) < 4:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])
                    set_at_timestamp = self.ctx.Utils.get_unixtime()
                    expire_time = (60 * 60 * 24) + set_at_timestamp
                    gline_reason = ' '.join(cmd[3:])

                    if nickname == '*' and hostname == '*':
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" You want to close the server ? i would recommand ./unrealircd stop :)")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    await self.ctx.Irc.Protocol.send_gline(nickname=nickname, hostname=hostname, set_by=dnickname, expire_timestamp=expire_time, set_at_timestamp=set_at_timestamp, reason=gline_reason)

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'ungline':
                try:
                    # 'shun', 'unshun'
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .ungline nickname host
                    if len(cmd) < 2:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])

                    # await self.ctx.Irc.Protocol.send2socket(f":{self.ctx.Config.SERVEUR_ID} TKL - G {nickname} {hostname} {dnickname}")
                    await self.ctx.Irc.Protocol.send_ungline(nickname=nickname, hostname=hostname)

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'kline':
                try:
                    # TKL + k user host set_by expire_timestamp set_at_timestamp :reason
                    # .gline [nickname] [host] [reason]
                    if len(cmd) < 4:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])
                    set_at_timestamp = self.ctx.Utils.get_unixtime()
                    expire_time = (60 * 60 * 24) + set_at_timestamp
                    gline_reason = ' '.join(cmd[3:])

                    if nickname == '*' and hostname == '*':
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" You want to close the server ? i would recommand ./unrealircd stop :)")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    await self.ctx.Irc.Protocol.send_kline(nickname=nickname, hostname=hostname, set_by=dnickname, expire_timestamp=expire_time, set_at_timestamp=set_at_timestamp, reason=gline_reason)

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'unkline':
                try:
                    # 'shun', 'unshun'
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .ungline nickname host
                    if len(cmd) < 2:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])

                    await self.ctx.Irc.Protocol.send_unkline(nickname=nickname, hostname=hostname)

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'shun':
                try:
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .shun [nickname] [host] [reason]

                    if len(cmd) < 4:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])
                    set_at_timestamp = self.ctx.Utils.get_unixtime()
                    expire_time = (60 * 60 * 24) + set_at_timestamp
                    shun_reason = ' '.join(cmd[3:])

                    if nickname == '*' and hostname == '*':
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" You want to close the server ? i would recommand ./unrealircd stop :)")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                        return None

                    await self.ctx.Irc.Protocol.send2socket(f":{self.ctx.Config.SERVEUR_ID} TKL + s {nickname} {hostname} {dnickname} {expire_time} {set_at_timestamp} :{shun_reason}")
                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname host reason")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'unshun':
                try:
                    # 'shun', 'unshun'
                    # TKL + G user host set_by expire_timestamp set_at_timestamp :reason
                    # .unshun nickname host
                    if len(cmd) < 2:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                        return None

                    nickname = str(cmd[1])
                    hostname = str(cmd[2])

                    await self.ctx.Irc.Protocol.send2socket(f":{self.ctx.Config.SERVEUR_ID} TKL - s {nickname} {hostname} {dnickname}")

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()} nickname hostname")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'glinelist':
                try:
                    self.user_to_notice = fromuser
                    await self.ctx.Irc.Protocol.send2socket(f":{self.ctx.Config.SERVICE_ID} STATS G")

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()}")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'shunlist':
                try:
                    self.user_to_notice = fromuser
                    await self.ctx.Irc.Protocol.send2socket(f":{self.ctx.Config.SERVICE_ID} STATS s")

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()}")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case 'klinelist':
                try:
                    self.user_to_notice = fromuser
                    await self.ctx.Irc.Protocol.send2socket(f":{self.ctx.Config.SERVICE_ID} STATS k")

                except KeyError as ke:
                    self.ctx.Logs.error(ke)
                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" /msg {dnickname} {command.upper()}")
                    self.ctx.Logs.warning(f'Unknown Error: {str(err)}')

            case _:
                pass
