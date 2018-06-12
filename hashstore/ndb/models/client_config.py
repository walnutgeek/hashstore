from typing import Any

from hashstore.ndb.mixins import Cdt, Udt, ServersMixin, Singleton, \
    GuidPk, NameIt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey, Boolean

Base:Any = declarative_base(name='ClientConfigBase')
ClientConfigBase:Any = Base

class ClientKey(Singleton, Cdt, Udt, ClientConfigBase):
    pass

class Server(ServersMixin, ClientConfigBase):
    pass


class MountSession(NameIt, GuidPk, Cdt, Udt, ClientConfigBase):
    path = Column(String, index=True, nullable=False, unique=True)
    username = Column(String, nullable=False)
    server_id = Column(None, ForeignKey('server.id'), nullable=False)
    default = Column(Boolean, default=False)
