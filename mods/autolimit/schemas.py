from core.definition import MainModel, dataclass

@dataclass
class ModConfModel(MainModel):
    global_autolimit: int = 0
    global_amount: int = 3
    global_interval: int = 2

@dataclass
class ALChannel(MainModel):
    channel: str
    amount: int
    interval: int