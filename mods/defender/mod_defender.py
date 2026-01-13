from dataclasses import dataclass
import logging
from typing import Any, TYPE_CHECKING, Optional
from core.classes.interfaces.imodule import IModule
import mods.defender.schemas as schemas
import mods.defender.utils as utils
import mods.defender.threads as thds
from core.utils import tr

if TYPE_CHECKING:
    from core.loader import Loader

class Defender(IModule):

    @dataclass
    class ModConfModel(schemas.ModConfModel):
        ...

    MOD_HEADER: dict[str, str] = {
        'name':'Defender',
        'version':'1.0.0',
        'description':'Defender main module that uses the reputation security.',
        'author':'Defender Team',
        'core_version':'Defender-6'
    }

    def __init__(self, context: 'Loader') -> None:
        super().__init__(context)
        self._mod_config: Optional[schemas.ModConfModel] = None
        self.Schemas = schemas.RepDB()
        self.Threads = thds

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

        # table_autoop = '''CREATE TABLE IF NOT EXISTS defender_autoop (
        #     id INTEGER PRIMARY KEY AUTOINCREMENT,
        #     datetime TEXT,
        #     nickname TEXT,
        #     channel TEXT
        #     )
        # '''

        table_autolimit = '''CREATE TABLE IF NOT EXISTS defender_autolimit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            channel TEXT
        '''

        # self.ctx.Base.db_execute_query(table_autoop)
        # self.ctx.Base.db_execute_query(table_config)
        # self.ctx.Base.db_execute_query(table_trusted)
        return None

    async def load(self):
        # Variable qui va contenir les options de configuration du module Defender
        self._mod_config: schemas.ModConfModel  = self.ModConfModel()

        # sync the database with local variable (Mandatory)
        await self.sync_db()

        # Add module utils functions
        self.mod_utils = utils

        # Create module commands (Mandatory)
        self.ctx.Commands.build_command(0, self.module_name, 'code', 'Display the code or key for access')
        self.ctx.Commands.build_command(1, self.module_name, 'info', 'Provide information about the channel or server')
        self.ctx.Commands.build_command(1, self.module_name, 'autolimit', 'Automatically set channel user limits')
        self.ctx.Commands.build_command(3, self.module_name, 'reputation', 'Check or manage user reputation')
        self.ctx.Commands.build_command(3, self.module_name, 'proxy_scan', 'Scan users for proxy connections')
        self.ctx.Commands.build_command(3, self.module_name, 'flood', 'Handle flood detection and mitigation')
        self.ctx.Commands.build_command(3, self.module_name, 'status', 'Check the status of the server or bot')
        self.ctx.Commands.build_command(3, self.module_name, 'show_reputation', 'Display reputation information')
        self.ctx.Commands.build_command(3, self.module_name, 'sentinel', 'Monitor and guard the channel or server')

        self.timeout = self.ctx.Config.API_TIMEOUT

        # Listes qui vont contenir les ip a scanner avec les différentes API
        self.Schemas.DB_ABUSEIPDB_USERS = []
        self.Schemas.DB_FREEIPAPI_USERS = []
        self.Schemas.DB_CLOUDFILT_USERS = []
        self.Schemas.DB_PSUTIL_USERS = []
        self.Schemas.DB_LOCALSCAN_USERS = []

        # Variables qui indique que les threads sont en cours d'éxecutions
        self.abuseipdb_isRunning = True if self.mod_config.abuseipdb_scan == 1 else False
        self.freeipapi_isRunning = True if self.mod_config.freeipapi_scan == 1 else False
        self.cloudfilt_isRunning = True if self.mod_config.cloudfilt_scan == 1 else False
        self.psutil_isRunning = True if self.mod_config.psutil_scan == 1 else False
        self.localscan_isRunning = True if self.mod_config.local_scan == 1 else False
        self.reputationTimer_isRunning = True if self.mod_config.reputation == 1 else False
        self.autolimit_isRunning = True if self.mod_config.autolimit == 1 else False

        # Variable qui va contenir les users
        self.flood_system = {}

        # Contient les premieres informations de connexion
        self.reputation_first_connexion = {'ip': '', 'score': -1}

        # Laisser vide si aucune clé
        self.abuseipdb_key = '13c34603fee4d2941a2c443cc5c77fd750757ca2a2c1b304bd0f418aff80c24be12651d1a3cfe674'
        self.cloudfilt_key = 'r1gEtjtfgRQjtNBDMxsg'

        # Démarrer les threads pour démarrer les api
        self.ctx.Base.create_asynctask(self.Threads.coro_freeipapi_scan(self)) if self.mod_config.freeipapi_scan == 1 else None
        self.ctx.Base.create_asynctask(self.Threads.coro_cloudfilt_scan(self)) if self.mod_config.cloudfilt_scan == 1 else None
        self.ctx.Base.create_asynctask(self.Threads.coro_abuseipdb_scan(self)) if self.mod_config.abuseipdb_scan == 1 else None
        self.ctx.Base.create_asynctask(self.Threads.coro_local_scan(self)) if self.mod_config.local_scan == 1 else None
        self.ctx.Base.create_asynctask(self.Threads.coro_psutil_scan(self)) if self.mod_config.psutil_scan == 1 else None
        self.ctx.Base.create_asynctask(self.Threads.coro_apply_reputation_sanctions(self)) if self.mod_config.reputation == 1 else None
        self.ctx.Base.create_asynctask(self.Threads.coro_autolimit(self)) if self.mod_config.autolimit == 1 else None

        if self.mod_config.reputation == 1:
            await self.ctx.Irc.Protocol.send_sjoin(self.ctx.Config.SALON_JAIL)
            await self.ctx.Irc.Protocol.send2socket(f":{self.ctx.Config.SERVICE_NICKNAME} SAMODE {self.ctx.Config.SALON_JAIL} +o {self.ctx.Config.SERVICE_NICKNAME}")
            for chan in self.ctx.Channel.UID_CHANNEL_DB:
                if chan.name != self.ctx.Config.SALON_JAIL:
                    await self.ctx.Irc.Protocol.send_set_mode('+b', channel_name=chan.name, params='~security-group:unknown-users')
                    await self.ctx.Irc.Protocol.send_set_mode('+eee', channel_name=chan.name, params='~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users')

    def __onload(self):

        abuseipdb = self.ctx.Settings.get_cache('ABUSEIPDB')
        freeipapi = self.ctx.Settings.get_cache('FREEIPAPI')
        cloudfilt = self.ctx.Settings.get_cache('CLOUDFILT')
        psutils = self.ctx.Settings.get_cache('PSUTIL')
        localscan = self.ctx.Settings.get_cache('LOCALSCAN')

        if abuseipdb:
            self.Schemas.DB_ABUSEIPDB_USERS = abuseipdb

        if freeipapi:
            self.Schemas.DB_FREEIPAPI_USERS = freeipapi

        if cloudfilt:
            self.Schemas.DB_CLOUDFILT_USERS = cloudfilt

        if psutils:
            self.Schemas.DB_PSUTIL_USERS = psutils

        if localscan:
            self.Schemas.DB_LOCALSCAN_USERS = localscan

    async def unload(self) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """
        self.Schemas.DB_ABUSEIPDB_USERS = []
        self.Schemas.DB_FREEIPAPI_USERS = []
        self.Schemas.DB_CLOUDFILT_USERS = []
        self.Schemas.DB_PSUTIL_USERS = []
        self.Schemas.DB_LOCALSCAN_USERS = []

        self.abuseipdb_isRunning:bool = False
        self.freeipapi_isRunning:bool = False
        self.cloudfilt_isRunning:bool = False
        self.psutil_isRunning:bool    = False
        self.localscan_isRunning:bool = False
        self.reputationTimer_isRunning:bool = False
        self.autolimit_isRunning: bool = False

        self.ctx.Commands.drop_command_by_module(self.module_name)

        if self.mod_config.reputation == 1:
            await self.ctx.Irc.Protocol.send_part_chan(self.ctx.Config.SERVICE_ID, self.ctx.Config.SALON_JAIL)
            for chan in self.ctx.Channel.UID_CHANNEL_DB:
                if chan.name != self.ctx.Config.SALON_JAIL:
                    await self.ctx.Irc.Protocol.send_set_mode('-b', channel_name=chan.name, params='~security-group:unknown-users')
                    await self.ctx.Irc.Protocol.send_set_mode('-eee', channel_name=chan.name, params='~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users')

        return None

    async def insert_db_trusted(self, uid: str, nickname:str) -> None:
        u = self.ctx.User.get_user(uid)
        if u is None:
            return None

        uid = u.uid
        nickname = u.nickname

        query = "SELECT id FROM def_trusted WHERE user = ?"
        exec_query = await self.ctx.Base.db_execute_query(query, {"user": nickname})
        response = exec_query.fetchone()

        if response is not None:
            q_insert = "INSERT INTO def_trusted (datetime, user, host, vhost) VALUES (?, ?, ?, ?)"
            mes_donnees = {'datetime': self.ctx.mod_utils.get_datetime(), 'user': nickname, 'host': '*', 'vhost': '*'}
            exec_query = self.ctx.Base.db_execute_query(q_insert, mes_donnees)
            pass

    async def join_saved_channels(self) -> None:
        """_summary_
        """
        try:
            result = await self.ctx.Base.db_execute_query(f"SELECT distinct channel_name FROM {self.ctx.Config.TABLE_CHANNEL}")
            channels = result.fetchall()
            jail_chan = self.ctx.Config.SALON_JAIL
            jail_chan_mode = self.ctx.Config.SALON_JAIL_MODES
            service_id = self.ctx.Config.SERVICE_ID
            dumodes = self.ctx.Config.SERVICE_UMODES
            dnickname = self.ctx.Config.SERVICE_NICKNAME

            for channel in channels:
                chan = channel[0]
                await self.ctx.Irc.Protocol.send_sjoin(chan)
                if chan == jail_chan:
                    await self.ctx.Irc.Protocol.send2socket(f":{service_id} SAMODE {jail_chan} +{dumodes} {dnickname}")
                    await self.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {jail_chan} +{jail_chan_mode}")

            return None

        except Exception as err:
            self.ctx.Logs.error(f"General Error: {err}")

    async def cmd(self, data: list[str]) -> None:

        if not data or len(data) < 2:
            return None
        cmd = data.copy() if isinstance(data, list) else list(data).copy()

        try:
            index, command = self.ctx.Irc.Protocol.get_ircd_protocol_poisition(cmd)
            if index == -1:
                return None

            match command:

                case 'REPUTATION':
                    self.mod_utils.handle_on_reputation(self, cmd)
                    return None

                case 'MODE':
                    await self.mod_utils.handle_on_mode(self, cmd)
                    return None

                case 'PRIVMSG':
                    await self.mod_utils.handle_on_privmsg(self, cmd)
                    return None

                case 'UID':
                    await self.mod_utils.handle_on_uid(self, cmd)
                    return None

                case 'SJOIN':
                    await self.mod_utils.handle_on_sjoin(self, cmd)
                    return None

                case 'SLOG':
                    self.mod_utils.handle_on_slog(self, cmd)
                    return None

                case 'NICK':
                    await self.mod_utils.handle_on_nick(self, cmd)
                    return None

                case 'QUIT':
                    await self.mod_utils.handle_on_quit(self, cmd)
                    return None

                case _:
                    return None

        except KeyError as ke:
            self.ctx.Logs.error(f"{ke} / {cmd} / length {str(len(cmd))}")
        except IndexError as ie:
            self.ctx.Logs.error(f"{ie} / {cmd} / length {str(len(cmd))}")
        except Exception as err:
            self.ctx.Logs.error(f"General Error: {err}", exc_info=True)

    async def hcmds(self, user: str, channel: Any, cmd: list, fullcmd: list = []) -> None:
        u = self.ctx.User.get_user(user)
        if u is None:
            return None

        command = str(cmd[0]).lower()
        fromuser = u.nickname
        channel = fromchannel = channel if self.ctx.Channel.is_valid_channel(channel) else None

        dnickname = self.ctx.Config.SERVICE_NICKNAME            # Defender nickname
        dchanlog = self.ctx.Config.SERVICE_CHANLOG              # Defender chan log
        dumodes = self.ctx.Config.SERVICE_UMODES                # Les modes de Defender
        service_id = self.ctx.Config.SERVICE_ID                 # Defender serveur id
        jail_chan = self.ctx.Config.SALON_JAIL                  # Salon pot de miel
        jail_chan_mode = self.ctx.Config.SALON_JAIL_MODES       # Mode du salon "pot de miel"

        color_green = self.ctx.Config.COLORS.green
        color_red = self.ctx.Config.COLORS.red
        color_black = self.ctx.Config.COLORS.black
        color_nogc = self.ctx.Config.COLORS.nogc

        match command:

            case 'show_reputation':

                if self.mod_config.reputation == 0:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="Reputation system if off!")
                    return None

                if not self.ctx.Reputation.UID_REPUTATION_DB:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="No one is suspected")

                for suspect in self.ctx.Reputation.UID_REPUTATION_DB:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, 
                                             nick_to=fromuser, 
                                             msg=f" Uid: {suspect.uid} | Nickname: {suspect.nickname} | Reputation: {suspect.score_connexion} | Secret code: {suspect.secret_code} | Connected on: {suspect.connexion_datetime}")

            case 'code':
                try:
                    release_code = cmd[1]
                    jailed_nickname = u.nickname
                    jailed_UID = u.uid
                    get_reputation = self.ctx.Reputation.get_reputation(jailed_UID)

                    if get_reputation is None:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=" No code is requested ...")
                        return False

                    jailed_IP = get_reputation.remote_ip
                    jailed_salon = self.ctx.Config.SALON_JAIL
                    reputation_seuil = self.mod_config.reputation_seuil
                    welcome_salon = self.ctx.Config.SALON_LIBERER

                    self.ctx.Logs.debug(f"IP de {jailed_nickname} : {jailed_IP}")
                    link = self.ctx.Config.SERVEUR_LINK
                    color_green = self.ctx.Config.COLORS.green
                    color_black = self.ctx.Config.COLORS.black

                    if release_code == get_reputation.secret_code:
                        await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg="Bon mot de passe. Allez du vent !", channel=jailed_salon)

                        if self.mod_config.reputation_ban_all_chan == 1:
                            for chan in self.ctx.Channel.UID_CHANNEL_DB:
                                if chan.name != jailed_salon:
                                    await self.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {chan.name} -b {jailed_nickname}!*@*")

                        self.ctx.Reputation.delete(jailed_UID)
                        self.ctx.Logs.debug(f'{jailed_UID} - {jailed_nickname} removed from REPUTATION_DB')
                        await self.ctx.Irc.Protocol.send_sapart(nick_to_sapart=jailed_nickname, channel_name=jailed_salon)
                        await self.ctx.Irc.Protocol.send_sajoin(nick_to_sajoin=jailed_nickname, channel_name=welcome_salon)
                        await self.ctx.Irc.Protocol.send2socket(f":{link} REPUTATION {jailed_IP} {self.mod_config.reputation_score_after_release}")
                        u.score_connexion = reputation_seuil + 1
                        await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname,
                                                  msg=f"[{color_green} MOT DE PASS CORRECT {color_black}] : You have now the right to enjoy the network !", 
                                                  nick_to=jailed_nickname)

                    else:
                        await self.ctx.Irc.Protocol.send_priv_msg(
                                nick_from=dnickname,
                                msg="Mauvais password", 
                                channel=jailed_salon
                            )
                        await self.ctx.Irc.Protocol.send_priv_msg(
                                nick_from=dnickname,
                                msg=f"[{color_green} MAUVAIS PASSWORD {color_black}] You have typed a wrong code. for recall your password is: {self.ctx.Config.SERVICE_PREFIX}code {get_reputation.secret_code}",
                                nick_to=jailed_nickname
                            )

                except IndexError as ie:
                    self.ctx.Logs.error(f'Index Error: {ie}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} code [code]")
                except KeyError as ke:
                    self.ctx.Logs.error(f'_hcmd code: KeyError {ke}')

            case 'autolimit':
                try:
                    # autolimit on
                    # autolimit set [amount] [interval]
                    if len(cmd) < 2:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.ctx.Config.SERVICE_NICKNAME} {command.upper()} ON")
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.ctx.Config.SERVICE_NICKNAME} {command.upper()} SET [AMOUNT] [INTERVAL]")
                        return None

                    arg = str(cmd[1]).lower()

                    match arg:
                        case 'on':
                            if self.mod_config.autolimit == 0:
                                await self.update_configuration('autolimit', 1)
                                self.autolimit_isRunning = True
                                self.ctx.Base.create_asynctask(thds.coro_autolimit(self), async_name='coro_autolimit')
                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[{self.ctx.Config.COLORS.green}AUTOLIMIT{self.ctx.Config.COLORS.nogc}] Activated", channel=self.ctx.Config.SERVICE_CHANLOG)
                            else:
                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[{self.ctx.Config.COLORS.red}AUTOLIMIT{self.ctx.Config.COLORS.nogc}] Already activated", channel=self.ctx.Config.SERVICE_CHANLOG)

                        case 'off':
                            if self.mod_config.autolimit == 1:
                                await self.update_configuration('autolimit', 0)
                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[{self.ctx.Config.COLORS.green}AUTOLIMIT{self.ctx.Config.COLORS.nogc}] Deactivated", channel=self.ctx.Config.SERVICE_CHANLOG)
                            else:
                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[{self.ctx.Config.COLORS.red}AUTOLIMIT{self.ctx.Config.COLORS.nogc}] Already Deactivated", channel=self.ctx.Config.SERVICE_CHANLOG)

                        case 'set':
                            amount = int(cmd[2])
                            interval = int(cmd[3])

                            await self.update_configuration('autolimit_amount', amount)
                            await self.update_configuration('autolimit_interval', interval)
                            await self.ctx.Irc.Protocol.send_priv_msg(
                                nick_from=dnickname,
                                msg=f"[{self.ctx.Config.COLORS.green}AUTOLIMIT{self.ctx.Config.COLORS.nogc}] Amount set to ({amount}) | Interval set to ({interval})", 
                                channel=self.ctx.Config.SERVICE_CHANLOG
                                )

                        case _:
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.ctx.Config.SERVICE_NICKNAME} {command.upper()} ON")
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.ctx.Config.SERVICE_NICKNAME} {command.upper()} SET [AMOUNT] [INTERVAL]")

                except Exception as err:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.ctx.Config.SERVICE_NICKNAME} {command.upper()} ON")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.ctx.Config.SERVICE_NICKNAME} {command.upper()} SET [AMOUNT] [INTERVAL]")
                    self.ctx.Logs.error(f"Value Error -> {err}")

            case 'reputation':
                # .reputation [on/off] --> activate or deactivate reputation system
                # .reputation set banallchan [on/off] --> activate or deactivate ban in all channel
                # .reputation set limit [xxxx] --> change the reputation threshold
                # .reputation release [nick]
                # .reputation [arg1] [arg2] [arg3]
                try:
                    len_cmd = len(cmd)
                    if len_cmd < 2:
                        raise IndexError("Showing help!")

                    activation = str(cmd[1]).lower()

                    # Nous sommes dans l'activation ON / OFF
                    if len_cmd == 2:
                        key = 'reputation'
                        if activation == 'on':

                            if self.mod_config.reputation == 1:
                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.ctx.Config.COLORS.green}REPUTATION{self.ctx.Config.COLORS.black} ] : Already activated", channel=dchanlog)
                                return None

                            await self.update_configuration(key, 1)
                            self.ctx.Base.create_asynctask(self.Threads.coro_apply_reputation_sanctions(self))

                            await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.ctx.Config.COLORS.green}REPUTATION{self.ctx.Config.COLORS.black} ] : Activated by {fromuser}", channel=dchanlog)

                            await self.ctx.Irc.Protocol.send_join_chan(uidornickname=dnickname, channel=jail_chan)
                            await self.ctx.Irc.Protocol.send2socket(f":{service_id} SAMODE {jail_chan} +{dumodes} {dnickname}")
                            await self.ctx.Irc.Protocol.send_set_mode(f'+{jail_chan_mode}', channel_name=jail_chan)

                            if self.mod_config.reputation_sg == 1:
                                for chan in self.ctx.Channel.UID_CHANNEL_DB:
                                    if chan.name != jail_chan:
                                        await self.ctx.Irc.Protocol.send_set_mode('+b', channel_name=chan.name, params='~security-group:unknown-users')
                                        await self.ctx.Irc.Protocol.send_set_mode(
                                            '+eee', 
                                            channel_name=chan.name, 
                                            params='~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users'
                                            )

                            await self.ctx.Channel.db_query_channel('add', self.module_name, jail_chan)

                        if activation == 'off':

                            if self.mod_config.reputation == 0:
                                await self.ctx.Irc.Protocol.send_priv_msg(
                                    nick_from=dnickname,
                                    msg=f"[ {self.ctx.Config.COLORS.green}REPUTATION{self.ctx.Config.COLORS.black} ] : Already deactivated",
                                    channel=dchanlog
                                    )
                                return False

                            await self.update_configuration(key, 0)
                            self.reputationTimer_isRunning = False

                            await self.ctx.Irc.Protocol.send_priv_msg(
                                    nick_from=dnickname,
                                    msg=f"[ {self.ctx.Config.COLORS.red}REPUTATION{self.ctx.Config.COLORS.black} ] : Deactivated by {fromuser}",
                                    channel=dchanlog
                                    )

                            await self.ctx.Irc.Protocol.send2socket(f":{service_id} SAMODE {jail_chan} -{dumodes} {dnickname}")
                            await self.ctx.Irc.Protocol.send_set_mode('-sS', channel_name=jail_chan)
                            await self.ctx.Irc.Protocol.send_part_chan(service_id, jail_chan)

                            for chan in self.ctx.Channel.UID_CHANNEL_DB:
                                if chan.name != jail_chan:
                                    await self.ctx.Irc.Protocol.send_set_mode('-b', channel_name=chan.name, params='~security-group:unknown-users')
                                    await self.ctx.Irc.Protocol.send_set_mode(
                                        '-eee', 
                                        channel_name=chan.name, 
                                        params='~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users'
                                        )

                            await self.ctx.Channel.db_query_channel('del', self.module_name, jail_chan)

                    if len_cmd == 3:
                        get_options = str(cmd[1]).lower()

                        match get_options:
                            case 'release':
                                # .reputation release [nick]
                                link = self.ctx.Config.SERVEUR_LINK
                                jailed_salon = self.ctx.Config.SALON_JAIL
                                welcome_salon = self.ctx.Config.SALON_LIBERER
                                client_obj = self.ctx.User.get_user(str(cmd[2]))

                                if self.mod_config.reputation != 1:
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,
                                                  nick_to=fromuser,
                                                  msg="The reputation system is not activated!")
                                    return None

                                if client_obj is None:
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,
                                                  nick_to=fromuser,
                                                  msg=f"This nickname ({str(cmd[2])}) is not connected to the network!")
                                    return None

                                client_to_release = self.ctx.Reputation.get_reputation(client_obj.uid)

                                if client_to_release is None:
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,
                                                  nick_to=fromuser, msg=f"This nickname ({str(cmd[2])}) doesn't exist in the reputation databalse!")
                                    return None

                                if self.ctx.Reputation.delete(client_to_release.uid):
                                    await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.green}REPUTATION RELEASE{self.ctx.Config.COLORS.black} ] : {client_to_release.nickname} has been released",
                                                channel=dchanlog)
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,
                                                  nick_to=fromuser, msg=f"This nickname has been released from reputation system")
                                    
                                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname,
                                                  nick_to=client_to_release.nickname, msg=f"You have been released from the reputation system by ({fromuser})")
                                    
                                    await self.ctx.Irc.Protocol.send_sapart(nick_to_sapart=client_to_release.nickname, channel_name=jailed_salon)
                                    await self.ctx.Irc.Protocol.send_sajoin(nick_to_sajoin=client_to_release.nickname, channel_name=welcome_salon)
                                    await self.ctx.Irc.Protocol.send2socket(f":{link} REPUTATION {client_to_release.remote_ip} {self.mod_config.reputation_score_after_release}")
                                    return None
                                else:
                                    await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.red}REPUTATION RELEASE ERROR{self.ctx.Config.COLORS.black} ] : "
                                                f"{client_to_release.nickname} has not been released! as he is not in the reputation database",
                                                channel=dchanlog
                                            )
                    if len_cmd > 4:
                        get_set = str(cmd[1]).lower()

                        if get_set != 'set':
                            raise IndexError('Showing help')

                        get_options = str(cmd[2]).lower()

                        match get_options:
                            
                            case 'banallchan':
                                key = 'reputation_ban_all_chan'
                                get_value = str(cmd[3]).lower()
                                if get_value == 'on':

                                    if self.mod_config.reputation_ban_all_chan == 1:
                                        await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.red}BAN ON ALL CHANS{self.ctx.Config.COLORS.black} ] : Already activated",
                                                channel=dchanlog
                                            )
                                        return False

                                    # self.update_db_configuration(key, 1)
                                    await self.update_configuration(key, 1)

                                    await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.green}BAN ON ALL CHANS{self.ctx.Config.COLORS.black} ] : Activated by {fromuser}",
                                                channel=dchanlog
                                            )

                                elif get_value == 'off':
                                    if self.mod_config.reputation_ban_all_chan == 0:
                                        await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.red}BAN ON ALL CHANS{self.ctx.Config.COLORS.black} ] : Already deactivated",
                                                channel=dchanlog
                                            )
                                        return False

                                    # self.update_db_configuration(key, 0)
                                    await self.update_configuration(key, 0)

                                    await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.green}BAN ON ALL CHANS{self.ctx.Config.COLORS.black} ] : Deactivated by {fromuser}",
                                                channel=dchanlog
                                            )

                            case 'limit':
                                reputation_seuil = int(cmd[3])
                                key = 'reputation_seuil'

                                # self.update_db_configuration(key, reputation_seuil)
                                await self.update_configuration(key, reputation_seuil)

                                await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.green}REPUTATION SEUIL{self.ctx.Config.COLORS.black} ] : Limit set to {str(reputation_seuil)} by {fromuser}",
                                                channel=dchanlog
                                            )
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Reputation set to {reputation_seuil}")

                            case 'timer':
                                reputation_timer = int(cmd[3])
                                key = 'reputation_timer'
                                await self.update_configuration(key, reputation_timer)

                                await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.green}REPUTATION TIMER{self.ctx.Config.COLORS.black} ] : Timer set to {str(reputation_timer)} minute(s) by {fromuser}",
                                                channel=dchanlog
                                            )
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Reputation set to {reputation_timer}")

                            case 'score_after_release':
                                reputation_score_after_release = int(cmd[3])
                                key = 'reputation_score_after_release'
                                await self.update_configuration(key, reputation_score_after_release)

                                await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.green}REPUTATION SCORE AFTER RELEASE{self.ctx.Config.COLORS.black} ] : Reputation score after release set to {str(reputation_score_after_release)} by {fromuser}",
                                                channel=dchanlog
                                            )
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Reputation score after release set to {reputation_score_after_release}")

                            case 'security_group':
                                reputation_sg = int(cmd[3])
                                key = 'reputation_sg'
                                await self.update_configuration(key, reputation_sg)

                                await self.ctx.Irc.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.ctx.Config.COLORS.green}REPUTATION SECURITY-GROUP{self.ctx.Config.COLORS.black} ] : Reputation Security-group set to {str(reputation_sg)} by {fromuser}",
                                                channel=dchanlog
                                            )
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Reputation score after release set to {reputation_sg}")

                            case _:
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation [ON/OFF]")
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation release [nickname]")
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set banallchan [ON/OFF]")
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set limit [1234]")
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set score_after_release [1234]")
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set timer [1234]")
                                await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set action [kill|None]")

                except IndexError as ie:
                    self.ctx.Logs.warning(f'{ie}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation [ON/OFF]")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation release [nickname]")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set banallchan [ON/OFF]")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set limit [1234]")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set score_after_release [1234]")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set timer [1234]")
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set action [kill|None]")

                except ValueError as ve:
                    self.ctx.Logs.warning(f'{ve}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=" La valeur devrait etre un entier >= 0")

            case 'proxy_scan':

                # .proxy_scan set local_scan on/off          --> Va activer le scan des ports
                # .proxy_scan set psutil_scan on/off         --> Active les informations de connexion a la machine locale
                # .proxy_scan set abuseipdb_scan on/off      --> Active le scan via l'api abuseipdb
                len_cmd = len(cmd)

                if len_cmd == 4:
                    set_key = str(cmd[1]).lower()

                    if set_key != 'set':
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')

                    option = str(cmd[2]).lower() # => local_scan, psutil_scan, abuseipdb_scan
                    action = str(cmd[3]).lower() # => on / off

                    match option:
                        case 'local_scan':
                            if action == 'on':
                                if self.mod_config.local_scan == 1:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.ctx.Base.create_asynctask(self.Threads.coro_local_scan(self))
                                await self.update_configuration(option, 1)

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.mod_config.local_scan == 0:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                await self.update_configuration(option, 0)
                                self.localscan_isRunning = False

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case 'psutil_scan':
                            if action == 'on':
                                if self.mod_config.psutil_scan == 1:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.ctx.Base.create_asynctask(self.Threads.coro_psutil_scan(self))
                                await self.update_configuration(option, 1)

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.mod_config.psutil_scan == 0:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                await self.update_configuration(option, 0)
                                self.psutil_isRunning = False

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case 'abuseipdb_scan':
                            if action == 'on':
                                if self.mod_config.abuseipdb_scan == 1:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.ctx.Base.create_asynctask(self.Threads.coro_abuseipdb_scan(self))
                                await self.update_configuration(option, 1)

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.mod_config.abuseipdb_scan == 0:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                await self.update_configuration(option, 0)
                                self.abuseipdb_isRunning = False

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case 'freeipapi_scan':
                            if action == 'on':
                                if self.mod_config.freeipapi_scan == 1:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.ctx.Base.create_asynctask(self.Threads.coro_freeipapi_scan(self))
                                await self.update_configuration(option, 1)

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.mod_config.freeipapi_scan == 0:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                await self.update_configuration(option, 0)
                                self.freeipapi_isRunning = False

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case 'cloudfilt_scan':
                            if action == 'on':
                                if self.mod_config.cloudfilt_scan == 1:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.ctx.Base.create_asynctask(self.Threads.coro_cloudfilt_scan(self))
                                await self.update_configuration(option, 1)

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.mod_config.cloudfilt_scan == 0:
                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                await self.update_configuration(option, 0)
                                self.cloudfilt_isRunning = False

                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case _:
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                            await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')
                else:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')

            case 'flood':
                # .flood on/off
                # .flood set flood_message 5
                # .flood set flood_time 1
                # .flood set flood_timer 20
                try:
                    len_cmd = len(cmd)

                    if len_cmd == 2:
                        activation = str(cmd[1]).lower()
                        key = 'flood'
                        if activation == 'on':
                            if self.mod_config.flood == 1:
                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.ctx.Config.COLORS.green}FLOOD{self.ctx.Config.COLORS.black} ] : Already activated", channel=dchanlog)
                                return False

                            await self.update_configuration(key, 1)

                            await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.ctx.Config.COLORS.green}FLOOD{self.ctx.Config.COLORS.black} ] : Activated by {fromuser}", channel=dchanlog)

                        if activation == 'off':
                            if self.mod_config.flood == 0:
                                await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.ctx.Config.COLORS.red}FLOOD{self.ctx.Config.COLORS.black} ] : Already Deactivated", channel=dchanlog)
                                return False

                            await self.update_configuration(key, 0)

                            await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.ctx.Config.COLORS.green}FLOOD{self.ctx.Config.COLORS.black} ] : Deactivated by {fromuser}", channel=dchanlog)

                    if len_cmd == 4:
                        set_key = str(cmd[2]).lower()

                        if str(cmd[1]).lower() == 'set':
                            match set_key:
                                case 'flood_message':
                                    key = 'flood_message'
                                    set_value = int(cmd[3])
                                    await self.update_configuration(key, set_value)

                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, 
                                                              msg=f"[ {self.ctx.Config.COLORS.green}FLOOD{self.ctx.Config.COLORS.black} ] : Flood message set to {set_value} by {fromuser}", 
                                                              channel=dchanlog)

                                case 'flood_time':
                                    key = 'flood_time'
                                    set_value = int(cmd[3])
                                    await self.update_configuration(key, set_value)

                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, 
                                                              msg=f"[ {self.ctx.Config.COLORS.green}FLOOD{self.ctx.Config.COLORS.black} ] : Flood time set to {set_value} by {fromuser}", 
                                                              channel=dchanlog)

                                case 'flood_timer':
                                    key = 'flood_timer'
                                    set_value = int(cmd[3])
                                    await self.update_configuration(key, set_value)

                                    await self.ctx.Irc.Protocol.send_priv_msg(nick_from=dnickname, 
                                                              msg=f"[ {self.ctx.Config.COLORS.green}FLOOD{self.ctx.Config.COLORS.black} ] : Flood timer set to {set_value} by {fromuser}", 
                                                              channel=dchanlog)

                                case _:
                                    pass

                except ValueError as ve:
                    self.ctx.Logs.error(f"{self.__class__.__name__} Value Error : {ve}")

            case 'status':
                color_green = self.ctx.Config.COLORS.green
                color_red = self.ctx.Config.COLORS.red
                color_black = self.ctx.Config.COLORS.black
                nogc = self.ctx.Config.COLORS.nogc
                try:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' [{color_green if self.mod_config.reputation == 1 else color_red}Reputation{nogc}]                           ==> {self.mod_config.reputation}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'           reputation_seuil             ==> {self.mod_config.reputation_seuil}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'           reputation_after_release     ==> {self.mod_config.reputation_score_after_release}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'           reputation_ban_all_chan      ==> {self.mod_config.reputation_ban_all_chan}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'           reputation_timer             ==> {self.mod_config.reputation_timer}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=' [Proxy_scan]')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.mod_config.local_scan == 1 else color_red}local_scan{nogc}                 ==> {self.mod_config.local_scan}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.mod_config.psutil_scan == 1 else color_red}psutil_scan{nogc}                ==> {self.mod_config.psutil_scan}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.mod_config.abuseipdb_scan == 1 else color_red}abuseipdb_scan{nogc}             ==> {self.mod_config.abuseipdb_scan}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.mod_config.freeipapi_scan == 1 else color_red}freeipapi_scan{nogc}             ==> {self.mod_config.freeipapi_scan}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.mod_config.cloudfilt_scan == 1 else color_red}cloudfilt_scan{nogc}             ==> {self.mod_config.cloudfilt_scan}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' [{color_green if self.mod_config.autolimit == 1 else color_red}Autolimit{nogc}]                            ==> {self.mod_config.autolimit}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.mod_config.autolimit == 1 else color_red}Autolimit Amount{nogc}           ==> {self.mod_config.autolimit_amount}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.mod_config.autolimit == 1 else color_red}Autolimit Interval{nogc}         ==> {self.mod_config.autolimit_interval}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' [{color_green if self.mod_config.flood == 1 else color_red}Flood{nogc}]                                ==> {self.mod_config.flood}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg='      flood_action                      ==> Coming soon')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'      flood_message                     ==> {self.mod_config.flood_message}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'      flood_time                        ==> {self.mod_config.flood_time}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'      flood_timer                       ==> {self.mod_config.flood_timer}')
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' [{color_green if self.mod_config.flood == 1 else color_red}Sentinel{nogc}]                             ==> {self.mod_config.sentinel}')
                except KeyError as ke:
                    self.ctx.Logs.error(f"Key Error : {ke}")

            case 'info':
                try:
                    if len(cmd) < 2:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Syntax. /msg {dnickname} INFO [nickname]")
                        return None

                    nickoruid = cmd[1]
                    UserObject = self.ctx.User.get_user(nickoruid)

                    if UserObject is not None:
                        channels: list = [chan.name for chan in self.ctx.Channel.UID_CHANNEL_DB for uid_in_chan in chan.uids if self.ctx.User.clean_uid(uid_in_chan) == UserObject.uid]

                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' UID              : {UserObject.uid}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' NICKNAME         : {UserObject.nickname}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' USERNAME         : {UserObject.username}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' REALNAME         : {UserObject.realname}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' HOSTNAME         : {UserObject.hostname}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' VHOST            : {UserObject.vhost}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' IP               : {UserObject.remote_ip}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Country          : {UserObject.geoip}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' WebIrc           : {UserObject.isWebirc}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' WebWebsocket     : {UserObject.isWebsocket}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' REPUTATION       : {UserObject.score_connexion}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' MODES            : {UserObject.umodes}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' CHANNELS         : {", ".join(channels)}')
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' CONNECTION TIME  : {UserObject.connexion_datetime}')
                    else:
                        await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"This user {nickoruid} doesn't exist")

                except KeyError as ke:
                    self.ctx.Logs.warning(f"Key error info user : {ke}")

            case 'sentinel':
                # .sentinel on
                if len(cmd) < 2:
                    await self.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Syntax. /msg {dnickname} sentinel [ON | OFF]")
                    return None

                activation = str(cmd[1]).lower()
                channel_to_dont_quit = [self.ctx.Config.SALON_JAIL, self.ctx.Config.SERVICE_CHANLOG]

                if activation == 'on':
                    result = await self.ctx.Base.db_execute_query(f"SELECT distinct channel_name FROM {self.ctx.Config.TABLE_CHANNEL}")
                    channels = result.fetchall()
                    channel_in_db = [channel[0] for channel in channels]
                    channel_to_dont_quit.extend(channel_in_db)

                    await self.update_configuration('sentinel', 1)
                    for chan in self.ctx.Channel.UID_CHANNEL_DB:
                        if chan.name not in channel_to_dont_quit:
                            await self.ctx.Irc.Protocol.send_join_chan(uidornickname=dnickname, channel=chan.name)
                            await self.ctx.Irc.Protocol.send_priv_msg(dnickname, f"Sentinel mode activated on {channel}", channel=chan.name)
                    await self.ctx.Irc.Protocol.send_priv_msg(dnickname, f"[ {color_green}SENTINEL{color_nogc} ] Activated by {fromuser}", channel=self.ctx.Config.SERVICE_CHANLOG)
                    return None

                if activation == 'off':
                    result = await self.ctx.Base.db_execute_query(f"SELECT distinct channel_name FROM {self.ctx.Config.TABLE_CHANNEL}")
                    channels = result.fetchall()
                    channel_in_db = [channel[0] for channel in channels]
                    channel_to_dont_quit.extend(channel_in_db)
                    await self.update_configuration('sentinel', 0)
                    for chan in self.ctx.Channel.UID_CHANNEL_DB:
                        if chan.name not in channel_to_dont_quit:
                            await self.ctx.Irc.Protocol.send_part_chan(uidornickname=dnickname, channel=chan.name)
                            await self.ctx.Irc.Protocol.send_priv_msg(dnickname, f"Sentinel mode deactivated on {channel}", channel=chan.name)

                    await self.join_saved_channels()
                    await self.ctx.Irc.Protocol.send_priv_msg(dnickname, f"[ {color_red}SENTINEL{color_nogc} ] Deactivated by {fromuser}", channel=self.ctx.Config.SERVICE_CHANLOG)
                    return None

            case _:
                pass