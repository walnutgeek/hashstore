'''
`glue` - Data Model

Glues all pieces of system together.

`User` linked thru `Permission`s  to `Portal`s.
`Portal` points to  hash-based content address that changes when
underlying data is changes. `PortalHistory` tracks changes.

Underlaying data is served as `content` or used as `service`
configuration.

`Service` can reside on multiple  `Server` specified by
`ServiceHome`.

`Server` store server network address and identity.

'''

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, Column, String, desc
from hashstore.ndb.mixins import ReprIt, GuidPk, Cdt, Udt, \
    NameIt, ServersMixin
from hashstore.ndb import StringCast, IntCast
from hashstore.ids import Cake, SaltedSha
import enum

doctest=True

Base = declarative_base()


class PermissionType(enum.Enum):
    '''
    >>> PermissionType.Read_.info()
    'code:0 expands->Read_'

         Read data identified by Cake which could be ether data or
         portal

    >>> PermissionType.Read_Any_Data.info()
    'code:1 expands->Read_Any_Data'

        Allows to read any data existing content based `Cake`.

    >>> PermissionType.Write_Any_Data.info()
    'code:2 expands->Read_Any_Data,Write_Any_Data'

        Allows to write any data and generate new content based `Cake`s.

    >>> PermissionType.Edit_Portal_.info()
    'code:3 expands->Edit_Portal_,Read_,Read_Any_Data,Write_Any_Data'

        you can write any data, and edit portal to point to it.

    >>> PermissionType.Create_Portals.info()
    'code:4 expands->Create_Portals'

        Allows to create new portals. For all portals created
        `Own_Portal_` pemission will be assigned to the user.
    
    >>> PermissionType.Own_Portal_.info()
    'code:5 expands->Edit_Portal_,Own_Portal_,Read_,Read_Any_Data,Write_Any_Data'

        read, write and grant rights to that portal

    >>> PermissionType.Read_Any_Portal.info()
    'code:6 expands->Read_Any_Portal'

        read any existing portal assuming that you know that
        portal's `Cake`
    
    >>> PermissionType.Admin.info()
    'code:42 expands->Admin,Create_Portals,Read_Any_Data,Read_Any_Portal,Write_Any_Data'

        can read, write create portals and grant rights to anything

    '''
    Read_ = 0
    Read_Any_Data = 1
    Write_Any_Data = 2
    Edit_Portal_ = 3
    Create_Portals = 4
    Own_Portal_ = 5
    Read_Any_Portal = 6
    Admin = 42

    def expand(self):
        expands = set()
        expands.add(self)
        if hasattr(self, 'expand_to'):
            for e in self.expand_to:
                if e not in expands:
                    expands.update( e.expand() )
        return expands

    def info(self):
        expands = ','.join(sorted(map(lambda e: e.name, self.expand())))
        return "code:%d expands->%s" % (self.value, expands)


PermissionType.Write_Any_Data.expand_to = (
    PermissionType.Read_Any_Data,
    )
PermissionType.Edit_Portal_.expand_to = (
    PermissionType.Read_,
    PermissionType.Write_Any_Data,
    )
PermissionType.Own_Portal_.expand_to = (
    PermissionType.Edit_Portal_,
    PermissionType.Write_Any_Data,
    )
PermissionType.Admin.expand_to = (
    PermissionType.Write_Any_Data,
    PermissionType.Create_Portals,
    PermissionType.Read_Any_Portal,
    )


class UserState(enum.Enum):
    disabled = 0
    active = 1
    invitation = 2


class PortalType(enum.IntEnum):
    content = 0
    service = 1


class User(GuidPk, NameIt, Cdt, Udt, ReprIt, Base):
    email= Column(String, nullable=False)
    user_state = Column(IntCast(UserState), nullable=False)
    passwd = Column(StringCast(SaltedSha), nullable=False)
    full_name = Column(String, nullable=True)
    permissions = relationship( "Permission",
        order_by = ("Permission.id"),
        back_populates = "user")


class Portal(GuidPk, NameIt, Cdt, Udt, Base):
    latest = Column(StringCast(Cake), nullable=True)
    portal_type = Column(IntCast(PortalType), nullable=False,
                         default=PortalType.content)
    permissions = relationship("Permission",
                              back_populates = "portal")
    history = relationship("PortalHistory",
                           order_by=desc("PortalHistory.created_dt"),
                           back_populates = "portal")
    servers = relationship('Server', secondary="service_home")


class PortalHistory(GuidPk, NameIt, Cdt, Base):
    portal_id = Column(None, ForeignKey('portal.id'))
    modified_by = Column(None, ForeignKey('user.id'))
    cake = Column(StringCast(Cake), nullable=False)
    portal = relationship("Portal", back_populates="history")


class Permission(GuidPk, NameIt, Cdt, Udt, Base):
    portal_id = Column(None, ForeignKey('portal.id'),nullable=True)
    user_id = Column(None, ForeignKey('user.id'))
    cake = Column(StringCast(Cake), nullable=True)
    permission_type = Column(IntCast(PermissionType), nullable=False)
    user = relationship("User", back_populates="permissions")
    portal = relationship("Portal", back_populates="permissions")


class Server(ServersMixin, Base):
    seen_by = Column(None,ForeignKey('server.id'))
    services = relationship('Portal', secondary="service_home")


class ServiceHome(NameIt,Base):
    server_id = Column(None, ForeignKey("server.id"), primary_key=True)
    service_id = Column(None, ForeignKey("portal.id"), primary_key=True)
