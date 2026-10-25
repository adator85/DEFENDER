from enum import Enum

class Colors(Enum):
    white = "\x0300"
    black = "\x0301"
    blue = "\x0302"
    green = "\x0303"
    red = "\x0304"
    yellow = "\x0306"
    bold = "\x02"
    nogc = "\x03"
    underline = "\x1F"
    reset = "\x0F"

    def __str__(self) -> str:
        return str(self.value)
