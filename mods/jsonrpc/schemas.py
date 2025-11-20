from core.definition import MainModel, dataclass 

@dataclass
class ModConfModel(MainModel):
    jsonrpc: int = 0
