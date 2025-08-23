import traceback
import mods.defender.schemas as schemas
import mods.defender.utils as utils
import mods.defender.threads as thds
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.irc import Irc

class Defender:

    def __init__(self, irc_instance: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = irc_instance

        # Add Loader Object to the module (Mandatory)
        self.Loader = irc_instance.Loader

        # Add server protocol Object to the module (Mandatory)
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

        # Add Settings object to save objects when reloading modules (Mandatory)
        self.Settings = irc_instance.Settings

        # Add Reputation object to the module (Optional)
        self.Reputation = irc_instance.Reputation

        # Add module schemas
        self.Schemas = schemas

        # Add utils functions
        self.Utils = utils

        # Create module commands (Mandatory)
        self.Irc.build_command(0, self.module_name, 'code', 'Display the code or key for access')
        self.Irc.build_command(1, self.module_name, 'info', 'Provide information about the channel or server')
        self.Irc.build_command(1, self.module_name, 'autolimit', 'Automatically set channel user limits')
        self.Irc.build_command(3, self.module_name, 'reputation', 'Check or manage user reputation')
        self.Irc.build_command(3, self.module_name, 'proxy_scan', 'Scan users for proxy connections')
        self.Irc.build_command(3, self.module_name, 'flood', 'Handle flood detection and mitigation')
        self.Irc.build_command(3, self.module_name, 'status', 'Check the status of the server or bot')
        self.Irc.build_command(3, self.module_name, 'timer', 'Set or manage timers')
        self.Irc.build_command(3, self.module_name, 'show_reputation', 'Display reputation information')
        self.Irc.build_command(3, self.module_name, 'sentinel', 'Monitor and guard the channel or server')

        # Init the module (Mandatory)
        self.__init_module()

        # Log the module
        self.Logs.debug(f'-- Module {self.module_name} V2 loaded ...')

    def __init_module(self) -> None:

        # Create you own tables if needed (Mandatory)
        self.__create_tables()

        # Load module configuration (Mandatory)
        self.__load_module_configuration()
        # End of mandatory methods you can start your customization #

        self.timeout = self.Config.API_TIMEOUT

        # Listes qui vont contenir les ip a scanner avec les différentes API
        self.Schemas.DB_ABUSEIPDB_USERS = []
        self.Schemas.DB_FREEIPAPI_USERS = []
        self.Schemas.DB_CLOUDFILT_USERS = []
        self.Schemas.DB_PSUTIL_USERS = []
        self.Schemas.DB_LOCALSCAN_USERS = []

        # Variables qui indique que les threads sont en cours d'éxecutions
        self.abuseipdb_isRunning:bool       = True
        self.freeipapi_isRunning:bool       = True
        self.cloudfilt_isRunning:bool       = True
        self.psutil_isRunning:bool          = True
        self.localscan_isRunning:bool       = True
        self.reputationTimer_isRunning:bool = True
        self.autolimit_isRunning: bool      = True

        # Variable qui va contenir les users
        self.flood_system = {}

        # Contient les premieres informations de connexion
        self.reputation_first_connexion = {'ip': '', 'score': -1}

        # Laisser vide si aucune clé
        self.abuseipdb_key = '13c34603fee4d2941a2c443cc5c77fd750757ca2a2c1b304bd0f418aff80c24be12651d1a3cfe674'
        self.cloudfilt_key = 'r1gEtjtfgRQjtNBDMxsg'

        # Démarrer les threads pour démarrer les api
        self.Base.create_thread(func=thds.thread_freeipapi_scan, func_args=(self, ))
        self.Base.create_thread(func=thds.thread_cloudfilt_scan, func_args=(self, ))
        self.Base.create_thread(func=thds.thread_abuseipdb_scan, func_args=(self, ))
        self.Base.create_thread(func=thds.thread_local_scan, func_args=(self, ))
        self.Base.create_thread(func=thds.thread_psutil_scan, func_args=(self, ))

        self.Base.create_thread(func=thds.thread_apply_reputation_sanctions, func_args=(self, ))

        if self.ModConfig.autolimit == 1:
            self.Base.create_thread(func=thds.thread_autolimit, func_args=(self, ))

        if self.ModConfig.reputation == 1:
            self.Protocol.send_sjoin(self.Config.SALON_JAIL)
            self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} SAMODE {self.Config.SALON_JAIL} +o {self.Config.SERVICE_NICKNAME}")

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
        # Variable qui va contenir les options de configuration du module Defender
        self.ModConfig = self.Schemas.ModConfModel()

        # Sync the configuration with core configuration (Mandatory)
        self.Base.db_sync_core_config(self.module_name, self.ModConfig)

        return None

    def __update_configuration(self, param_key: str, param_value: str):

        self.Base.db_update_core_config(self.module_name, self.ModConfig, param_key, param_value)

    def __onload(self):

        abuseipdb = self.Settings.get_cache('ABUSEIPDB')
        freeipapi = self.Settings.get_cache('FREEIPAPI')
        cloudfilt = self.Settings.get_cache('CLOUDFILT')
        psutils = self.Settings.get_cache('PSUTIL')
        localscan = self.Settings.get_cache('LOCALSCAN')

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

    def unload(self) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """
        self.Settings.set_cache('ABUSEIPDB', self.Schemas.DB_ABUSEIPDB_USERS)
        self.Settings.set_cache('FREEIPAPI', self.Schemas.DB_FREEIPAPI_USERS)
        self.Settings.set_cache('CLOUDFILT', self.Schemas.DB_CLOUDFILT_USERS)
        self.Settings.set_cache('PSUTIL', self.Schemas.DB_PSUTIL_USERS)
        self.Settings.set_cache('LOCALSCAN', self.Schemas.DB_LOCALSCAN_USERS)

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

        return None

    def insert_db_trusted(self, uid: str, nickname:str) -> None:

        uid = self.User.get_uid(uid)
        nickname = self.User.get_nickname(nickname)

        query = "SELECT id FROM def_trusted WHERE user = ?"
        exec_query = self.Base.db_execute_query(query, {"user": nickname})
        response = exec_query.fetchone()

        if response is not None:
            q_insert = "INSERT INTO def_trusted (datetime, user, host, vhost) VALUES (?, ?, ?, ?)"
            mes_donnees = {'datetime': self.Base.get_datetime(), 'user': nickname, 'host': '*', 'vhost': '*'}
            exec_query = self.Base.db_execute_query(q_insert, mes_donnees)
            pass

    def join_saved_channels(self) -> None:
        """_summary_
        """
        try:
            result = self.Base.db_execute_query(f"SELECT distinct channel_name FROM {self.Config.TABLE_CHANNEL}")
            channels = result.fetchall()
            jail_chan = self.Config.SALON_JAIL
            jail_chan_mode = self.Config.SALON_JAIL_MODES
            service_id = self.Config.SERVICE_ID
            dumodes = self.Config.SERVICE_UMODES
            dnickname = self.Config.SERVICE_NICKNAME

            for channel in channels:
                chan = channel[0]
                self.Protocol.send_sjoin(chan)
                if chan == jail_chan:
                    self.Protocol.send2socket(f":{service_id} SAMODE {jail_chan} +{dumodes} {dnickname}")
                    self.Protocol.send2socket(f":{service_id} MODE {jail_chan} +{jail_chan_mode}")

            return None

        except Exception as err:
            self.Logs.error(f"General Error: {err}")

    def run_db_action_timer(self, wait_for: float = 0) -> None:

        query = f"SELECT param_key FROM {self.Config.TABLE_CONFIG}"
        res = self.Base.db_execute_query(query)
        service_id = self.Config.SERVICE_ID
        dchanlog = self.Config.SERVICE_CHANLOG

        for param in res.fetchall():
            if param[0] == 'reputation':
                self.Protocol.send_priv_msg(
                    nick_from=service_id,
                    msg=f" ===> {param[0]}",
                    channel=dchanlog
                )
            else:
                self.Protocol.send_priv_msg(
                    nick_from=service_id,
                    msg=f"{param[0]}",
                    channel=dchanlog
                )

        return None

    def cmd(self, data: list[str]) -> None:

        if not data or len(data) < 2:
            return None
        cmd = data.copy() if isinstance(data, list) else list(data).copy()

        try:
            index, command = self.Irc.Protocol.get_ircd_protocol_poisition(cmd)
            if index == -1:
                return None

            match command:

                case 'REPUTATION':
                    self.Utils.handle_on_reputation(self, cmd)
                    return None

                case 'MODE':
                    self.Utils.handle_on_mode(self, cmd)
                    return None

                case 'PRIVMSG':
                    self.Utils.handle_on_privmsg(self, cmd)
                    return None

                case 'UID':
                    self.Utils.handle_on_uid(self, cmd)
                    return None

                case 'SJOIN':

                    self.Utils.handle_on_sjoin(self, cmd)
                    return None

                case 'SLOG':
                    self.Utils.handle_on_slog(self, cmd)
                    return None

                case 'NICK':
                    self.Utils.handle_on_nick(self, cmd)
                    return None

                case 'QUIT':
                    self.Utils.handle_on_quit(self, cmd)
                    return None

                case _:
                    return None

        except KeyError as ke:
            self.Logs.error(f"{ke} / {cmd} / length {str(len(cmd))}")
        except IndexError as ie:
            self.Logs.error(f"{ie} / {cmd} / length {str(len(cmd))}")
        except Exception as err:
            self.Logs.error(f"General Error: {err}")
            traceback.print_exc()

    def hcmds(self, user:str, channel: any, cmd: list, fullcmd: list = []) -> None:

        command = str(cmd[0]).lower()
        fromuser = user
        channel = fromchannel = channel if self.Channel.is_valid_channel(channel) else None

        dnickname = self.Config.SERVICE_NICKNAME            # Defender nickname
        dchanlog = self.Config.SERVICE_CHANLOG              # Defender chan log
        dumodes = self.Config.SERVICE_UMODES                # Les modes de Defender
        service_id = self.Config.SERVICE_ID                 # Defender serveur id
        jail_chan = self.Config.SALON_JAIL                  # Salon pot de miel
        jail_chan_mode = self.Config.SALON_JAIL_MODES       # Mode du salon "pot de miel"

        match command:

            case 'timer':
                try:
                    timer_sent = self.Base.int_if_possible(cmd[1])
                    timer_sent = int(timer_sent)
                    self.Base.create_timer(timer_sent, self.run_db_action_timer)

                except TypeError as te:
                    self.Logs.error(f"Type Error -> {te}")
                except ValueError as ve:
                    self.Logs.error(f"Value Error -> {ve}")

            case 'show_reputation':

                if not self.Reputation.UID_REPUTATION_DB:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="No one is suspected")

                for suspect in self.Reputation.UID_REPUTATION_DB:
                    self.Protocol.send_notice(nick_from=dnickname, 
                                             nick_to=fromuser, 
                                             msg=f" Uid: {suspect.uid} | Nickname: {suspect.nickname} | Reputation: {suspect.score_connexion} | Secret code: {suspect.secret_code} | Connected on: {suspect.connexion_datetime}")

            case 'code':
                try:
                    release_code = cmd[1]
                    jailed_nickname = self.User.get_nickname(fromuser)
                    jailed_UID = self.User.get_uid(fromuser)
                    get_reputation = self.Reputation.get_Reputation(jailed_UID)

                    if get_reputation is None:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=" No code is requested ...")
                        return False

                    jailed_IP = get_reputation.remote_ip
                    jailed_salon = self.Config.SALON_JAIL
                    reputation_seuil = self.ModConfig.reputation_seuil
                    welcome_salon = self.Config.SALON_LIBERER

                    self.Logs.debug(f"IP de {jailed_nickname} : {jailed_IP}")
                    link = self.Config.SERVEUR_LINK
                    color_green = self.Config.COLORS.green
                    color_black = self.Config.COLORS.black

                    if release_code == get_reputation.secret_code:
                        self.Protocol.send_priv_msg(nick_from=dnickname, msg="Bon mot de passe. Allez du vent !", channel=jailed_salon)

                        if self.ModConfig.reputation_ban_all_chan == 1:
                            for chan in self.Channel.UID_CHANNEL_DB:
                                if chan.name != jailed_salon:
                                    self.Protocol.send2socket(f":{service_id} MODE {chan.name} -b {jailed_nickname}!*@*")

                        self.Reputation.delete(jailed_UID)
                        self.Logs.debug(f'{jailed_UID} - {jailed_nickname} removed from REPUTATION_DB')
                        self.Protocol.send_sapart(nick_to_sapart=jailed_nickname, channel_name=jailed_salon)
                        self.Protocol.send_sajoin(nick_to_sajoin=jailed_nickname, channel_name=welcome_salon)
                        self.Protocol.send2socket(f":{link} REPUTATION {jailed_IP} {self.ModConfig.reputation_score_after_release}")
                        self.User.get_user(jailed_UID).score_connexion = reputation_seuil + 1
                        self.Protocol.send_priv_msg(nick_from=dnickname,
                                                  msg=f"[{color_green} MOT DE PASS CORRECT {color_black}] : You have now the right to enjoy the network !", 
                                                  nick_to=jailed_nickname)

                    else:
                        self.Protocol.send_priv_msg(
                                nick_from=dnickname,
                                msg="Mauvais password", 
                                channel=jailed_salon
                            )
                        self.Protocol.send_priv_msg(
                                nick_from=dnickname,
                                msg=f"[{color_green} MAUVAIS PASSWORD {color_black}] You have typed a wrong code. for recall your password is: {self.Config.SERVICE_PREFIX}code {get_reputation.secret_code}",
                                nick_to=jailed_nickname
                            )

                except IndexError as ie:
                    self.Logs.error(f'Index Error: {ie}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} code [code]")
                except KeyError as ke:
                    self.Logs.error(f'_hcmd code: KeyError {ke}')

            case 'autolimit':
                try:
                    # autolimit on
                    # autolimit set [amount] [interval]
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.Config.SERVICE_NICKNAME} {command.upper()} ON")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.Config.SERVICE_NICKNAME} {command.upper()} SET [AMOUNT] [INTERVAL]")
                        return None

                    arg = str(cmd[1]).lower()

                    match arg:
                        case 'on':
                            if self.ModConfig.autolimit == 0:
                                self.__update_configuration('autolimit', 1)
                                self.autolimit_isRunning = True
                                self.Base.create_thread(func=thds.thread_autolimit, func_args=(self, ))
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[{self.Config.COLORS.green}AUTOLIMIT{self.Config.COLORS.nogc}] Activated", channel=self.Config.SERVICE_CHANLOG)
                            else:
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[{self.Config.COLORS.red}AUTOLIMIT{self.Config.COLORS.nogc}] Already activated", channel=self.Config.SERVICE_CHANLOG)

                        case 'off':
                            if self.ModConfig.autolimit == 1:
                                self.__update_configuration('autolimit', 0)
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[{self.Config.COLORS.green}AUTOLIMIT{self.Config.COLORS.nogc}] Deactivated", channel=self.Config.SERVICE_CHANLOG)
                            else:
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[{self.Config.COLORS.red}AUTOLIMIT{self.Config.COLORS.nogc}] Already Deactivated", channel=self.Config.SERVICE_CHANLOG)

                        case 'set':
                            amount = int(cmd[2])
                            interval = int(cmd[3])

                            self.__update_configuration('autolimit_amount', amount)
                            self.__update_configuration('autolimit_interval', interval)
                            self.Protocol.send_priv_msg(
                                nick_from=dnickname,
                                msg=f"[{self.Config.COLORS.green}AUTOLIMIT{self.Config.COLORS.nogc}] Amount set to ({amount}) | Interval set to ({interval})", 
                                channel=self.Config.SERVICE_CHANLOG
                                )

                        case _:
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.Config.SERVICE_NICKNAME} {command.upper()} ON")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.Config.SERVICE_NICKNAME} {command.upper()} SET [AMOUNT] [INTERVAL]")

                except Exception as err:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.Config.SERVICE_NICKNAME} {command.upper()} ON")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {self.Config.SERVICE_NICKNAME} {command.upper()} SET [AMOUNT] [INTERVAL]")
                    self.Logs.error(f"Value Error -> {err}")

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

                            if self.ModConfig.reputation == 1:
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.Config.COLORS.green}REPUTATION{self.Config.COLORS.black} ] : Already activated", channel=dchanlog)
                                return False

                            # self.update_db_configuration('reputation', 1)
                            self.__update_configuration(key, 1)

                            self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.Config.COLORS.green}REPUTATION{self.Config.COLORS.black} ] : Activated by {fromuser}", channel=dchanlog)

                            self.Protocol.send_join_chan(uidornickname=dnickname, channel=jail_chan)
                            self.Protocol.send2socket(f":{service_id} SAMODE {jail_chan} +{dumodes} {dnickname}")
                            self.Protocol.send2socket(f":{service_id} MODE {jail_chan} +{jail_chan_mode}")

                            if self.ModConfig.reputation_sg == 1:
                                for chan in self.Channel.UID_CHANNEL_DB:
                                    if chan.name != jail_chan:
                                        self.Protocol.send2socket(f":{service_id} MODE {chan.name} +b ~security-group:unknown-users")
                                        self.Protocol.send2socket(f":{service_id} MODE {chan.name} +eee ~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users")

                            self.Channel.db_query_channel('add', self.module_name, jail_chan)

                        if activation == 'off':

                            if self.ModConfig.reputation == 0:
                                self.Protocol.send_priv_msg(
                                    nick_from=dnickname,
                                    msg=f"[ {self.Config.COLORS.green}REPUTATION{self.Config.COLORS.black} ] : Already deactivated",
                                    channel=dchanlog
                                    )
                                return False

                            self.__update_configuration(key, 0)

                            self.Protocol.send_priv_msg(
                                    nick_from=dnickname,
                                    msg=f"[ {self.Config.COLORS.red}REPUTATION{self.Config.COLORS.black} ] : Deactivated by {fromuser}",
                                    channel=dchanlog
                                    )
                            self.Protocol.send2socket(f":{service_id} SAMODE {jail_chan} -{dumodes} {dnickname}")
                            self.Protocol.send2socket(f":{service_id} MODE {jail_chan} -sS")
                            self.Protocol.send2socket(f":{service_id} PART {jail_chan}")

                            for chan in self.Channel.UID_CHANNEL_DB:
                                if chan.name != jail_chan:
                                    self.Protocol.send2socket(f":{service_id} MODE {chan.name} -b ~security-group:unknown-users")
                                    self.Protocol.send2socket(f":{service_id} MODE {chan.name} -eee ~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users")

                            self.Channel.db_query_channel('del', self.module_name, jail_chan)

                    if len_cmd == 3:
                        get_options = str(cmd[1]).lower()

                        match get_options:
                            case 'release':
                                # .reputation release [nick]
                                p = self.Protocol
                                link = self.Config.SERVEUR_LINK
                                jailed_salon = self.Config.SALON_JAIL
                                welcome_salon = self.Config.SALON_LIBERER
                                client_obj = self.User.get_user(str(cmd[2]))

                                if client_obj is None:
                                    p.send_notice(nick_from=dnickname,
                                                  nick_to=fromuser,
                                                  msg=f"This nickname ({str(cmd[2])}) is not connected to the network!")
                                    return None

                                client_to_release = self.Reputation.get_Reputation(client_obj.uid)

                                if client_to_release is None:
                                    p.send_notice(nick_from=dnickname,
                                                  nick_to=fromuser, msg=f"This nickname ({str(cmd[2])}) doesn't exist in the reputation databalse!")
                                    return None

                                if self.Reputation.delete(client_to_release.uid):
                                    p.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.green}REPUTATION RELEASE{self.Config.COLORS.black} ] : {client_to_release.nickname} has been released",
                                                channel=dchanlog)
                                    p.send_notice(nick_from=dnickname,
                                                  nick_to=fromuser, msg=f"This nickname has been released from reputation system")
                                    
                                    p.send_notice(nick_from=dnickname,
                                                  nick_to=client_to_release.nickname, msg=f"You have been released from the reputation system by ({fromuser})")
                                    
                                    p.send_sapart(nick_to_sapart=client_to_release.nickname, channel_name=jailed_salon)
                                    p.send_sajoin(nick_to_sajoin=client_to_release.nickname, channel_name=welcome_salon)
                                    p.send2socket(f":{link} REPUTATION {client_to_release.remote_ip} {self.ModConfig.reputation_score_after_release}")
                                    return None
                                else:
                                    p.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.red}REPUTATION RELEASE ERROR{self.Config.COLORS.black} ] : "
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

                                    if self.ModConfig.reputation_ban_all_chan == 1:
                                        self.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.red}BAN ON ALL CHANS{self.Config.COLORS.black} ] : Already activated",
                                                channel=dchanlog
                                            )
                                        return False

                                    # self.update_db_configuration(key, 1)
                                    self.__update_configuration(key, 1)

                                    self.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.green}BAN ON ALL CHANS{self.Config.COLORS.black} ] : Activated by {fromuser}",
                                                channel=dchanlog
                                            )

                                elif get_value == 'off':
                                    if self.ModConfig.reputation_ban_all_chan == 0:
                                        self.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.red}BAN ON ALL CHANS{self.Config.COLORS.black} ] : Already deactivated",
                                                channel=dchanlog
                                            )
                                        return False

                                    # self.update_db_configuration(key, 0)
                                    self.__update_configuration(key, 0)

                                    self.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.green}BAN ON ALL CHANS{self.Config.COLORS.black} ] : Deactivated by {fromuser}",
                                                channel=dchanlog
                                            )

                            case 'limit':
                                reputation_seuil = int(cmd[3])
                                key = 'reputation_seuil'

                                # self.update_db_configuration(key, reputation_seuil)
                                self.__update_configuration(key, reputation_seuil)

                                self.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.green}REPUTATION SEUIL{self.Config.COLORS.black} ] : Limit set to {str(reputation_seuil)} by {fromuser}",
                                                channel=dchanlog
                                            )
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Reputation set to {reputation_seuil}")

                            case 'timer':
                                reputation_timer = int(cmd[3])
                                key = 'reputation_timer'
                                self.__update_configuration(key, reputation_timer)

                                self.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.green}REPUTATION TIMER{self.Config.COLORS.black} ] : Timer set to {str(reputation_timer)} minute(s) by {fromuser}",
                                                channel=dchanlog
                                            )
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Reputation set to {reputation_timer}")

                            case 'score_after_release':
                                reputation_score_after_release = int(cmd[3])
                                key = 'reputation_score_after_release'
                                self.__update_configuration(key, reputation_score_after_release)

                                self.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.green}REPUTATION SCORE AFTER RELEASE{self.Config.COLORS.black} ] : Reputation score after release set to {str(reputation_score_after_release)} by {fromuser}",
                                                channel=dchanlog
                                            )
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Reputation score after release set to {reputation_score_after_release}")

                            case 'security_group':
                                reputation_sg = int(cmd[3])
                                key = 'reputation_sg'
                                self.__update_configuration(key, reputation_sg)

                                self.Protocol.send_priv_msg(
                                                nick_from=dnickname,
                                                msg=f"[ {self.Config.COLORS.green}REPUTATION SECURITY-GROUP{self.Config.COLORS.black} ] : Reputation Security-group set to {str(reputation_sg)} by {fromuser}",
                                                channel=dchanlog
                                            )
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Reputation score after release set to {reputation_sg}")

                            case _:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation [ON/OFF]")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation release [nickname]")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set banallchan [ON/OFF]")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set limit [1234]")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set score_after_release [1234]")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set timer [1234]")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set action [kill|None]")

                except IndexError as ie:
                    self.Logs.warning(f'{ie}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation [ON/OFF]")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation release [nickname]")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set banallchan [ON/OFF]")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set limit [1234]")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set score_after_release [1234]")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set timer [1234]")
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f" Right command : /msg {dnickname} reputation set action [kill|None]")

                except ValueError as ve:
                    self.Logs.warning(f'{ve}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=" La valeur devrait etre un entier >= 0")

            case 'proxy_scan':

                # .proxy_scan set local_scan on/off          --> Va activer le scan des ports
                # .proxy_scan set psutil_scan on/off         --> Active les informations de connexion a la machine locale
                # .proxy_scan set abuseipdb_scan on/off      --> Active le scan via l'api abuseipdb
                len_cmd = len(cmd)
                color_green = self.Config.COLORS.green
                color_red = self.Config.COLORS.red
                color_black = self.Config.COLORS.black

                if len_cmd == 4:
                    set_key = str(cmd[1]).lower()

                    if set_key != 'set':
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')

                    option = str(cmd[2]).lower() # => local_scan, psutil_scan, abuseipdb_scan
                    action = str(cmd[3]).lower() # => on / off

                    match option:
                        case 'local_scan':
                            if action == 'on':
                                if self.ModConfig.local_scan == 1:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 1)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.ModConfig.local_scan == 0:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 0)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case 'psutil_scan':
                            if action == 'on':
                                if self.ModConfig.psutil_scan == 1:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 1)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.ModConfig.psutil_scan == 0:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 0)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case 'abuseipdb_scan':
                            if action == 'on':
                                if self.ModConfig.abuseipdb_scan == 1:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 1)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.ModConfig.abuseipdb_scan == 0:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 0)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case 'freeipapi_scan':
                            if action == 'on':
                                if self.ModConfig.freeipapi_scan == 1:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 1)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.ModConfig.freeipapi_scan == 0:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 0)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case 'cloudfilt_scan':
                            if action == 'on':
                                if self.ModConfig.cloudfilt_scan == 1:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Already activated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 1)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_green}PROXY_SCAN {option.upper()}{color_black} ] : Activated by {fromuser}", channel=dchanlog)
                            elif action == 'off':
                                if self.ModConfig.cloudfilt_scan == 0:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Already Deactivated", channel=dchanlog)
                                    return None

                                self.__update_configuration(option, 0)

                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {color_red}PROXY_SCAN {option.upper()}{color_black} ] : Deactivated by {fromuser}", channel=dchanlog)

                        case _:
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')
                else:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set local_scan [ON/OFF]')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set psutil_scan [ON/OFF]')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set abuseipdb_scan [ON/OFF]')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set freeipapi_scan [ON/OFF]')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Right command : /msg {dnickname} proxy_scan set cloudfilt_scan [ON/OFF]')

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
                            if self.ModConfig.flood == 1:
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.Config.COLORS.green}FLOOD{self.Config.COLORS.black} ] : Already activated", channel=dchanlog)
                                return False

                            self.__update_configuration(key, 1)

                            self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.Config.COLORS.green}FLOOD{self.Config.COLORS.black} ] : Activated by {fromuser}", channel=dchanlog)

                        if activation == 'off':
                            if self.ModConfig.flood == 0:
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.Config.COLORS.red}FLOOD{self.Config.COLORS.black} ] : Already Deactivated", channel=dchanlog)
                                return False

                            self.__update_configuration(key, 0)

                            self.Protocol.send_priv_msg(nick_from=dnickname, msg=f"[ {self.Config.COLORS.green}FLOOD{self.Config.COLORS.black} ] : Deactivated by {fromuser}", channel=dchanlog)

                    if len_cmd == 4:
                        set_key = str(cmd[2]).lower()

                        if str(cmd[1]).lower() == 'set':
                            match set_key:
                                case 'flood_message':
                                    key = 'flood_message'
                                    set_value = int(cmd[3])
                                    self.__update_configuration(key, set_value)

                                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                              msg=f"[ {self.Config.COLORS.green}FLOOD{self.Config.COLORS.black} ] : Flood message set to {set_value} by {fromuser}", 
                                                              channel=dchanlog)

                                case 'flood_time':
                                    key = 'flood_time'
                                    set_value = int(cmd[3])
                                    self.__update_configuration(key, set_value)

                                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                              msg=f"[ {self.Config.COLORS.green}FLOOD{self.Config.COLORS.black} ] : Flood time set to {set_value} by {fromuser}", 
                                                              channel=dchanlog)

                                case 'flood_timer':
                                    key = 'flood_timer'
                                    set_value = int(cmd[3])
                                    self.__update_configuration(key, set_value)

                                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                              msg=f"[ {self.Config.COLORS.green}FLOOD{self.Config.COLORS.black} ] : Flood timer set to {set_value} by {fromuser}", 
                                                              channel=dchanlog)

                                case _:
                                    pass

                except ValueError as ve:
                    self.Logs.error(f"{self.__class__.__name__} Value Error : {ve}")

            case 'status':
                color_green = self.Config.COLORS.green
                color_red = self.Config.COLORS.red
                color_black = self.Config.COLORS.black
                nogc = self.Config.COLORS.nogc
                try:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' [{color_green if self.ModConfig.reputation == 1 else color_red}Reputation{nogc}]                           ==> {self.ModConfig.reputation}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'           reputation_seuil             ==> {self.ModConfig.reputation_seuil}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'           reputation_after_release     ==> {self.ModConfig.reputation_score_after_release}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'           reputation_ban_all_chan      ==> {self.ModConfig.reputation_ban_all_chan}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'           reputation_timer             ==> {self.ModConfig.reputation_timer}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=' [Proxy_scan]')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.ModConfig.local_scan == 1 else color_red}local_scan{nogc}                 ==> {self.ModConfig.local_scan}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.ModConfig.psutil_scan == 1 else color_red}psutil_scan{nogc}                ==> {self.ModConfig.psutil_scan}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.ModConfig.abuseipdb_scan == 1 else color_red}abuseipdb_scan{nogc}             ==> {self.ModConfig.abuseipdb_scan}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.ModConfig.freeipapi_scan == 1 else color_red}freeipapi_scan{nogc}             ==> {self.ModConfig.freeipapi_scan}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.ModConfig.cloudfilt_scan == 1 else color_red}cloudfilt_scan{nogc}             ==> {self.ModConfig.cloudfilt_scan}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' [{color_green if self.ModConfig.autolimit == 1 else color_red}Autolimit{nogc}]                            ==> {self.ModConfig.autolimit}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.ModConfig.autolimit == 1 else color_red}Autolimit Amount{nogc}           ==> {self.ModConfig.autolimit_amount}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'             {color_green if self.ModConfig.autolimit == 1 else color_red}Autolimit Interval{nogc}         ==> {self.ModConfig.autolimit_interval}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' [{color_green if self.ModConfig.flood == 1 else color_red}Flood{nogc}]                                ==> {self.ModConfig.flood}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg='      flood_action                      ==> Coming soon')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'      flood_message                     ==> {self.ModConfig.flood_message}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'      flood_time                        ==> {self.ModConfig.flood_time}')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f'      flood_timer                       ==> {self.ModConfig.flood_timer}')
                except KeyError as ke:
                    self.Logs.error(f"Key Error : {ke}")

            case 'info':
                try:
                    if len(cmd) < 2:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Syntax. /msg {dnickname} INFO [nickname]")
                        return None

                    nickoruid = cmd[1]
                    UserObject = self.User.get_user(nickoruid)

                    if UserObject is not None:
                        channels: list = [chan.name for chan in self.Channel.UID_CHANNEL_DB for uid_in_chan in chan.uids if self.Loader.Utils.clean_uid(uid_in_chan) == UserObject.uid]

                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' UID              : {UserObject.uid}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' NICKNAME         : {UserObject.nickname}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' USERNAME         : {UserObject.username}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' REALNAME         : {UserObject.realname}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' HOSTNAME         : {UserObject.hostname}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' VHOST            : {UserObject.vhost}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' IP               : {UserObject.remote_ip}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' Country          : {UserObject.geoip}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' WebIrc           : {UserObject.isWebirc}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' WebWebsocket     : {UserObject.isWebsocket}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' REPUTATION       : {UserObject.score_connexion}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' MODES            : {UserObject.umodes}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' CHANNELS         : {channels}')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f' CONNECTION TIME  : {UserObject.connexion_datetime}')
                    else:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"This user {nickoruid} doesn't exist")

                except KeyError as ke:
                    self.Logs.warning(f"Key error info user : {ke}")

            case 'sentinel':
                # .sentinel on
                activation = str(cmd[1]).lower()
                channel_to_dont_quit = [self.Config.SALON_JAIL, self.Config.SERVICE_CHANLOG]

                if activation == 'on':
                    for chan in self.Channel.UID_CHANNEL_DB:
                        if chan.name not in channel_to_dont_quit:
                            self.Protocol.send_join_chan(uidornickname=dnickname, channel=chan.name)
                    return None

                if activation == 'off':
                    for chan in self.Channel.UID_CHANNEL_DB:
                        if chan.name not in channel_to_dont_quit:
                            self.Protocol.send_part_chan(uidornickname=dnickname, channel=chan.name)
                    self.join_saved_channels()
                    return None
