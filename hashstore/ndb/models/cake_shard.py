import enum

import datetime
from typing import Any

from hashstore.bakery import ContentAddress, Cake
from hashstore.ndb import StringCast, IntCast
from hashstore.ndb.mixins import ReprIt, NameIt, Cdt, GuidPk, Udt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, Column, LargeBinary, ForeignKey
from sqlalchemy import and_, Column, String, Boolean, \
    DateTime, Index, Integer

from hashstore.utils import JsonWrap

Base:Any = declarative_base(name='CakeShardBase')
CakeShardBase:Any = Base


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

