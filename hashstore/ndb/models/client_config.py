from hashstore.ndb.mixins import Cdt, Udt, ServersMixin, Singleton, \
    GuidPk, NameIt
from hashstore.bakery.ids import Cake
from hashstore.ndb import StringCast
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey

Base = ClientConfigBase = declarative_base(name='ClientConfigBase')


class ClientKey(Singleton, Cdt, Udt, ClientConfigBase):
    pass

class Server(ServersMixin, ClientConfigBase):
    pass


class MountSession(NameIt, GuidPk, Cdt, Udt, ClientConfigBase):
    path = Column(String, index=True, nullable=False, unique=True)
    username = Column(String, nullable=False)
    server_id = Column(None, ForeignKey('server.id'), nullable=False)
