from typing import Optional
from core.definition import MainModel
from dataclasses import dataclass, field

@dataclass
class VoteChannelModel(MainModel):
    channel_name: Optional[str] = None
    target_user: Optional[str] = None
    voter_users: list = field(default_factory=list)
    vote_for: int = 0
    vote_against: int = 0
