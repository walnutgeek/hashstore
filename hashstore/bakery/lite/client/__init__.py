
from hashstore.bakery.lite.mixins import (
    Cdt, Udt, ServersMixin, Singleton, CakePk, NameIt, DirSingleton,
    ReprIt)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean

from typing import Any

from hashkernel.bakery import Cake, CakePath
from hashstore.utils.db import IntCast,StringCast
import enum


ClientConfigBase:Any = declarative_base(name='ClientConfigBase')


class ClientKey(Singleton, Cdt, Udt, ClientConfigBase):
    pass


class Server(ServersMixin, ClientConfigBase):
    pass


class MountSession(NameIt, CakePk, Cdt, Udt, ClientConfigBase):
    path = Column(String, index=True, nullable=False, unique=True)
    username = Column(String, nullable=False)
    server_id = Column(None, ForeignKey('server.id'), nullable=False)
    default = Column(Boolean, default=False)


ScanBase:Any = declarative_base(name='ScanBase')


class FileType(enum.Enum):
    DIR = 0
    FILE = 1

    def __str__(self):
        return self.name


# class DirKey(DirSingleton, ScanBase):
#     last_backup_path = Column(StringCast(CakePath), nullable=True)
#
# class DirPath(ScanBase):
#     id = Column(Integer, primary_key=True)
#     path = Column(String, nullable=False)
#     cake_path = Column(StringCast(CakePath), nullable=False)
#     cake = Column(StringCast(Cake), nullable=True)
#
# class DirEntry(NameIt, ReprIt, ScanBase):
#     path_id = Column(None, ForeignKey('dir_path.id'), primary_key=True)
#     name = Column(String, primary_key=True)
#     file_type = Column(IntCast(FileType), nullable=False)
#     cake = Column(StringCast(Cake), nullable=False)
#     size = Column(Integer, nullable=True)
#     modtime = Column(Integer, nullable=True)


class DirKey(DirSingleton, ScanBase):
    last_backup_path = Column(StringCast(CakePath), nullable=True)


class DirEntry(NameIt, ReprIt, ScanBase):
    name = Column(String, primary_key=True)
    file_type = Column(IntCast(FileType), nullable=False)
    cake = Column(StringCast(Cake), nullable=False)
    size = Column(Integer, nullable=True)
    modtime = Column(Integer, nullable=True)
