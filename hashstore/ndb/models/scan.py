from hashstore.ndb.mixins import ReprIt, NameIt, Singleton
from hashstore.bakery.ids import Cake
from hashstore.ndb import IntCast,StringCast
import enum

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer

Base = declarative_base()


class FileType(enum.Enum):
    DIR = 0
    FILE = 1

    def __str__(self):
        return self.name


class DirKey(Singleton,Base):
    pass


class DirEntry(NameIt, ReprIt, Base):
    name = Column(String, primary_key=True)
    file_type = Column(IntCast(FileType), nullable=False)
    cake = Column(StringCast(Cake), nullable=False)
    size = Column(Integer, nullable=True)
    modtime = Column(Integer, nullable=True)
