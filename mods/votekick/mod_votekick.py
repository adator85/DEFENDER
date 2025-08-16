"""
    File        : mod_votekick.py
    Version     : 1.0.0
    Description : Manages votekick sessions for multiple channels.
                Handles activation, ongoing vote checks, and cleanup.
    Author      : adator
    Created     : 2025-08-16
    Last Updated: 2025-08-16
-----------------------------------------
"""
import re
import mods.votekick.schemas as schemas
from mods.votekick.votekick_manager import VotekickManager
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from core.irc import Irc


class Votekick:

    def __init__(self, uplink: 'Irc') -> None:

        # Module name (Mandatory)
        self.module_name = 'mod_' + str(self.__class__.__name__).lower()

        # Add Irc Object to the module
        self.Irc = uplink

        # Add Loader Object to the module (Mandatory)
        self.Loader = uplink.Loader

        # Add server protocol Object to the module (Mandatory)
        self.Protocol = uplink.Protocol

        # Add Global Configuration to the module
        self.Config = uplink.Config

        # Add Base object to the module
        self.Base = uplink.Base

        # Add logs object to the module
        self.Logs = uplink.Base.logs

        # Add User object to the module
        self.User = uplink.User

        # Add Channel object to the module
        self.Channel = uplink.Channel

        # Add Utils.
        self.Utils = uplink.Utils

        # Add Schemas module
        self.Schemas = schemas

        # Add VoteKick Manager
        self.VoteKickManager = VotekickManager(self)

        metadata = uplink.Loader.Settings.get_cache('VOTEKICK')
        
        if metadata is not None:
            self.VoteKickManager.VOTE_CHANNEL_DB = metadata
            # self.VOTE_CHANNEL_DB = metadata

        # Créer les nouvelles commandes du module
        self.Irc.build_command(1, self.module_name, 'vote', 'The kick vote module')

        # Init the module
        self.__init_module()

        # Log the module
        self.Logs.debug(f'-- Module {self.module_name} loaded ...')

    def __init_module(self) -> None:

        # Add admin object to retrieve admin users
        self.Admin = self.Irc.Admin
        self.__create_tables()
        self.join_saved_channels()

        return None

    def __create_tables(self) -> None:
        """Methode qui va créer la base de donnée si elle n'existe pas.
           Une Session unique pour cette classe sera crée, qui sera utilisé dans cette classe / module

        Returns:
            None: Aucun retour n'es attendu
        """

        table_logs = '''CREATE TABLE IF NOT EXISTS votekick_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            server_msg TEXT
            ) 
        '''

        table_vote = '''CREATE TABLE IF NOT EXISTS votekick_channel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            channel TEXT
            )
        '''

        self.Base.db_execute_query(table_logs)
        self.Base.db_execute_query(table_vote)
        return None

    def unload(self) -> None:
        try:
            # Cache the local DB with current votes.
            self.Loader.Settings.set_cache('VOTEKICK', self.VoteKickManager.VOTE_CHANNEL_DB)

            for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
                self.Protocol.send_part_chan(uidornickname=self.Config.SERVICE_ID, channel=chan.channel_name)

            self.VoteKickManager.VOTE_CHANNEL_DB = []
            self.Logs.debug(f'Delete memory DB VOTE_CHANNEL_DB: {self.VoteKickManager.VOTE_CHANNEL_DB}')

            return None
        except UnboundLocalError as ne:
            self.Logs.error(f'{ne}')
        except NameError as ue:
            self.Logs.error(f'{ue}')
        except Exception as err:
            self.Logs.error(f'General Error: {err}')

    def init_vote_system(self, channel: str) -> bool:

        response = False
        for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
            if chan.channel_name == channel:
                chan.target_user = ''
                chan.voter_users = []
                chan.vote_against = 0
                chan.vote_for = 0
                response = True

        return response

    def insert_vote_channel(self, channel_obj: schemas.VoteChannelModel) -> bool:
        result = False
        found = False
        for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
            if chan.channel_name == channel_obj.channel_name:
                found = True

        if not found:
            self.VoteKickManager.VOTE_CHANNEL_DB.append(channel_obj)
            self.Logs.debug(f"The channel has been added {channel_obj}")
            # self.db_add_vote_channel(ChannelObject.channel_name)

        return result

    def db_add_vote_channel(self, channel: str) -> bool:
        """Cette fonction ajoute les salons ou seront autoriser les votes

        Args:
            channel (str): le salon à enregistrer.
        """
        current_datetime = self.Utils.get_sdatetime()
        mes_donnees = {'channel': channel}

        response = self.Base.db_execute_query("SELECT id FROM votekick_channel WHERE channel = :channel", mes_donnees)

        is_channel_exist = response.fetchone()

        if is_channel_exist is None:
            mes_donnees = {'datetime': current_datetime, 'channel': channel}
            insert = self.Base.db_execute_query(f"INSERT INTO votekick_channel (datetime, channel) VALUES (:datetime, :channel)", mes_donnees)
            if insert.rowcount > 0:
                return True
            else:
                return False
        else:
            return False

    def db_delete_vote_channel(self, channel: str) -> bool:
        """Cette fonction supprime les salons de join de Defender

        Args:
            channel (str): le salon à enregistrer.
        """
        mes_donnes = {'channel': channel}
        response = self.Base.db_execute_query("DELETE FROM votekick_channel WHERE channel = :channel", mes_donnes)
        
        affected_row = response.rowcount

        if affected_row > 0:
            return True
        else:
            return False

    def join_saved_channels(self) -> None:

        param = {'module_name': self.module_name}
        result = self.Base.db_execute_query(f"SELECT id, channel_name FROM {self.Config.TABLE_CHANNEL} WHERE module_name = :module_name", param)

        channels = result.fetchall()

        for channel in channels:
            id_, chan = channel
            self.insert_vote_channel(self.Schemas.VoteChannelModel(channel_name=chan, target_user='', voter_users=[], vote_for=0, vote_against=0))
            self.Protocol.sjoin(channel=chan)
            self.Protocol.send2socket(f":{self.Config.SERVICE_NICKNAME} SAMODE {chan} +o {self.Config.SERVICE_NICKNAME}")

        return None

    def is_vote_ongoing(self, channel: str) -> bool:

        response = False
        for vote in self.VoteKickManager.VOTE_CHANNEL_DB:
            if vote.channel_name == channel:
                if vote.target_user:
                    response = True

        return response

    def timer_vote_verdict(self, channel: str) -> None:

        dnickname = self.Config.SERVICE_NICKNAME

        if not self.is_vote_ongoing(channel):
            return None

        for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
            if chan.channel_name == channel:
                target_user = self.User.get_nickname(chan.target_user)
                if chan.vote_for > chan.vote_against:
                    self.Protocol.send_priv_msg(
                        nick_from=dnickname,
                        msg=f"User {self.Config.COLORS.bold}{target_user}{self.Config.COLORS.nogc} has {chan.vote_against} votes against and {chan.vote_for} votes for. For this reason, it'll be kicked from the channel",
                        channel=channel
                    )
                    self.Protocol.send2socket(f":{dnickname} KICK {channel} {target_user} Following the vote, you are not welcome in {channel}")
                    self.Channel.delete_user_from_channel(channel, self.User.get_uid(target_user))
                elif chan.vote_for <= chan.vote_against:
                    self.Protocol.send_priv_msg(
                        nick_from=dnickname,
                        msg=f"User {self.Config.COLORS.bold}{target_user}{self.Config.COLORS.nogc} has {chan.vote_against} votes against and {chan.vote_for} votes for. For this reason, it\'ll remain in the channel",
                        channel=channel
                    )

                # Init the system
                if self.init_vote_system(channel):
                    self.Protocol.send_priv_msg(
                        nick_from=dnickname,
                        msg="System vote re initiated",
                        channel=channel
                    )

        return None

    def cmd(self, data: list) -> None:

        cmd = list(data).copy()

        try:

            return None

        except KeyError as ke:
            self.Logs.error(f"Key Error: {ke}")
        except IndexError as ie:
            self.Logs.error(f"{ie} / {cmd} / length {str(len(cmd))}")
        except Exception as err:
            self.Logs.error(f"General Error: {err}")

    def hcmds(self, user:str, channel: Any, cmd: list, fullcmd: Optional[list] = None) -> None:
        # cmd is the command starting from the user command
        # full cmd is sending the entire server response

        command = str(cmd[0]).lower()
        fullcmd = fullcmd
        dnickname = self.Config.SERVICE_NICKNAME
        fromuser = user
        fromchannel = channel

        match command:

            case 'vote':

                if len(cmd) == 1:
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote activate #channel')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote deactivate #channel')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote +')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote -')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote cancel')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote status')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote submit nickname')
                    self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote verdict')
                    return None

                option = str(cmd[1]).lower()

                match option:

                    case 'activate':
                        try:
                            # vote activate #channel
                            if self.Admin.get_admin(fromuser) is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' :Your are not allowed to execute this command')
                                return None

                            sentchannel = str(cmd[2]).lower() if self.Channel.is_valid_channel(str(cmd[2]).lower()) else None
                            if sentchannel is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f" The correct command is {self.Config.SERVICE_PREFIX}{command} {option} #CHANNEL")

                            self.insert_vote_channel(
                                self.Schemas.VoteChannelModel(
                                    channel_name=sentchannel,
                                    target_user='',
                                    voter_users=[],
                                    vote_for=0,
                                    vote_against=0
                                    )
                                )

                            self.Channel.db_query_channel('add', self.module_name, sentchannel)

                            self.Protocol.send_join_chan(uidornickname=dnickname, channel=sentchannel)
                            self.Protocol.send2socket(f":{dnickname} SAMODE {sentchannel} +o {dnickname}")
                            self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg="You can now use !submit <nickname> to decide if he will stay or not on this channel ",
                                                      channel=sentchannel
                                                      )
                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} {command} {option} #channel')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Exemple /msg {dnickname} {command} {option} #welcome')

                    case 'deactivate':
                        try:
                            # vote deactivate #channel
                            if self.Admin.get_admin(fromuser) is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f" Your are not allowed to execute this command")
                                return None

                            sentchannel = str(cmd[2]).lower() if self.Channel.is_valid_channel(str(cmd[2]).lower()) else None
                            if sentchannel is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f" The correct command is {self.Config.SERVICE_PREFIX}{command} {option} #CHANNEL")

                            self.Protocol.send2socket(f":{dnickname} SAMODE {sentchannel} -o {dnickname}")
                            self.Protocol.send_part_chan(uidornickname=dnickname, channel=sentchannel)

                            for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
                                if chan.channel_name == sentchannel:
                                    self.VoteKickManager.VOTE_CHANNEL_DB.remove(chan)
                                    self.Channel.db_query_channel('del', self.module_name, chan.channel_name)

                            self.Logs.debug(f"The Channel {sentchannel} has been deactivated from the vote system")
                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f" /msg {dnickname} {command} {option} #channel")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f" Exemple /msg {dnickname} {command} {option} #welcome")

                    case '+':
                        try:
                            # vote +
                            channel = fromchannel
                            for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
                                if chan.channel_name == channel:
                                    if fromuser in chan.voter_users:
                                        self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg="You already submitted a vote",
                                                      channel=channel
                                                      )
                                    else:
                                        chan.vote_for += 1
                                        chan.voter_users.append(fromuser)
                                        self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg="Vote recorded, thank you",
                                                      channel=channel
                                                      )
                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} {command} {option}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Exemple /msg {dnickname} {command} {option}')

                    case '-':
                        try:
                            # vote -
                            channel = fromchannel
                            for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
                                if chan.channel_name == channel:
                                    if fromuser in chan.voter_users:
                                        self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg="You already submitted a vote",
                                                      channel=channel
                                                      )
                                    else:
                                        chan.vote_against += 1
                                        chan.voter_users.append(fromuser)
                                        self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg="Vote recorded, thank you",
                                                      channel=channel
                                                      )
                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} {command} {option}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Exemple /msg {dnickname} {command} {option}')

                    case 'cancel':
                        try:
                            # vote cancel
                            if self.Admin.get_admin(fromuser) is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Your are not allowed to execute this command')
                                return None

                            if channel is None:
                                self.Logs.error(f"The channel is not known, defender can't cancel the vote")
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' You need to specify the channel => /msg {dnickname} vote_cancel #channel')

                            for vote in self.VoteKickManager.VOTE_CHANNEL_DB:
                                if vote.channel_name == channel:
                                    self.init_vote_system(channel)
                                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg="Vote system re-initiated",
                                                      channel=channel
                                                      )

                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} {command} {option}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Exemple /msg {dnickname} {command} {option}')

                    case 'status':
                        try:
                            # vote status
                            for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
                                if chan.channel_name == channel:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg=f"Channel: {chan.channel_name} | Target: {self.User.get_nickname(chan.target_user)} | For: {chan.vote_for} | Against: {chan.vote_against} | Number of voters: {str(len(chan.voter_users))}",
                                                      channel=channel
                                                      )
                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} {command} {option}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Exemple /msg {dnickname} {command} {option}')

                    case 'submit':
                        try:
                            # vote submit nickname
                            if self.Admin.get_admin(fromuser) is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Your are not allowed to execute this command')
                                return None

                            nickname_submitted = cmd[2]
                            uid_submitted = self.User.get_uid(nickname_submitted)
                            user_submitted = self.User.get_User(nickname_submitted)
                            ongoing_user = None

                            # check if there is an ongoing vote
                            if self.is_vote_ongoing(channel):
                                for vote in self.VoteKickManager.VOTE_CHANNEL_DB:
                                    if vote.channel_name == channel:
                                        ongoing_user = self.User.get_nickname(vote.target_user)

                                self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg=f"There is an ongoing vote on {ongoing_user}",
                                                      channel=channel
                                                      )
                                return None

                            # check if the user exist
                            if user_submitted is None:
                                self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg=f"This nickname <{nickname_submitted}> do not exist",
                                                      channel=channel
                                                      )
                                return None

                            uid_cleaned = self.Base.clean_uid(uid_submitted)
                            channel_obj = self.Channel.get_channel(channel)
                            if channel_obj is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' This channel [{channel}] do not exist in the Channel Object')
                                return None

                            clean_uids_in_channel: list = []
                            for uid in channel_obj.uids:
                                clean_uids_in_channel.append(self.Base.clean_uid(uid))

                            if not uid_cleaned in clean_uids_in_channel:
                                self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg=f"This nickname <{nickname_submitted}> is not available in this channel",
                                                      channel=channel
                                                      )
                                return None

                            # check if Ircop or Service or Bot
                            pattern = fr'[o|B|S]'
                            operator_user = re.findall(pattern, user_submitted.umodes)
                            if operator_user:
                                self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg="You cant vote for this user ! he/she is protected",
                                                      channel=channel
                                                      )
                                return None

                            for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
                                if chan.channel_name == channel:
                                    chan.target_user = self.User.get_uid(nickname_submitted)

                            self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg=f"{nickname_submitted} has been targeted for a vote",
                                                      channel=channel
                                                      )

                            self.Base.create_timer(60, self.timer_vote_verdict, (channel, ))
                            self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg="This vote will end after 60 secondes",
                                                      channel=channel
                                                      )

                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} {command} {option} nickname')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Exemple /msg {dnickname} {command} {option} adator')

                    case 'verdict':
                        try:
                            # vote verdict
                            if self.Admin.get_admin(fromuser) is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f'Your are not allowed to execute this command')
                                return None

                            for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
                                if chan.channel_name == channel:
                                    target_user = self.User.get_nickname(chan.target_user)
                                    if chan.vote_for > chan.vote_against:
                                        self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg=f"User {self.Config.COLORS.bold}{target_user}{self.Config.COLORS.nogc} has {chan.vote_against} votes against and {chan.vote_for} votes for. For this reason, it\'ll be kicked from the channel",
                                                      channel=channel
                                                      )
                                        self.Protocol.send2socket(f":{dnickname} KICK {channel} {target_user} Following the vote, you are not welcome in {channel}")
                                    elif chan.vote_for <= chan.vote_against:
                                        self.Protocol.send_priv_msg(
                                            nick_from=dnickname, 
                                            msg=f"User {self.Config.COLORS.bold}{target_user}{self.Config.COLORS.nogc} has {chan.vote_against} votes against and {chan.vote_for} votes for. For this reason, it\'ll remain in the channel",
                                            channel=channel
                                            )

                                    # Init the system
                                    if self.init_vote_system(channel):
                                        self.Protocol.send_priv_msg(
                                            nick_from=dnickname, 
                                            msg="System vote re initiated",
                                            channel=channel
                                            )
                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} {command} {option}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Exemple /msg {dnickname} {command} {option}')

                    case _:
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote activate #channel')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote deactivate #channel')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote +')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote -')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote cancel')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote status')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote submit nickname')
                        self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} vote verdict')
                        return None

            case _:
                return None