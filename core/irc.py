import asyncio
import re
import ssl
import threading
from typing import TYPE_CHECKING, Optional, Union
from core.classes.modules import rehash
from core.classes.interfaces.iprotocol import IProtocol
from core.utils import tr

if TYPE_CHECKING:
    from core.loader import Loader

class Irc:
    _instance = None

    def __new__(cls, *agrs):

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self, loader: 'Loader'):

        self.signal: bool = True

        # Load Context class (Loader)
        self.ctx = loader

        # Define Reader and Writer
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

        # Date et heure de la premiere connexion de Defender
        self.defender_connexion_datetime = self.ctx.Config.DEFENDER_CONNEXION_DATETIME

        # Lancer toutes les 30 secondes des actions de nettoyages
        self.beat = self.ctx.Config.DEFENDER_HEARTBEAT_FREQUENCY

        # Heartbeat active
        self.hb_active = self.ctx.Config.DEFENDER_HEARTBEAT

        # ID du serveur qui accueil le service ( Host Serveur Id )
        self.HSID = self.ctx.Config.HSID

        # Charset utiliser pour décoder/encoder les messages
        self.CHARSET = self.ctx.Config.SERVEUR_CHARSET
        """0: utf-8 | 1: iso-8859-1"""

        self.autolimit_started: bool = False
        """This variable is to make sure the thread is not running"""

        # define first reputation score to 0
        self.first_score: int = 0

        # Define first IP connexion
        self.first_connexion_ip: str = None

        # Load Commands Utils
        # self.Commands = self.Loader.Commands
        """Command utils"""
        self.ctx.Commands.build_command(0, 'core', 'help', 'This provide the help')
        self.ctx.Commands.build_command(0, 'core', 'auth', 'Login to the IRC Service')
        self.ctx.Commands.build_command(0, 'core', 'copyright', 'Give some information about the IRC Service')
        self.ctx.Commands.build_command(0, 'core', 'uptime', 'Give you since when the service is connected')
        self.ctx.Commands.build_command(0, 'core', 'firstauth', 'First authentication of the Service')
        self.ctx.Commands.build_command(1, 'core', 'deauth', 'Deauth from the irc service')
        self.ctx.Commands.build_command(1, 'core', 'checkversion', 'Check the version of the irc service')
        self.ctx.Commands.build_command(2, 'core', 'show_modules', 'Display a list of loaded modules')
        self.ctx.Commands.build_command(2, 'core', 'show_channels', 'Display a list of active channels')
        self.ctx.Commands.build_command(2, 'core', 'show_users', 'Display a list of connected users')
        self.ctx.Commands.build_command(2, 'core', 'show_admins', 'Display a list of administrators')
        self.ctx.Commands.build_command(2, 'core', 'show_configuration', 'Display the current configuration settings')
        self.ctx.Commands.build_command(2, 'core', 'show_cache', 'Display the current cache')
        self.ctx.Commands.build_command(2, 'core', 'clear_cache', 'Clear the cache!')
        self.ctx.Commands.build_command(3, 'core', 'addaccess', 'Add a user or entity to an access list with specific permissions.')
        self.ctx.Commands.build_command(3, 'core', 'editaccess', 'Modify permissions for an existing user or entity in the access list.')
        self.ctx.Commands.build_command(3, 'core', 'delaccess', 'Remove a user or entity from the access list.')
        self.ctx.Commands.build_command(3, 'core', 'cert', 'Append your new fingerprint to your account!')
        self.ctx.Commands.build_command(4, 'core', 'quit', 'Disconnect the bot or user from the server.')
        self.ctx.Commands.build_command(4, 'core', 'rehash', 'Reload the configuration file without restarting')
        self.ctx.Commands.build_command(4, 'core', 'restart', 'Restart the bot or service.')
        self.ctx.Commands.build_command(4, 'core', 'raw', 'Send a raw command directly to the IRC server')
        self.ctx.Commands.build_command(4, 'core', 'print_vars', 'Print users in a file.')
        self.ctx.Commands.build_command(4, 'core', 'show_timers', 'Display active timers')
        self.ctx.Commands.build_command(4, 'core', 'show_threads', 'Display active threads in the system')
        self.ctx.Commands.build_command(4, 'core', 'show_asyncio', 'Display active asyncio')
        self.ctx.Commands.build_command(4, 'core', 'start_rpc', 'Start defender jsonrpc server')
        self.ctx.Commands.build_command(4, 'core', 'stop_rpc', 'Stop defender jsonrpc server')
        self.ctx.Commands.build_command(4, 'core', 'load', 'Load an existing module')
        self.ctx.Commands.build_command(4, 'core', 'unload', 'Unload a module')
        self.ctx.Commands.build_command(4, 'core', 'reload', 'Reload a module')

    ##############################################
    #               CONNEXION IRC                #
    ##############################################

    async def run(self):
        try:
            self.signal = True
            await self.connect()
            await self.listen()
        except asyncio.exceptions.IncompleteReadError as ie:
            # When IRCd server is down
            # asyncio.exceptions.IncompleteReadError: 0 bytes read on a total of undefined expected bytes
            self.ctx.Logs.critical(f"The IRCd server is no more connected! {ie}")
        except asyncio.exceptions.CancelledError as cerr:
            self.ctx.Logs.debug(f"Asyncio CancelledError reached! {cerr}")

    async def connect(self):

        if self.ctx.Config.SERVEUR_SSL:
            self.reader, self.writer = await asyncio.open_connection(self.ctx.Config.SERVEUR_IP, self.ctx.Config.SERVEUR_PORT, ssl=self.ctx.Utils.get_ssl_context())
        else:
            self.reader, self.writer = await asyncio.open_connection(self.ctx.Config.SERVEUR_IP, self.ctx.Config.SERVEUR_PORT)

        self.init_service_user()
        self.Protocol: 'IProtocol' = self.ctx.PFactory.get()
        self.Protocol.register_command()
        await self.Protocol.send_link()

    async def listen(self):
        self.ctx.Base.create_asynctask(
            self.ctx.Base.create_thread_io(
                self.ctx.Utils.heartbeat,
                self.ctx, self.beat,
                run_once=True, thread_flag=True
                )
        )

        while self.signal:
            data = await self.reader.readuntil(b'\r\n')
            await self.send_response(data.splitlines())

    async def send_response(self, responses:list[bytes]) -> None:
        try:
            for data in responses:
                response = data.decode(self.CHARSET[0]).split()
                await self.cmd(response)

        except (UnicodeEncodeError, UnicodeDecodeError) as ue:
            for data in responses:
                response = data.decode(self.CHARSET[1], 'replace').split()
                await self.cmd(response)
            self.ctx.Logs.error(f'UnicodeEncodeError: {ue}')
            self.ctx.Logs.error(responses)
        except AssertionError as ae:
            self.ctx.Logs.error(f"Assertion error : {ae}")

    # --------------------------------------------
    #            END OF IRC CONNECTION           #
    # --------------------------------------------

    def init_service_user(self) -> None:

        self.ctx.User.insert(self.ctx.Definition.MUser(
            uid=self.ctx.Config.SERVICE_ID,
            nickname=self.ctx.Config.SERVICE_NICKNAME,
            username=self.ctx.Config.SERVICE_USERNAME,
            realname=self.ctx.Config.SERVICE_REALNAME,
            hostname=self.ctx.Config.SERVICE_HOST,
            umodes=self.ctx.Config.SERVICE_SMODES
        ))
        return None

    async def join_saved_channels(self) -> None:
        """## Joining saved channels"""
        exec_query = await self.ctx.Base.db_execute_query(f'SELECT distinct channel_name FROM {self.ctx.Config.TABLE_CHANNEL}')
        result_query = exec_query.fetchall()

        if result_query:
            for chan_name in result_query:
                chan = chan_name[0]
                await self.Protocol.send_sjoin(channel=chan)

    async def generate_help_menu(self, nickname: str, module: Optional[str] = None) -> None:

        # Check if the nickname is an admin
        p = self.Protocol
        admin_obj = self.ctx.Admin.get_admin(nickname)
        dnickname = self.ctx.Config.SERVICE_NICKNAME
        color_nogc = self.ctx.Config.COLORS.nogc
        color_black = self.ctx.Config.COLORS.black
        current_level = 0

        if admin_obj is not None:
            current_level = admin_obj.level

        await p.send_notice(nick_from=dnickname,nick_to=nickname, msg=f" ***************** LISTE DES COMMANDES *****************")
        header = f"  {'Level':<8}| {'Command':<25}| {'Module':<15}| {'Description':<35}"
        line = "-"*75
        await p.send_notice(nick_from=dnickname,nick_to=nickname, msg=header)
        await p.send_notice(nick_from=dnickname,nick_to=nickname, msg=f"  {line}")
        for cmd in self.ctx.Commands.get_commands_by_level(current_level):
            if module is None or cmd.module_name.lower() == module.lower():
                await p.send_notice(
                        nick_from=dnickname, 
                        nick_to=nickname, 
                        msg=f"  {color_black}{cmd.command_level:<8}{color_nogc}| {cmd.command_name:<25}| {cmd.module_name:<15}| {cmd.description:<35}"
                        )
        
        return None

    def insert_db_admin(self, uid: str, account: str, level: int, language: str) -> None:
        user_obj = self.ctx.User.get_user(uid)

        if user_obj is None:
            return None
        
        self.ctx.Admin.insert(
            self.ctx.Definition.MAdmin(
                **user_obj.to_dict(),
                language=language,
                account=account,
                level=int(level)
            )
        )

        return None

    def delete_db_admin(self, uid:str) -> None:

        if self.ctx.Admin.get_admin(uid) is None:
            return None

        if not self.ctx.Admin.delete(uid):
            self.ctx.Logs.critical(f'UID: {uid} was not deleted')

        return None

    async def create_defender_user(self, sender: str,  new_admin: str, new_level: int, new_password: str) -> bool:
        """Create a new admin user for defender

        Args:
            sender (str): The current admin sending the request
            new_admin (str): The new admin to create
            new_level (int): The level of the admin
            new_password (str): The clear password

        Returns:
            bool: True if created.
        """

        # > addaccess [nickname] [level] [password]
        dnick = self.ctx.Config.SERVICE_NICKNAME
        p = self.Protocol

        get_user = self.ctx.User.get_user(new_admin)
        level = self.ctx.Base.convert_to_int(new_level)
        password = new_password

        if get_user is None:
            response = tr("The nickname (%s) is not currently connected! please create a new admin when the nickname is connected to the network!", new_admin)
            await p.send_notice(dnick, sender, response)
            self.ctx.Logs.debug(f"New admin {new_admin} sent by {sender} is not connected")
            return False

        if level is None or level > 4 or level == 0:
            await p.send_notice(dnick, sender, tr("The level (%s) must be a number from 1 to 4", level))
            self.ctx.Logs.debug(f"Level must a number between 1 to 4 (sent by {sender})")
            return False

        nickname = get_user.nickname
        hostname = get_user.hostname
        vhost = get_user.vhost
        spassword = self.ctx.Utils.hash_password(password)

        # Check if the user already exist
        if not await self.ctx.Admin.db_is_admin_exist(nickname):
            mes_donnees = {'datetime': self.ctx.Utils.get_sdatetime(), 'user': nickname, 'password': spassword, 'hostname': hostname, 'vhost': vhost, 'level': level, 'language': self.ctx.Config.LANG}
            await self.ctx.Base.db_execute_query(f'''INSERT INTO {self.ctx.Config.TABLE_ADMIN} 
                    (createdOn, user, password, hostname, vhost, level, language) VALUES
                    (:datetime, :user, :password, :hostname, :vhost, :level, :language)
                    ''', mes_donnees)

            await p.send_notice(dnick, sender, tr("New admin (%s) has been added with level %s", nickname, level))
            self.ctx.Logs.info(f"A new admin ({nickname}) has been created by {sender}!")
            return True
        else:
            await p.send_notice(dnick, sender, tr("The nickname (%s) Already exist!", nickname))
            self.ctx.Logs.info(f"The nickname {nickname} already exist! (sent by {sender})")
            return False

    async def thread_check_for_new_version(self, fromuser: str) -> None:
        dnickname = self.ctx.Config.SERVICE_NICKNAME
        response = await self.ctx.Base.create_asynctask(
            self.ctx.Base.create_thread_io(
                self.ctx.Base.check_for_new_version, True
            )
        )

        if response:
            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" New Version available : {self.ctx.Config.CURRENT_VERSION} >>> {self.ctx.Config.LATEST_VERSION}")
            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=" Please run (git pull origin main) in the current folder")
        else:
            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=" You have the latest version of defender")

        return None

    async def cmd(self, data: list[str]) -> None:
        """Parse server response

        Args:
            data (list[str]): Server response splitted in a list
        """
        try:
            original_response: list[str] = data.copy()
            if len(original_response) < 2:
                self.ctx.Logs.warning(f'Size ({str(len(original_response))}) - {original_response}')
                return None

            self.ctx.Logs.debug(f">> {self.ctx.Utils.hide_sensitive_data(original_response)}")
            pos, parsed_protocol = self.Protocol.get_ircd_protocol_poisition(cmd=original_response, log=True)
            modules = self.ctx.ModuleUtils.model_get_loaded_modules().copy()

            for parsed in self.Protocol.Handler.get_ircd_commands():
                if parsed.command_name.upper() == parsed_protocol:
                    await parsed.func(original_response)
                    for module in modules:
                        await module.class_instance.cmd(original_response) if self.ctx.Utils.is_coroutinefunction(module.class_instance.cmd) else module.class_instance.cmd(original_response)

        except IndexError as ie:
            self.ctx.Logs.error(f"IndexError: {ie}")
        except Exception as err:
            self.ctx.Logs.error(f"General Error: {err}", exc_info=True)

    async def hcmds(self, user: str, channel: Union[str, None], cmd: list, fullcmd: list = []) -> None:
        """Create

        Args:
            user (str): The user who sent the query
            channel (Union[str, None]): If the command contain the channel
            cmd (list): The defender cmd
            fullcmd (list, optional): The full list of the cmd coming from PRIVMS. Defaults to [].

        Returns:
            None: Nothing to return
        """
        u = self.ctx.User.get_user(user)
        """The User Object"""
        if u is None:
            return None

        fromuser = u.nickname
        uid = u.uid
        self.ctx.Settings.current_admin = self.ctx.Admin.get_admin(user)              # set Current admin if any.

        RED = self.ctx.Config.COLORS.red
        GREEN = self.ctx.Config.COLORS.green
        BLACK = self.ctx.Config.COLORS.black
        NOGC = self.ctx.Config.COLORS.nogc

        # Defender information
        dnickname = self.ctx.Config.SERVICE_NICKNAME                                  # Defender nickname
        dchanlog = self.ctx.Config.SERVICE_CHANLOG                                    # Defender chan log

        if len(cmd) > 0:
            command = str(cmd[0]).lower()
        else:
            return False

        if not self.ctx.Commands.is_client_allowed_to_run_command(fromuser, command):
            command = 'notallowed'

        # Envoyer la commande aux classes dynamiquement chargées
        if command != 'notallowed':
            for module in self.ctx.ModuleUtils.DB_MODULES:
                await module.class_instance.hcmds(user, channel, cmd, fullcmd)

        match command:

            case 'notallowed':
                try:
                    current_command = str(cmd[0])
                    await self.Protocol.send_priv_msg(
                        msg=tr('[ %s%s%s ] - Access denied to %s', RED, current_command.upper(), NOGC, fromuser),
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=tr('Access denied!')
                        )

                except IndexError as ie:
                    self.ctx.Logs.error(f'{ie}')

            case 'deauth':

                current_command = str(cmd[0]).upper()
                uid_to_deauth = uid
                self.delete_db_admin(uid_to_deauth)

                await self.Protocol.send_priv_msg(
                        msg=tr("[ %s%s%s ] - %s has been disconnected from %s", RED, current_command, NOGC, fromuser, dnickname),
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                await self.Protocol.send_notice(dnickname, fromuser, tr("You have been successfully disconnected from %s", dnickname))
                return None

            case 'firstauth':
                # Syntax. /msg defender firstauth OWNER_NICKNAME OWNER_PASSWORD
                # Check command
                current_nickname = fromuser
                current_uid = uid
                current_command = str(cmd[0])

                if current_nickname is None:
                    self.ctx.Logs.critical(f"This nickname [{fromuser}] don't exist")
                    return None

                if len(cmd) < 3:
                    await self.Protocol.send_notice(dnickname,fromuser, tr("Syntax. /msg %s %s [OWNER_NICKNAME] [OWNER_PASSWORD]", self.ctx.Config.SERVICE_NICKNAME, current_command))
                    return None

                query = f"SELECT count(id) as c FROM {self.ctx.Config.TABLE_ADMIN}"
                result = await self.ctx.Base.db_execute_query(query)
                result_db = result.fetchone()

                if result_db[0] > 0:
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=tr("You can't use this command anymore ! Please use [%sauth] instead", self.ctx.Config.SERVICE_PREFIX)
                        )
                    return None

                # Credentials sent from the user
                cmd_owner = str(cmd[1])
                cmd_password = str(cmd[2])

                # Credentials coming from the Configuration
                config_owner    = self.ctx.Config.OWNER
                config_password = self.ctx.Config.PASSWORD

                if cmd_owner != config_owner:
                    self.ctx.Logs.critical(f"The nickname sent [{cmd_owner}] is different than the configuration owner [{config_owner}] !")
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=tr("The nickname sent [%s] is different than the one set in the configuration file !", cmd_owner)
                        )
                    return None

                if cmd_owner == config_owner and cmd_password == config_password:
                    await self.ctx.Base.db_create_first_admin()
                    self.insert_db_admin(current_uid, cmd_owner, 5, self.ctx.Config.LANG)
                    await self.Protocol.send_priv_msg(
                        msg=tr("[%s %s %s] - %s is now connected to %s", GREEN, current_command.upper(), NOGC, fromuser, dnickname),
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    await self.Protocol.send_notice(dnickname, fromuser, tr("Successfuly connected to %s", dnickname))
                else:
                    await self.Protocol.send_priv_msg(
                        msg=tr("[ %s %s %s ] - %s provided a wrong password!", RED, current_command.upper(), NOGC, current_nickname),
                        nick_from=dnickname,
                        channel=dchanlog
                        )

                    await self.Protocol.send_notice(dnickname, fromuser, tr("Wrong password!"))

            case 'auth':
                # Syntax. !auth nickname password
                if len(cmd) < 3:
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} [nickname] [password]")
                    return None

                user_to_log = cmd[1]
                password = cmd[2]
                current_client = u
                admin_obj = self.ctx.Admin.get_admin(fromuser)

                if current_client is None:
                    # This case should never happen
                    await self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                msg=f"[ {RED}{str(command).upper()} FAIL{NOGC} ] - Nickname {fromuser} is trying to connect to defender wrongly",
                                                channel=dchanlog)
                    return None
                
                if admin_obj:
                    await self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                msg=f"[ {GREEN}{str(command).upper()}{NOGC} ] - {fromuser} is already connected to {dnickname}",
                                                channel=dchanlog)
                    await self.Protocol.send_notice(dnickname, fromuser, tr("You are already connected to %s", dnickname))
                    return None

                mes_donnees = {'user': user_to_log, 'password': self.ctx.Utils.hash_password(password)}
                query = f"SELECT id, user, level, language FROM {self.ctx.Config.TABLE_ADMIN} WHERE user = :user AND password = :password"
                result = await self.ctx.Base.db_execute_query(query, mes_donnees)
                user_from_db = result.fetchone()

                if user_from_db:
                    account = str(user_from_db[1])
                    level = int(user_from_db[2])
                    language = str(user_from_db[3])
                    self.insert_db_admin(current_client.uid, account, level, language)
                    await self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                msg=f"[ {GREEN}{str(command).upper()} SUCCESS{NOGC} ] - {current_client.nickname} ({account}) est désormais connecté a {dnickname}",
                                                channel=dchanlog)
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=tr("Successfuly connected to %s", dnickname))
                    return None
                else:
                    await self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                msg=f"[ {RED}{str(command).upper()} FAIL{NOGC} ] - {current_client.nickname} a tapé un mauvais mot de pass",
                                                channel=dchanlog)
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=tr("Wrong password!"))
                    return None

            case 'addaccess':
                try:
                    # .addaccess adator 5 password
                    if len(cmd) < 4:
                        await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Right command : /msg {dnickname} addaccess [nickname] [level] [password]")
                        await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"level: from 1 to 4")
                        return None

                    new_admin = str(cmd[1])
                    level = self.ctx.Base.int_if_possible(cmd[2])
                    password = str(cmd[3])

                    await self.create_defender_user(fromuser, new_admin, level, password)
                    return None

                except IndexError as ie:
                    self.ctx.Logs.error(f'_hcmd addaccess: {ie}')
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} addaccess [nickname] [level] [password]")
                except TypeError as te:
                    self.ctx.Logs.error(f'_hcmd addaccess: out of index : {te}')
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} addaccess [nickname] [level] [password]")

            case 'editaccess':
                # .editaccess [USER] [NEW_PASSWORD] [LEVEL]
                try:
                    if len(cmd) < 3:
                        await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Right command : /msg {dnickname} editaccess [nickname] [NEWPASSWORD] [NEWLEVEL]")
                        await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"level: from 1 to 4")
                        return None

                    if len(cmd) == 4:
                        user_new_level = int(cmd[3])
                        if user_new_level > 5:
                            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Maximum authorized level is 5")
                            return None
                        if user_new_level == 0:
                            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You must provide a valid level [1 to 4]")
                            return None

                    user_to_edit = cmd[1]
                    user_password = self.ctx.Utils.hash_password(cmd[2])
                    get_admin = self.ctx.Admin.get_admin(fromuser)

                    if get_admin is None:
                        await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"This user {fromuser} has no Admin access")
                        return None

                    current_user = fromuser
                    current_uid = uid
                    current_user_level = get_admin.level

                    if current_user == user_to_edit:
                        user_new_level = get_admin.level

                    # Rechercher le user dans la base de données.
                    mes_donnees = {'user': user_to_edit}
                    query = f"SELECT user, level FROM {self.ctx.Config.TABLE_ADMIN} WHERE user = :user"
                    result = await self.ctx.Base.db_execute_query(query, mes_donnees)

                    isUserExist = result.fetchone()
                    if not isUserExist is None:

                        if current_user_level < int(isUserExist[1]):
                            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You are not allowed to edit this access")
                            return None

                        if current_user_level == int(isUserExist[1]) and current_user != user_to_edit:
                            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" You can't edit access of a user with same level")
                            return None

                        # Le user existe dans la base de données
                        data_to_update = {'user': user_to_edit, 'password': user_password, 'level': user_new_level}
                        sql_update = f"UPDATE {self.ctx.Config.TABLE_ADMIN} SET level = :level, password = :password WHERE user = :user"
                        exec_query = await self.ctx.Base.db_execute_query(sql_update, data_to_update)
                        if exec_query.rowcount > 0:
                            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" User {user_to_edit} has been modified with level {str(user_new_level)}")
                            self.ctx.Admin.update_level(user_to_edit, user_new_level)
                        else:
                            await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Impossible de modifier l'utilisateur {str(user_new_level)}")

                except TypeError as te:
                    self.ctx.Logs.error(f"Type error : {te}")
                except ValueError as ve:
                    self.ctx.Logs.error(f"Value Error : {ve}")
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" {self.ctx.Config.SERVICE_PREFIX}editaccess [USER] [NEWPASSWORD] [NEWLEVEL]")

            case 'delaccess':
                # .delaccess [USER] [CONFIRMUSER]
                if len(cmd) < 3:
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Right command : /msg {dnickname} delaccess [nickname] [CONFIRMNICKNAME]")
                    return None

                user_to_del = cmd[1]
                user_confirmation = cmd[2]

                if user_to_del != user_confirmation:
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer")
                    self.ctx.Logs.warning(f':{dnickname} NOTICE {fromuser} : Les user ne sont pas les mêmes, tu dois confirmer le user que tu veux supprimer')
                    return None

                get_admin = self.ctx.Admin.get_admin(fromuser)

                if get_admin is None:
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"This user {fromuser} has no admin access")
                    return None

                current_user = fromuser
                current_uid = uid
                current_user_level = get_admin.level

                # Rechercher le user dans la base de données.
                mes_donnees = {'user': user_to_del}
                query = f"SELECT user, level FROM {self.ctx.Config.TABLE_ADMIN} WHERE user = :user"
                result = await self.ctx.Base.db_execute_query(query, mes_donnees)
                info_user = result.fetchone()

                if not info_user is None:
                    level_user_to_del = info_user[1]
                    if current_user_level <= level_user_to_del:
                        await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You are not allowed to delete this access")
                        self.ctx.Logs.warning(f':{dnickname} NOTICE {fromuser} : You are not allowed to delete this access')
                        return None

                    data_to_delete = {'user': user_to_del}
                    sql_delete = f"DELETE FROM {self.ctx.Config.TABLE_ADMIN} WHERE user = :user"
                    exec_query = await self.ctx.Base.db_execute_query(sql_delete, data_to_delete)
                    if exec_query.rowcount > 0:
                        await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"User {user_to_del} has been deleted !")
                        self.ctx.Admin.delete(user_to_del)
                    else:
                        await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Impossible de supprimer l'utilisateur.")
                        self.ctx.Logs.warning(f":{dnickname} NOTICE {fromuser} : Impossible de supprimer l'utilisateur.")

            case 'cert':
                # Syntax !cert
                try:
                    if len(cmd) < 2:
                        await self.Protocol.send_notice(dnickname, fromuser, f"Right command : /msg {dnickname} cert add")
                        await self.Protocol.send_notice(dnickname, fromuser, f"Right command : /msg {dnickname} cert del")
                        return None

                    admin_obj = self.ctx.Admin.get_admin(fromuser)
                    param = cmd[1] # add or del
                    match param:
                        case 'add':
                            if admin_obj:
                                if admin_obj.fingerprint is not None:
                                    query = f'UPDATE {self.ctx.Config.TABLE_ADMIN} SET fingerprint = :fingerprint WHERE user = :user'
                                    r = await self.ctx.Base.db_execute_query(query, {'fingerprint': admin_obj.fingerprint, 'user': admin_obj.account})
                                    if r.rowcount > 0:
                                        await self.Protocol.send_notice(dnickname, fromuser, f'[ {GREEN}CERT{NOGC} ] Your new fingerprint has been attached to your account. {admin_obj.fingerprint}')
                                    else:
                                        await self.Protocol.send_notice(dnickname, fromuser, f'[ {RED}CERT{NOGC} ] Impossible to add your fingerprint.{admin_obj.fingerprint}')
                                else:
                                    await self.Protocol.send_notice(dnickname, fromuser, f'[ {RED}CERT{NOGC} ] There is no fingerprint to add.')
                        case 'del':
                            if admin_obj:
                                query = f"UPDATE {self.ctx.Config.TABLE_ADMIN} SET fingerprint = :fingerprint WHERE user =:user"
                                r = await self.ctx.Base.db_execute_query(query, {'fingerprint': None, 'user': admin_obj.account})
                                if r.rowcount > 0:
                                    await self.Protocol.send_notice(dnickname, fromuser, f'[ {GREEN}CERT{NOGC} ] Your fingerprint has been removed from your account. {admin_obj.fingerprint}')
                                else:
                                    await self.Protocol.send_notice(dnickname, fromuser, f'[ {RED}CERT{NOGC} ] Impossible to remove your fingerprint.{admin_obj.fingerprint}')
                        case _:
                            await self.Protocol.send_notice(dnickname, fromuser, f"Right command : /msg {dnickname} cert add")
                            await self.Protocol.send_notice(dnickname, fromuser, f"Right command : /msg {dnickname} cert del")
                            return None

                except Exception as e:
                    self.ctx.Logs.error(e)

            case 'help':
                # Syntax. !help [module_name]
                module_name = str(cmd[1]) if len(cmd) == 2 else None
                await self.generate_help_menu(nickname=fromuser, module=module_name)
                return None
                
            case 'load':
                try:
                    # Load a module ex: .load mod_defender
                    if len(cmd) < 2:
                        await self.Protocol.send_notice(dnickname, fromuser, tr("Syntax. /msg %s %s MODULE_NAME", dnickname, command.upper()))
                        return None

                    mod_name = str(cmd[1])
                    await self.ctx.ModuleUtils.load_one_module(mod_name, fromuser)
                    return None
                except KeyError as ke:
                    self.ctx.Logs.error(f"Key Error: {ke} - list recieved: {cmd}")
                except Exception as err:
                    self.ctx.Logs.error(f"General Error: {err} - list recieved: {cmd}", exc_info=True)

            case 'unload':
                # unload mod_defender
                try:
                    # The module name. exemple: mod_defender
                    if len(cmd) < 2:
                        self.Protocol.send_notice(dnickname, fromuser, tr("Syntax. /msg %s %s MODULE_NAME", dnickname, command.upper()))
                        return None
                    module_name = str(cmd[1]).lower()
                    await self.ctx.ModuleUtils.unload_one_module(module_name, False)
                    return None
                except Exception as err:
                    self.ctx.Logs.error(f"General Error: {err}")

            case 'reload':
                # reload mod_defender
                try:
                    # ==> mod_defender
                    if len(cmd) < 2:
                        await self.Protocol.send_notice(dnickname, fromuser, tr("Syntax. /msg %s %s MODULE_NAME", dnickname, command.upper()))
                        return None

                    module_name = str(cmd[1]).lower()
                    await self.ctx.ModuleUtils.reload_one_module(module_name, fromuser)
                    return None
                except Exception as e:
                    self.ctx.Logs.error(f"Something went wrong with a module you want to reload: {e}")
                    await self.Protocol.send_priv_msg(
                        nick_from=dnickname,
                        msg=f"Something went wrong with the module: {e}",
                        channel=dchanlog
                    )
                    await self.ctx.ModuleUtils.db_delete_module(module_name)

            case 'quit':
                try:
                    final_reason = ' '.join(cmd[1:])
                    self.hb_active = False
                    self.ctx.Base.create_asynctask(rehash.force_shutdown(self.ctx), run_once=True)
                    await rehash.shutdown(self.ctx)
                    self.ctx.Base.execute_periodic_action()

                    for chan_name in self.ctx.Channel.UID_CHANNEL_DB:
                        await self.Protocol.send_set_mode('-l', channel_name=chan_name.name)

                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Arrêt du service {dnickname}"
                    )
                    self.signal = False
                    await self.Protocol.send_squit(server_id=self.ctx.Config.SERVEUR_ID, server_link=self.ctx.Config.SERVEUR_LINK, reason=final_reason)
                    self.ctx.Logs.info(f'Arrêt du server {dnickname}')
                    self.ctx.Config.DEFENDER_RESTART = 0

                    self.writer.close()
                    await self.writer.wait_closed()

                except IndexError as ie:
                    self.ctx.Logs.error(f'{ie}')
                except ConnectionResetError:
                    if self.writer.is_closing():
                        self.ctx.Logs.debug(f"Defender stopped properly!")
                except ssl.SSLError as serr:
                    self.ctx.Logs.error(f"Defender has ended with an SSL Error! - {serr}")

            case 'restart':
                final_reason = ' '.join(cmd[1:])
                await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"{dnickname.capitalize()} is going to restart!")
                
                # Set restart status to 1 saying that the service will restart
                self.ctx.Config.DEFENDER_RESTART = 1

                # set init to 1 saying that the service will be re initiated
                self.ctx.Config.DEFENDER_INIT = 1

                await rehash.restart_service(self.ctx)

            case 'rehash':
                await rehash.rehash_service(self.ctx, fromuser)
                return None

            case 'show_modules':
                self.ctx.Logs.debug('List of modules: ' + ', '.join([module.module_name for module in self.ctx.ModuleUtils.model_get_loaded_modules()]))
                all_modules  = self.ctx.ModuleUtils.get_all_available_modules()
                loaded = False
                results = await self.ctx.Base.db_execute_query(f'SELECT datetime, user, module_name FROM {self.ctx.Config.TABLE_MODULE}')
                results = results.fetchall()

                for module in all_modules:
                    for loaded_mod in results:
                        if module == loaded_mod[2]:
                            loaded_datetime = loaded_mod[0]
                            loaded_user = loaded_mod[1]
                            loaded = True

                    if loaded:
                        await self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=tr('%s - %sLoaded%s by %s on %s', module, GREEN, NOGC, loaded_user, loaded_datetime)
                        )
                        loaded = False
                    else:
                        await self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=tr('%s - %sNot Loaded%s', module, RED, NOGC)
                        )

            case 'show_timers':
                if self.ctx.Base.running_timers:
                    for the_timer in self.ctx.Base.running_timers:
                        await self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg=f">> {the_timer.name} - {the_timer.is_alive()}"
                        )
                else:
                    await self.Protocol.send_notice(
                            nick_from=dnickname,
                            nick_to=fromuser,
                            msg="There is no timers that are running!"
                        )
                return None

            case 'show_threads':
                for thread in self.ctx.Base.running_threads:
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f">> {thread.name} ({thread.is_alive()})"
                    )
                
                for thread in threading.enumerate():
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f">> Thread name: {thread.name} - Is alive: {thread.is_alive()} - Daemon: {thread.daemon}"
                    )

                return None

            case 'show_asyncio':
                for task in asyncio.all_tasks():
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f">> {task.get_name()} (active)"
                    )
                return None

            case 'show_channels':
                for chan in self.ctx.Channel.UID_CHANNEL_DB:
                    list_nicknames: list = []
                    for uid in chan.uids:
                        pattern = fr'[:|@|%|\+|~|\*]*'
                        parsed_UID = re.sub(pattern, '', uid)
                        list_nicknames.append(self.ctx.User.get_nickname(parsed_UID))

                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Channel: {chan.name} - Users: {list_nicknames}"
                    )
                return None

            case 'show_users':
                count_users = len(self.ctx.User.UID_DB)
                await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Total Connected Users: {count_users}")
                for db_user in self.ctx.User.UID_DB:
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_user.uid} - isWebirc: {db_user.isWebirc} - isWebSocket: {db_user.isWebsocket} - Nickname: {db_user.nickname} - Connection: {db_user.connexion_datetime}"
                    )
                return None

            case 'show_admins':
                for db_admin in self.ctx.Admin.UID_ADMIN_DB:
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"UID : {db_admin.uid} - Nickname: {db_admin.nickname} - Account: {db_admin.account} - Level: {db_admin.level} - Language: {db_admin.language} - Connection: {db_admin.connexion_datetime}"
                    )
                return None

            case 'show_configuration':
                for key, value in self.ctx.Config.to_dict().items():
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f'{key} = {value}'
                        )
                return None

            case 'show_cache':
                await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"The cache is currently contains {self.ctx.Settings.get_cache_size()} value(s).")
                for key, value in self.ctx.Settings.show_cache().items():
                    await self.Protocol.send_notice(
                        nick_from=dnickname,
                        nick_to=fromuser,
                        msg=f"Key : {key} - Value: {value}"
                    )
                return None
            
            case 'clear_cache':
                cache_size = self.ctx.Settings.get_cache_size()
                if cache_size > 0:
                    self.ctx.Settings.clear_cache()
                    await self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"{cache_size} value(s) has been cleared from the cache.")
                return None

            case 'uptime':
                uptime = self.ctx.Utils.get_defender_uptime(self.ctx)
                await self.Protocol.send_notice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=uptime
                )
                return None

            case 'copyright':
                await self.Protocol.send_notice(
                    nick_from=dnickname,
                    nick_to=fromuser,
                    msg=f">> Defender V{self.ctx.Config.CURRENT_VERSION} Developped by adator®."
                )
                return None

            case 'checkversion':
                self.ctx.Base.create_asynctask(self.thread_check_for_new_version(fromuser))
                return None

            case 'raw':
                raw_command = ' '.join(cmd[1:])
                await self.Protocol.send_raw(raw_command)
                return None

            case 'print_vars':
                with open('users.txt', 'w') as fw:
                    i = 1
                    for u in self.ctx.User.UID_DB:
                        w = fw.write(u.to_dict().__str__() + "\n")
                        self.ctx.Logs.debug(f" {i} - chars written {w}")
                        i += 1
                    await self.Protocol.send_priv_msg(dnickname, "Data written in users.txt file", dchanlog)
                
                with open('modules.txt', 'w') as fw:
                    i = 1
                    for u in self.ctx.ModuleUtils.DB_MODULE_HEADERS:
                        w = fw.write(u.to_dict().__str__() + "\n")
                        self.ctx.Logs.debug(f" {i} - chars written {w}")
                        i += 1
                    await self.Protocol.send_priv_msg(dnickname, "Data written in modules.txt file", dchanlog)

                return None

            case 'start_rpc':
                self.ctx.Base.create_asynctask(self.ctx.RpcServer.start_rpc_server())

            case 'stop_rpc':
                self.ctx.Base.create_asynctask(self.ctx.RpcServer.stop_rpc_server())

            case _:
                pass
