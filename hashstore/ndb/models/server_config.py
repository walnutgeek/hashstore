from hashstore.ndb.mixins import ReprIt, NameIt, Cdt, Udt, \
    GuidPk, Singleton, GuidPkWithDefault
from hashstore.bakery import Cake, SaltedSha, InetAddress
from hashstore.ndb import StringCast

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column, String, Integer

Base = ServerConfigBase = declarative_base(name='ServerConfigBase')


class ServerKey(Singleton, ServerConfigBase):
    secret = Column(StringCast(Cake), default=Cake.new_portal())
    external_ip = Column(StringCast(InetAddress), nullable=True)
    port = Column(Integer, nullable=False)


class UserSession(GuidPkWithDefault(), NameIt, Cdt, Udt, ReprIt, ServerConfigBase):
    user = Column(StringCast(Cake), nullable=False)
    client = Column(StringCast(SaltedSha), nullable= True)
    remote_host = Column(String, nullable=True)
    active = Column(Boolean, nullable=False)


class DirMount(NameIt, GuidPk, Cdt, Udt, ReprIt, ServerConfigBase):
    path = Column(String, index=True, nullable=False, unique=True)
