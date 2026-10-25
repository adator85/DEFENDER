from dataclasses import dataclass, field
from core.definition import MainModel

@dataclass
class ModConfModel(MainModel):
    # clone_nicknames: list[str] = field(default_factory=list)
    snitch: int = 0

@dataclass
class MClone(MainModel):
    """Model Clone"""
    connected: bool
    uid: str
    nickname: str
    username: str
    realname: str
    vhost: str
    hostname: str
    umodes: str
    remote_ip: str
    group: str
    geoip: str
    channels: list = field(default_factory=list)

# DB_CLONES: list[MClone] = []