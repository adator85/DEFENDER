from core.definition import MainModel, dataclass, field

@dataclass
class ModConfModel(MainModel):
    clone_nicknames: list[str] = field(default_factory=list)

@dataclass
class MClone(MainModel):
    """Model Clone"""
    connected: bool = False
    uid: str = None
    nickname: str = None
    username: str = None
    realname: str = None
    channels: list = field(default_factory=list)
    vhost: str = None
    hostname: str = 'localhost'
    umodes: str = None
    remote_ip: str = '127.0.0.1'
    group: str = 'Default',
    geoip: str = 'XX'

# DB_CLONES: list[MClone] = []