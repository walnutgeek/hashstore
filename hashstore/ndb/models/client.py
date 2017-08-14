from hashstore.ndb.mixins import Cdt, Udt, ServersMixin, Singleton
from hashstore.ids import Cake
from hashstore.ndb import StringCast
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey

Base = declarative_base()

class ClientKey(Singleton, Cdt, Udt, Base):
    remote_session = Column(StringCast(Cake), nullable=True)
    server = Column(None, ForeignKey('server.id'), nullable=True )
    username = Column(String,nullable=True)

class Server(ServersMixin, Base):
    pass

