from hashstore.ndb.mixins import ReprIt, NameIt, Singleton
from hashstore.bakery import Cake
from hashstore.ndb import IntCast,StringCast
import enum

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer

Base = ScanBase = declarative_base(name='ScanBase')


class FileType(enum.Enum):
    DIR = 0
    FILE = 1

    def __str__(self):
        return self.name


class DirKey(Singleton, ScanBase):
    pass


class DirEntry(NameIt, ReprIt, ScanBase):
    name = Column(String, primary_key=True)
    file_type = Column(IntCast(FileType), nullable=False)
    cake = Column(StringCast(Cake), nullable=False)
    size = Column(Integer, nullable=True)
    modtime = Column(Integer, nullable=True)
