"""
    File        : mod_votekick.py
    Version     : 1.0.2
    Description : Manages votekick sessions for multiple channels.
                Handles activation, ongoing vote checks, and cleanup.
    Author      : adator
    Created     : 2025-08-16
    Last Updated: 2025-11-01
-----------------------------------------
"""
from dataclasses import dataclass
import re
from core.classes.interfaces.imodule import IModule
import mods.votekick.schemas as schemas
import mods.votekick.utils as utils
from mods.votekick.votekick_manager import VotekickManager
import mods.votekick.threads as thds
from typing import Any, Optional

class Votekick(IModule):

    @dataclass
    class ModConfModel(schemas.VoteChannelModel):
        ...

    MOD_HEADER: dict[str, str] = {
        'name':'votekick',
        'version':'1.0.2',
        'description':'Channel Democraty',
        'author':'Defender Team',
        'core_version':'Defender-6'
    }

    def create_tables(self) -> None:
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

    def load(self) -> None:

        self.ModConfig = self.ModConfModel()
        
        # Add VoteKick Manager
        self.VoteKickManager = VotekickManager(self)

        # Add Utils module
        self.ModUtils = utils

        # Add Schemas module
        self.Schemas = schemas

        # Add Threads module
        self.Threads = thds

        self.ModUtils.join_saved_channels(self)

        metadata = self.Settings.get_cache('VOTEKICK')
        
        if metadata is not None:
            self.VoteKickManager.VOTE_CHANNEL_DB = metadata

        # Créer les nouvelles commandes du module
        self.Irc.build_command(1, self.module_name, 'vote', 'The kick vote module')

    def unload(self) -> None:
        try:
            # Cache the local DB with current votes.
            if self.VoteKickManager.VOTE_CHANNEL_DB:
                self.Settings.set_cache('VOTEKICK', self.VoteKickManager.VOTE_CHANNEL_DB)

            for chan in self.VoteKickManager.VOTE_CHANNEL_DB:
                self.Protocol.send_part_chan(uidornickname=self.Config.SERVICE_ID, channel=chan.channel_name)

            self.VoteKickManager.VOTE_CHANNEL_DB = []
            self.Logs.debug(f'Delete memory DB VOTE_CHANNEL_DB: {self.VoteKickManager.VOTE_CHANNEL_DB}')

            self.Irc.Commands.drop_command_by_module(self.module_name)

            return None
        except UnboundLocalError as ne:
            self.Logs.error(f'{ne}')
        except NameError as ue:
            self.Logs.error(f'{ue}')
        except Exception as err:
            self.Logs.error(f'General Error: {err}')

    def cmd(self, data: list) -> None:

        if not data or len(data) < 2:
                return None

        cmd = data.copy() if isinstance(data, list) else list(data).copy()
        index, command = self.Irc.Protocol.get_ircd_protocol_poisition(cmd)
        if index == -1:
            return None

        try:

            match command:

                case 'PRIVMSG':
                    return None

                case 'QUIT':
                    return None

                case _:
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

                            if self.VoteKickManager.activate_new_channel(sentchannel):
                                self.Channel.db_query_channel('add', self.module_name, sentchannel)
                                self.Protocol.send_join_chan(uidornickname=dnickname, channel=sentchannel)
                                self.Protocol.send2socket(f":{dnickname} SAMODE {sentchannel} +o {dnickname}")
                                self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                        msg="You can now use !submit <nickname> to decide if he will stay or not on this channel ",
                                                        channel=sentchannel
                                                        )

                                return None

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

                            if self.VoteKickManager.drop_vote_channel_model(sentchannel):
                                self.Channel.db_query_channel('del', self.module_name, sentchannel)
                                return None

                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f" /msg {dnickname} {command} {option} #channel")
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f" Exemple /msg {dnickname} {command} {option} #welcome")

                    case '+':
                        try:
                            # vote +
                            channel = fromchannel
                            if self.VoteKickManager.action_vote(channel, fromuser, '+'):
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg="Vote recorded, thank you",channel=channel)
                            else:
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg="You already submitted a vote", channel=channel)

                        except Exception as err:
                            self.Logs.error(f'{err}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' /msg {dnickname} {command} {option}')
                            self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' Exemple /msg {dnickname} {command} {option}')

                    case '-':
                        try:
                            # vote -
                            channel = fromchannel
                            if self.VoteKickManager.action_vote(channel, fromuser, '-'):
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg="Vote recorded, thank you",channel=channel)
                            else:
                                self.Protocol.send_priv_msg(nick_from=dnickname, msg="You already submitted a vote", channel=channel)

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
                                    if self.VoteKickManager.init_vote_system(channel):
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
                            user_submitted = self.User.get_user(nickname_submitted)
                            ongoing_user = None

                            # check if there is an ongoing vote
                            if self.VoteKickManager.is_vote_ongoing(channel):
                                votec = self.VoteKickManager.get_vote_channel_model(channel)
                                if votec:
                                    ongoing_user = self.User.get_nickname(votec.target_user)
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

                            uid_cleaned = self.Loader.Utils.clean_uid(uid_submitted)
                            channel_obj = self.Channel.get_channel(channel)
                            if channel_obj is None:
                                self.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,msg=f' This channel [{channel}] do not exist in the Channel Object')
                                return None

                            clean_uids_in_channel: list = []
                            for uid in channel_obj.uids:
                                clean_uids_in_channel.append(self.Loader.Utils.clean_uid(uid))

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

                            self.Base.create_timer(60, self.Threads.timer_vote_verdict, (self, channel))
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
                            
                            votec = self.VoteKickManager.get_vote_channel_model(channel)
                            if votec:
                                target_user = self.User.get_nickname(votec.target_user)
                                if votec.vote_for >= votec.vote_against:
                                    self.Protocol.send_priv_msg(nick_from=dnickname, 
                                                      msg=f"User {self.Config.COLORS.bold}{target_user}{self.Config.COLORS.nogc} has {votec.vote_against} votes against and {votec.vote_for} votes for. For this reason, it\'ll be kicked from the channel",
                                                      channel=channel
                                                      )
                                    self.Protocol.send2socket(f":{dnickname} KICK {channel} {target_user} Following the vote, you are not welcome in {channel}")
                                else:
                                    self.Protocol.send_priv_msg(
                                            nick_from=dnickname, 
                                            msg=f"User {self.Config.COLORS.bold}{target_user}{self.Config.COLORS.nogc} has {votec.vote_against} votes against and {votec.vote_for} votes for. For this reason, it\'ll remain in the channel",
                                            channel=channel
                                            )
                                
                                if self.VoteKickManager.init_vote_system(channel):
                                    self.Protocol.send_priv_msg(
                                            nick_from=dnickname, 
                                            msg="System vote re initiated",
                                            channel=channel
                                            )
                            return None

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