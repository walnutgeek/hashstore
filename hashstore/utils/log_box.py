from typing import List

from hashstore.utils import CodeEnum
from hashstore.utils.smattr import SmAttr


class LogLevel(CodeEnum):
    INFO = 0
    WARN = 1
    ERROR = 2


class LogEntry(SmAttr):
    level: LogLevel
    msg:str

    def __str__(self):
        return f"{self.level.name()} {self.msg}\n"


class LogBox(SmAttr):
    entries: List[LogEntry]

    def add(self, level:LogLevel, msg:str):
        self.entries.append(LogEntry(level=level, msg=msg))

    def info(self, msg: str):
        self.add(LogLevel.INFO, msg)

    def warn(self, msg: str):
        self.add(LogLevel.WARN, msg)

    def error(self, msg: str):
        self.add(LogLevel.ERROR, msg)

    def has_errors(self):
        return any(e.level == LogLevel.ERROR for e in self.entries)

    def __str__(self):
        return ''.join( map(str, self.entries))
