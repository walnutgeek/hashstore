from typing import Any, Type

from hashstore.utils.db import StringCast
from hashstore.bakery import (Cake, CakeRole, CakeType)
import datetime
from sqlalchemy import Column, DateTime, String, Integer
from sqlalchemy.ext.declarative import declared_attr
from hashstore.utils import from_camel_case_to_underscores
from hashstore.utils.hashing import SaltedSha


class ReprIt:
    def __repr__(self):
        vals = ', '.join( f'{c.name}={repr(getattr(self, c.name))}'
                                for c in self.__table__.c)
        return f'<<table:{self.__tablename__} {vals}>>'


class NameIt(object):

    @declared_attr
    def __tablename__(cls):
        s = cls.__name__
        strip = from_camel_case_to_underscores(s)
        return strip


class GuidPk:
    id = Column(StringCast(Cake), primary_key=True)


def GuidPkWithDefault(role:CakeRole=None, type:CakeType=None):
    class GuidPk:
        id = Column(
            StringCast(Cake), primary_key=True,
            default=lambda : Cake.new_portal(role, type))
    return GuidPk

GuidPkWithSynapsePortalDefault:Any =GuidPkWithDefault(
    CakeRole.SYNAPSE, CakeType.PORTAL)

class Cdt:
    created_dt = Column(DateTime, nullable=False,
                        default=datetime.datetime.utcnow)


class Udt:
    updated_dt = Column(DateTime, nullable=True,
                        onupdate=datetime.datetime.utcnow)


class ServersMixin(NameIt, Cdt, Udt):
    id = Column(StringCast(Cake), primary_key=True)
    server_url = Column(String)
    secret = Column(StringCast(SaltedSha), nullable=False)


def newSingleton(ks=CakeType.PORTAL):
    new_dmount = lambda: Cake.new_portal(CakeRole.NEURON, ks)
    class NewSingleton(NameIt, ReprIt):
        single = Column(Integer,primary_key=True, default=1)
        id = Column(StringCast(Cake), nullable=False,
                    default=new_dmount)
    return NewSingleton

Singleton = newSingleton()

DirSingleton = newSingleton(CakeType.DMOUNT)