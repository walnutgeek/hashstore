from sqlalchemy import Enum, Integer, Column, String
from sqlalchemy.ext.declarative import declarative_base
from hashstore.ndb.mixins import ReprIt, NameIt, Singleton
from hashstore.bakery import Cake
from hashstore.ndb import StringCast
import enum

Base = declarative_base()


class FileType(enum.Enum):
    DIR = 0
    FILE = 1


class DirEntry(NameIt, ReprIt, Base):
    name = Column(String, primary_key=True)
    file_type = Column(Enum(FileType), nullable=False)
    cake = Column(StringCast(Cake))
    size = Column(Integer)
    modtime = Column(Integer)


class DirKey(Singleton, Base):
    pass
