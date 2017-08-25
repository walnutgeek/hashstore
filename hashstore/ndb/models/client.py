from hashstore.ndb.mixins import Cdt, Udt, ServersMixin, Singleton, \
    GuidPk, NameIt
from hashstore.bakery.ids import Cake
from hashstore.ndb import StringCast
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey

Base = declarative_base()


class ClientKey(Singleton, Cdt, Udt, Base):
    private_cake = Column(StringCast(Cake), nullable=True)


class Server(ServersMixin, Base):
    pass


class MountSession(NameIt, GuidPk, Cdt, Udt, Base):
    path = Column(String, index=True, nullable=False, unique=True)
    username = Column(String, nullable=False)
    server_id = Column(None, ForeignKey('server.id'), nullable=False)