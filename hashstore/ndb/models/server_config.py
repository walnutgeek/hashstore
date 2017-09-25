from hashstore.ndb.mixins import ReprIt, NameIt, Cdt, Udt, \
    GuidPk, Singleton
from hashstore.bakery.ids import Cake, SaltedSha, InetAddress
from hashstore.ndb import StringCast

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column, String, Integer

Base = ServerConfigBase = declarative_base(name='ServerConfigBase')


class ServerKey(Singleton, ServerConfigBase):
    secret = Column(StringCast(Cake), default=Cake.new_guid())
    external_ip = Column(StringCast(InetAddress), nullable=True)
    port = Column(Integer, nullable=False)


class UserSession(GuidPk, NameIt, Cdt, Udt, ReprIt, ServerConfigBase):
    user = Column(StringCast(Cake), nullable=False)
    client = Column(StringCast(SaltedSha), nullable= True)
    remote_host = Column(String, nullable=True)
    active = Column(Boolean, nullable=False)

