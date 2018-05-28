import enum

import datetime

from hashstore.bakery import ContentAddress, Cake
from hashstore.ndb import StringCast, IntCast
from hashstore.ndb.mixins import ReprIt, NameIt, Cdt, GuidPk, Udt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, Column, LargeBinary, ForeignKey
from sqlalchemy import and_, Column, String, Boolean, \
    DateTime, Index, Integer

from hashstore.utils import JsonWrap

Base = CakeShardBase = declarative_base(name='CakeShardBase')


class Event(NameIt, ReprIt, Cdt, Udt, CakeShardBase):
    id = Column(StringCast(Cake), primary_key=True)
    parent_event = Column(StringCast(Cake), nullable=True)
    event_type = Column(StringCast(Cake), nullable=True)
    composite = Column(Boolean, nullable=False)
    event_state = Column(String, nullable=False)
    code_ref = Column(StringCast(Cake), nullable=True)
    meta = Column(StringCast(JsonWrap), nullable=True)


class EventComponents(NameIt, ReprIt, Cdt, CakeShardBase):
    composite_id = Column(StringCast(Cake), primary_key=True)
    component_id = Column(StringCast(Cake), primary_key=True)
    component_name = Column(String, nullable=False)


class LinkType(enum.IntEnum):
    INPUT = 1
    OUTPUT = 2


class EventDataLink(NameIt, ReprIt, Cdt, CakeShardBase):
    event_id = Column(StringCast(Cake), primary_key=True)
    link_name = Column(String, primary_key=True)
    data_id = Column(StringCast(Cake), primary_key=True)
    link_type = Column(IntCast(LinkType), primary_key=True)


class Portal(GuidPk, NameIt, Cdt, Udt, CakeShardBase):
    latest = Column(StringCast(Cake), nullable=True)
    active = Column(Boolean, nullable=False, default=True)


class PortalHistory(NameIt, Cdt, CakeShardBase):
    portal_id = Column(None, ForeignKey('portal.id'), primary_key=True)
    dt = Column(DateTime, primary_key=True,
                        default=datetime.datetime.utcnow)
    by = Column(StringCast(Cake),nullable=False)
    cake = Column(StringCast(Cake), nullable=False)


class VolatileTree(NameIt, ReprIt, CakeShardBase):
    portal_id = Column(None, ForeignKey('portal.id'), primary_key=True)
    path = Column(String, nullable=False, primary_key=True)
    parent_path = Column(String, nullable=False)
    cake = Column(StringCast(Cake), nullable=True)
    start_by = Column(StringCast(Cake),nullable=False)
    end_by = Column(StringCast(Cake),nullable=True)
    start_dt = Column(DateTime, nullable=False, primary_key=True,
                      default=datetime.datetime.utcnow)
    end_dt = Column(DateTime, nullable=True,
                    onupdate=datetime.datetime.utcnow)


Index('VolatileTree_search',
      VolatileTree.portal_id,
      VolatileTree.parent_path,
      VolatileTree.end_dt,
      VolatileTree.path)

