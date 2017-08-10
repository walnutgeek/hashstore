from hashstore.ids import Cake_TYPE, Cake
import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declared_attr
from hashstore.utils import from_camel_case_to_underscores


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
    id = Column(Cake_TYPE, primary_key=True,
                default=Cake.new_guid)


class Cdt:
    created_dt = Column(DateTime, nullable=False,
                        default=datetime.datetime.utcnow)


class Udt:
    updated_dt = Column(DateTime, nullable=True,
                        onupdate=datetime.datetime.utcnow)
