from typing import List

from hashstore.kernel import CodeEnum
from hashstore.kernel.smattr import SmAttr


class LogLevel(CodeEnum):
    INFO = 0
    WARN = 1
    ERROR = 2


class LogEntry(SmAttr):
    level: LogLevel
    msg:str


class LogBox(SmAttr):
    """
    >>> lb = LogBox()
    >>> lb.has_level(LogLevel.INFO)
    False
    >>> lb.info('info message')
    >>> lb.has_errors()
    False
    >>> lb.has_level(LogLevel.INFO)
    True
    >>> lb.warn('warn message')
    >>> lb.has_errors()
    False
    >>> lb.error('error message')
    >>> lb.has_errors()
    True
    >>> lb.to_json() #doctest: +NORMALIZE_WHITESPACE
    {'entries': [{'level': 'INFO', 'msg': 'info message'},
        {'level': 'WARN', 'msg': 'warn message'},
        {'level': 'ERROR', 'msg': 'error message'}]}
    """
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
        return self.has_level(LogLevel.ERROR)

    def has_level(self, level):
        return any(e.level == level for e in self.entries)

