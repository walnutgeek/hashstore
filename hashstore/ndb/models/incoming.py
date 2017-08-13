from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, Column, Boolean
from hashstore.bakery.content import ContentAddress_TYPE
from hashstore.ndb.mixins import ReprIt, NameIt, Cdt, Udt

Base = declarative_base()


class Incoming(NameIt, ReprIt, Cdt, Udt, Base):
    incoming_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(ContentAddress_TYPE, nullable=True)
    new = Column(Boolean)

incoming = Incoming.__table__

incoming_meta = Base.metadata
