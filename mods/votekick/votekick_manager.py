from typing import TYPE_CHECKING, Literal, Optional
from mods.votekick.schemas import VoteChannelModel

if TYPE_CHECKING:
    from mods.votekick.mod_votekick import Votekick

class VotekickManager:

    VOTE_CHANNEL_DB:list[VoteChannelModel] = []

    def __init__(self, uplink: 'Votekick'):
        self.uplink = uplink
        self.Logs   = uplink.Logs
        self.Utils  = uplink.Utils

    def activate_new_channel(self, channel_name: str) -> bool:
        """Activate a new channel in the votekick systeme

        Args:
            channel_name (str): The channel name you want to activate

        Returns:
            bool: True if it was activated
        """
        votec = self.get_vote_channel_model(channel_name)

        if votec is None:
            self.VOTE_CHANNEL_DB.append(
                VoteChannelModel(
                    channel_name=channel_name,
                    target_user='',
                    voter_users=[],
                    vote_for=0,
                    vote_against=0
                    )
            )
            self.Logs.debug(f"[VOTEKICK MANAGER] {channel_name} has been activated.")
            return True
        
        return False

    def init_vote_system(self, channel_name: str) -> bool:
        """Initializes or resets the votekick system for a given channel.

        This method clears the current target, voter list, and vote counts
        in preparation for a new votekick session.

        Args:
            channel_name (str): The name of the channel for which the votekick system should be initialized.

        Returns:
            bool: True if the votekick system was successfully initialized, False if the channel is not found.
        """
        votec = self.get_vote_channel_model(channel_name)

        if votec is None:
            self.Logs.debug(f"[VOTEKICK MANAGER] The channel ({channel_name}) is not active!")
            return False
        
        votec.target_user = ''
        votec.voter_users = []
        votec.vote_for = 0
        votec.vote_against = 0
        self.Logs.debug(f"[VOTEKICK MANAGER] The channel ({channel_name}) has been successfully initialized!")
        return True

    def get_vote_channel_model(self, channel_name: str) -> Optional[VoteChannelModel]:
        """Get Vote Channel Object model

        Args:
            channel_name (str): The channel name you want to activate

        Returns:
            (VoteChannelModel | None): The VoteChannelModel if exist
        """
        for vote in self.VOTE_CHANNEL_DB:
            if vote.channel_name.lower() == channel_name.lower():
                self.Logs.debug(f"[VOTEKICK MANAGER] {channel_name} has been found in the VOTE_CHANNEL_DB")
                return vote
        
        return None
    
    def drop_vote_channel_model(self, channel_name: str) -> bool:
        """Drop a channel from the votekick system.

        Args:
            channel_name (str): The channel name you want to drop

        Returns:
            bool: True if the channel has been droped.
        """
        votec = self.get_vote_channel_model(channel_name)

        if votec:
            self.VOTE_CHANNEL_DB.remove(votec)
            self.Logs.debug(f"[VOTEKICK MANAGER] {channel_name} has been removed from the VOTE_CHANNEL_DB")
            return True
        
        return False
    
    def is_vote_ongoing(self, channel_name: str) -> bool:
        """Check if there is an angoing vote on the channel provided

        Args:
            channel_name (str): The channel name to check

        Returns:
            bool: True if there is an ongoing vote on the channel provided.
        """

        votec = self.get_vote_channel_model(channel_name)

        if votec is None:
            self.Logs.debug(f"[VOTEKICK MANAGER] {channel_name} is not activated!")
            return False
        
        if votec.target_user:
            self.Logs.debug(f'[VOTEKICK MANAGER] A vote is ongoing on {channel_name}')
            return True
        
        self.Logs.debug(f'[VOTEKICK MANAGER] {channel_name} is activated but there is no ongoing vote!')

        return False

    def action_vote(self, channel_name: str, nickname: str, action: Literal['+', '-']) -> bool:
        """
        Registers a vote (for or against) in an active votekick session on a channel.

        Args:
            channel_name (str): The name of the channel where the votekick session is active.
            nickname (str): The nickname of the user casting the vote.
            action (Literal['+', '-']): The vote action. Use '+' to vote for kicking, '-' to vote against.

        Returns:
            bool: True if the vote was successfully registered, False otherwise.
                This can fail if:
                - The action is invalid (not '+' or '-')
                - The user has already voted
                - The channel has no active votekick session
        """
        if action not in ['+', '-']:
            self.Logs.debug(f"[VOTEKICK MANAGER] The action must be + or - while you have provided ({action})")
            return False
        votec = self.get_vote_channel_model(channel_name)

        if votec:
            client_obj = self.uplink.User.get_user(votec.target_user)
            client_to_punish = votec.target_user if client_obj is None else client_obj.nickname
            if nickname in votec.voter_users:
                self.Logs.debug(f"[VOTEKICK MANAGER] This nickname ({nickname}) has already voted for ({client_to_punish})")
                return False
            else:
                if action == '+':
                    votec.vote_for += 1
                elif action == '-':
                    votec.vote_against += 1

                votec.voter_users.append(nickname)
                self.Logs.debug(f"[VOTEKICK MANAGER] The ({nickname}) has voted to ban ({client_to_punish})")
                return True
        else:
            self.Logs.debug(f"[VOTEKICK MANAGER] This channel {channel_name} is not active!")
            return False
