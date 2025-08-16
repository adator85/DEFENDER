from typing import TYPE_CHECKING, Optional
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
