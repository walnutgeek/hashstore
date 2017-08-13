from hashstore.ndb.mixins import ReprIt, NameIt, Cdt, Udt, \
    GuidPk, Singleton
from hashstore.ids import Cake_TYPE, SSHA_TYPE, Cake
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column, String, Integer

Base = declarative_base()


class ServerKey(Singleton,Base):
    secret = Column(Cake_TYPE, default=Cake.new_guid())
    port = Column(Integer, nullable=False)


class Session(GuidPk, NameIt, Cdt, Udt, ReprIt, Base):
    user = Column(Cake_TYPE, nullable=False)
    client = Column(SSHA_TYPE, nullable= True)
    host = Column(String, nullable=True)
    active = Column(Boolean, nullable=False)
