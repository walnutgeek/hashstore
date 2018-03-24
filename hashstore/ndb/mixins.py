from hashstore.ndb import StringCast
from hashstore.bakery import Cake, SaltedSha, Role
import datetime
from sqlalchemy import Column, DateTime, String, Integer
from sqlalchemy.ext.declarative import declared_attr
from hashstore.utils import from_camel_case_to_underscores

new_bundle_guid = lambda: Cake.new_portal(Role.NEURON)


class ReprIt:
    def __repr__(self):
        vals = ', '.join( '%s=%r' % (c.name, getattr(self, c.name))
                                for c in self.__table__.c)
        return '<<table:%s %s>>' % ( self.__tablename__, vals)


class NameIt(object):

    @declared_attr
    def __tablename__(cls):
        s = cls.__name__
        strip = from_camel_case_to_underscores(s)
        return strip


class GuidPk:
    id = Column(StringCast(Cake), primary_key=True,
                default=Cake.new_portal)


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


class Singleton(NameIt, ReprIt):
    single = Column(Integer,primary_key=True, default=1)
    id = Column(StringCast(Cake), nullable=False, default=new_bundle_guid)
