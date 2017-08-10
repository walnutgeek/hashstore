from sqlalchemy import Enum, Integer, Column, String
from sqlalchemy.ext.declarative import declarative_base
from hashstore.bakery.db_mixins import ReprIt, NameIt
from hashstore.ids import Cake_TYPE, Cake
import enum


Base = declarative_base()


class FileType(enum.Enum):
    DIR = 0
    FILE = 1


class DirEntry(NameIt, ReprIt, Base):
    name = Column(String, primary_key=True)
    file_type = Column(Enum(FileType), nullable=False)
    cake = Column(Cake_TYPE)
    size = Column(Integer)
    modtime = Column(Integer)


class DirKey(NameIt, ReprIt, Base):
    id = Column(Integer,primary_key=True, default=1)
    dir_id = Column(Cake_TYPE,nullable=False,default=Cake.new_guid)

