from threading import Timer, Thread, RLock
from socket import socket

class Settings:

    RUNNING_TIMERS: list[Timer]     = []
    RUNNING_THREADS: list[Thread]   = []
    RUNNING_SOCKETS: list[socket]   = []
    PERIODIC_FUNC: dict[object]     = {}
    LOCK: RLock                     = RLock()

    CONSOLE: bool                   = False

    USER_MODES: list[str]           = []
