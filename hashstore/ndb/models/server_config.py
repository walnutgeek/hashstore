from typing import Any

from hashstore.ndb.mixins import ReprIt, NameIt, Cdt, Udt, \
    GuidPk, Singleton, GuidPkWithSynapsePortalDefault
from hashstore.bakery import Cake
from hashstore.utils.hashing import SaltedSha, InetAddress
from hashstore.ndb import StringCast

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column, String, Integer

Base:Any = declarative_base(name='ServerConfigBase')
ServerConfigBase:Any = Base


class ServerKey(Singleton, ServerConfigBase):
    secret = Column(StringCast(Cake), default=Cake.new_portal())
    external_ip = Column(StringCast(InetAddress), nullable=True)
    port = Column(Integer, nullable=False)
    num_cake_shards = Column(Integer, nullable=False)


class UserSession(GuidPkWithSynapsePortalDefault, NameIt, Cdt, Udt,
                  ReprIt, ServerConfigBase):
    user = Column(StringCast(Cake), nullable=False)
    client = Column(StringCast(SaltedSha), nullable= True)
    remote_host = Column(String, nullable=True)
    active = Column(Boolean, nullable=False)


class DirMount(NameIt, GuidPk, Cdt, Udt, ReprIt, ServerConfigBase):
    path = Column(String, index=True, nullable=False, unique=True)
