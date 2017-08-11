from hashstore.bakery.db_mixins import ReprIt, NameIt, Cdt, Udt
from hashstore.ids import Cake_TYPE, SSHA_TYPE
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, Column, String

Base = declarative_base()


class RemoteServer(NameIt, ReprIt, Cdt, Udt, Base):
    id = Column(Integer, primary_key=True)
    path = Column(String, index=True, unique=True)
    server_id = Column(Cake_TYPE)
    server_url = Column(String)
    server_session = Column(SSHA_TYPE)
