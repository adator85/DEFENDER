from core.definition import MainModel, dataclass, MUser

@dataclass
class ModConfModel(MainModel):
    reputation: int = 0
    reputation_timer: int = 1
    reputation_seuil: int = 26
    reputation_score_after_release: int = 27
    reputation_ban_all_chan: int = 0
    reputation_sg: int = 1
    local_scan: int = 0
    psutil_scan: int = 0
    abuseipdb_scan: int = 0
    freeipapi_scan: int = 0
    cloudfilt_scan: int = 0
    flood: int = 0
    flood_message: int = 5
    flood_time: int = 1
    flood_timer: int = 20
    autolimit: int = 0
    autolimit_amount: int = 3
    autolimit_interval: int = 3

@dataclass
class FloodUser(MainModel):
    uid: str = None
    nbr_msg: int = 0
    first_msg_time: int = 0

DB_FLOOD_USERS: list[FloodUser] = []
DB_ABUSEIPDB_USERS: list[MUser] = []
DB_FREEIPAPI_USERS: list[MUser] = []
DB_CLOUDFILT_USERS: list[MUser] = []
DB_PSUTIL_USERS: list[MUser]    = []
DB_LOCALSCAN_USERS: list[MUser] = []