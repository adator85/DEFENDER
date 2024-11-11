from dataclasses import dataclass, fields, field
import copy
import random, faker, time, logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.irc import Irc

class Clone():

    @dataclass
    class ModConfModel:
        clone_nicknames: list[str]

    def __init__(self, ircInstance: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module (Mandatory)
        self.Irc = ircInstance

        # Add Irc Protocol Object to the module (Mandatory)
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

        # Add clone object to the module (Optionnal)
        self.Clone = ircInstance.Clone

        self.Definition = ircInstance.Loader.Definition

        # Créer les nouvelles commandes du module
        self.commands_level = {
            1: ['clone']
        }

        # Init the module (Mandatory)
        self.__init_module()

        # Log the module
        self.Logs.debug(f'Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Enrigstrer les nouvelles commandes dans le code
        self.__set_commands(self.commands_level)

        # Créer les tables necessaire a votre module (ce n'es pas obligatoire)
        self.__create_tables()

        self.stop = False
        logging.getLogger('faker').setLevel(logging.CRITICAL)

        self.fakeEN = faker.Faker('en_GB')
        self.fakeFR = faker.Faker('fr_FR')

        # Load module configuration (Mandatory)
        self.__load_module_configuration()

        self.Channel.db_query_channel(action='add', module_name=self.module_name, channel_name=self.Config.CLONE_CHANNEL)
        self.Protocol.send_join_chan(self.Config.SERVICE_NICKNAME, self.Config.CLONE_CHANNEL)

        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} SAMODE {self.Config.CLONE_CHANNEL} +o {self.Config.SERVICE_NICKNAME}")
        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} +nts")
        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} +k {self.Config.CLONE_CHANNEL_PASSWORD}")

    def __set_commands(self, commands:dict[int, list[str]]) -> None:
        """### Rajoute les commandes du module au programme principal

        Args:
            commands (list): Liste des commandes du module
        """
        for level, com in commands.items():
            for c in commands[level]:
                if not c in self.Irc.commands:
                    self.Irc.commands_level[level].append(c)
                    self.Irc.commands.append(c)

        return None

    def __create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module
        Args:
            database_name (str): Nom de la base de données ( pas d'espace dans le nom )

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
            self.ModConfig = self.ModConfModel(
                                    clone_nicknames=[]
                                )

            # Sync the configuration with core configuration (Mandatory)
            # self.Base.db_sync_core_config(self.module_name, self.ModConfig)

            return None

        except TypeError as te:
            self.Logs.critical(te)

    def unload(self) -> None:
        """Cette methode sera executée a chaque désactivation ou 
        rechargement de module
        """

        self.Channel.db_query_channel(action='del', module_name=self.module_name, channel_name=self.Config.CLONE_CHANNEL)
        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} -nts")
        self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} MODE {self.Config.CLONE_CHANNEL} -k {self.Config.CLONE_CHANNEL_PASSWORD}")
        self.Protocol.send_part_chan(self.Config.SERVICE_NICKNAME, self.Config.CLONE_CHANNEL)

        return None

    def generate_vhost(self) -> str:

        fake = self.fakeEN

        rand_1 = fake.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)
        rand_2 = fake.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)
        rand_3 = fake.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)

        vhost = ''.join(rand_1) + '.' + ''.join(rand_2) + '.' + ''.join(rand_3) + '.IP'
        return vhost

    def generate_clones(self, group: str = 'Default') -> None:
        try:

            fakeEN = self.fakeEN
            fakeFR = self.fakeFR
            unixtime = self.Base.get_unixtime()

            chaine = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            generate_uid = fakeEN.random_sample(chaine, 6)
            uid = self.Config.SERVEUR_ID + ''.join(generate_uid)

            umodes = self.Config.CLONE_UMODES

            # Generate Username
            chaine = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            new_username = fakeEN.random_sample(chaine, 9)
            username = ''.join(new_username)

            # Create realname XX F|M Department
            gender = fakeEN.random_choices(['F','M'], 1)
            gender = ''.join(gender)

            if gender == 'F':
                nickname = fakeEN.first_name_female()
            elif gender == 'M':
                nickname = fakeEN.first_name_male()
            else:
                nickname = fakeEN.first_name()

            age = random.randint(20, 60)
            department = fakeFR.department_name()
            realname = f'{age} {gender} {department}'

            decoded_ip = fakeEN.ipv4_private()
            hostname = fakeEN.hostname()

            vhost = self.generate_vhost()

            checkNickname = self.Clone.exists(nickname=nickname)
            checkUid = self.Clone.uid_exists(uid=uid)

            while checkNickname:
                caracteres = '0123456789'
                randomize = ''.join(random.choice(caracteres) for _ in range(2))
                nickname = nickname + str(randomize)
                checkNickname = self.Clone.exists(nickname=nickname)

            while checkUid:
                chaine = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                generate_uid = fakeEN.random_sample(chaine, 6)
                uid = self.Config.SERVEUR_ID + ''.join(generate_uid)
                checkUid = self.Clone.uid_exists(uid=uid)

            clone = self.Definition.MClone(
                        connected=False,
                        nickname=nickname,
                        username=username,
                        realname=realname,
                        hostname=hostname,
                        umodes=umodes,
                        uid=uid,
                        remote_ip=decoded_ip,
                        vhost=vhost,
                        group=group,
                        channels=[]
                        )

            self.Clone.insert(clone)

            return None

        except AttributeError as ae:
            self.Logs.error(f'Attribute Error : {ae}')
        except Exception as err:
            self.Logs.error(f"General Error: {err}")

    def thread_connect_clones(self, number_of_clones:int , group: str, interval: float = 0.2) -> None:

        for i in range(0, number_of_clones):
            self.generate_clones(group=group)

        for clone in self.Clone.UID_CLONE_DB:

            if self.stop:
                print(f"Stop creating clones ...")
                self.stop = False
                break

            if not clone.connected:
                self.Protocol.send_uid(clone.nickname, clone.username, clone.hostname, clone.uid, clone.umodes, clone.vhost, clone.remote_ip, clone.realname, print_log=False)
                self.Protocol.send_join_chan(uidornickname=clone.uid, channel=self.Config.CLONE_CHANNEL, password=self.Config.CLONE_CHANNEL_PASSWORD, print_log=False)

            time.sleep(interval)
            clone.connected = True

    def thread_kill_clones(self, fromuser: str) -> None:

        clone_to_kill: list[str] = []
        for clone in self.Clone.UID_CLONE_DB:
            clone_to_kill.append(clone.uid)

        for clone_uid in clone_to_kill:
            self.Protocol.send_quit(clone_uid, 'Gooood bye', print_log=False)

        del clone_to_kill

        return None

    def cmd(self, data:list) -> None:
        try:
            service_id = self.Config.SERVICE_ID                 # Defender serveur id
            cmd = list(data).copy()

            if len(cmd) < 2:
                return None

            match cmd[1]:

                case 'REPUTATION':
                    pass

            if len(cmd) < 3:
                return None

            match cmd[2]:
                case 'PRIVMSG':
                    # print(cmd)
                    uid_sender = self.User.clean_uid(cmd[1])
                    senderObj = self.User.get_User(uid_sender)

                    if senderObj.hostname in self.Config.CLONE_LOG_HOST_EXEMPT:
                        return None

                    if not senderObj is None:
                        senderMsg = ' '.join(cmd[4:])
                        getClone = self.Clone.get_Clone(cmd[3])

                        if getClone is None:
                            return None

                        if getClone.uid != self.Config.SERVICE_ID:
                            final_message = f"{senderObj.nickname}!{senderObj.username}@{senderObj.hostname} > {senderMsg.lstrip(':')}"
                            self.Protocol.send_priv_msg(
                                nick_from=getClone.uid,
                                msg=final_message,
                                channel=self.Config.CLONE_CHANNEL
                            )

        except Exception as err:
            self.Logs.error(f'General Error: {err}')

    def _hcmds(self, user:str, channel: any, cmd: list, fullcmd: list = []) -> None:

        try:
            command = str(cmd[0]).lower()
            fromuser = user

            dnickname = self.Config.SERVICE_NICKNAME            # Defender nickname

            match command:

                case 'clone':

                    if len(cmd) == 1:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone connect NUMBER GROUP_NAME INTERVAL")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill [all | nickname]")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join [all | nickname] #channel")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part [all | nickname] #channel")
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone list")

                    option = str(cmd[1]).lower()

                    match option:

                        case 'connect':
                            try:
                                # clone connect 5 Group 3
                                self.stop = False
                                number_of_clones = int(cmd[2])
                                group = str(cmd[3]).lower()
                                connection_interval = int(cmd[4]) if len(cmd) == 5 else 0.5

                                self.Base.create_thread(
                                    func=self.thread_connect_clones,
                                    func_args=(number_of_clones, group, connection_interval)
                                )

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone connect [number of clone you want to connect] [Group]")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Exemple /msg {dnickname} clone connect 6 Ambiance")

                        case 'kill':
                            try:
                                # clone kill [all | nickname]
                                self.stop = True
                                clone_name = str(cmd[2])
                                clone_to_kill: list[str] = []

                                if clone_name.lower() == 'all':
                                    self.Base.create_thread(func=self.thread_kill_clones, func_args=(fromuser, ))

                                else:
                                    cloneObj = self.Clone.get_Clone(clone_name)
                                    if not cloneObj is None:
                                        self.Protocol.send_quit(cloneObj.uid, 'Goood bye', print_log=False)

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill all")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill clone_nickname")

                        case 'join':
                            try:
                                # clone join [all | nickname] #channel
                                clone_name = str(cmd[2])
                                clone_channel_to_join = str(cmd[3])

                                if clone_name.lower() == 'all':

                                    for clone in self.Clone.UID_CLONE_DB:
                                        self.Protocol.send_join_chan(uidornickname=clone.uid, channel=clone_channel_to_join, print_log=False)

                                else:
                                    if self.Clone.exists(clone_name):
                                        if not self.Clone.get_uid(clone_name) is None:
                                            self.Protocol.send_join_chan(uidornickname=clone_name, channel=clone_channel_to_join, print_log=False)

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join all #channel")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join clone_nickname #channel")

                        case 'part':
                            try:
                                # clone part [all | nickname] #channel
                                clone_name = str(cmd[2])
                                clone_channel_to_part = str(cmd[3])

                                if clone_name.lower() == 'all':

                                    for clone in self.Clone.UID_CLONE_DB:
                                        self.Protocol.send_part_chan(uidornickname=clone.uid, channel=clone_channel_to_part, print_log=False)

                                else:
                                    if self.Clone.exists(clone_name):
                                        clone_uid = self.Clone.get_uid(clone_name)
                                        if not clone_uid is None:
                                            self.Protocol.send_part_chan(uidornickname=clone_uid, channel=clone_channel_to_part, print_log=False)

                            except Exception as err:
                                self.Logs.error(f'{err}')
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part all #channel")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part clone_nickname #channel")

                        case 'list':
                            try:
                                clone_count = len(self.Clone.UID_CLONE_DB)
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f">> Number of connected clones: {clone_count}")
                                for clone_name in self.Clone.UID_CLONE_DB:
                                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, 
                                                             msg=f">> Nickname: {clone_name.nickname} | Username: {clone_name.username} | Realname: {clone_name.realname} | Vhost: {clone_name.vhost} | UID: {clone_name.uid} | Group: {clone_name.group} | Connected: {clone_name.connected}")
                            except Exception as err:
                                self.Logs.error(f'{err}')

                        case 'say':
                            try:
                                # clone say clone_nickname #channel message
                                clone_name = str(cmd[2])
                                clone_channel = str(cmd[3]) if self.Channel.Is_Channel(str(cmd[3])) else None

                                final_message = ' '.join(cmd[4:])

                                if clone_channel is None or not self.Clone.exists(clone_name):
                                    self.Protocol.send_notice(
                                        nick_from=dnickname,
                                        nick_to=fromuser,
                                        msg=f"/msg {dnickname} clone say [clone_nickname] #channel message"
                                    )
                                    return None

                                if self.Clone.exists(clone_name):
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
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone kill [all | nickname]")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone join [all | nickname] #channel")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone part [all | nickname] #channel")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} clone list")

        except IndexError as ie:
            self.Logs.error(f'Index Error: {ie}')
        except Exception as err:
            self.Logs.error(f'Index Error: {err}')
