from hashstore.ndb.mixins import Cdt, Udt, ServersMixin, Singleton
from hashstore.ids import Cake_TYPE
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey

Base = declarative_base()

class ClientKey(Singleton, Cdt, Udt, Base):
    remote_session = Column(Cake_TYPE, nullable=True)
    server = Column(None, ForeignKey('server.id'), nullable=True )
    username = Column(String,nullable=True)

class Server(ServersMixin, Base):
    pass

