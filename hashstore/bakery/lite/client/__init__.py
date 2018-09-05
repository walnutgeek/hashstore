
from hashstore.bakery.lite.mixins import (
    Cdt, Udt, ServersMixin, Singleton,  GuidPk, NameIt, DirSingleton,
    ReprIt)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean

from typing import Any

from hashstore.bakery import Cake, CakePath
from hashstore.utils.db import IntCast,StringCast
import enum


ClientConfigBase:Any = declarative_base(name='ClientConfigBase')

class ClientKey(Singleton, Cdt, Udt, ClientConfigBase):
    pass

class Server(ServersMixin, ClientConfigBase):
    pass


class MountSession(NameIt, GuidPk, Cdt, Udt, ClientConfigBase):
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


class DirKey(DirSingleton, ScanBase):
    last_backup_path = Column(StringCast(CakePath), nullable=True)


class DirEntry(NameIt, ReprIt, ScanBase):
    name = Column(String, primary_key=True)
    file_type = Column(IntCast(FileType), nullable=False)
    cake = Column(StringCast(Cake), nullable=False)
    size = Column(Integer, nullable=True)
    modtime = Column(Integer, nullable=True)
