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
from sqlalchemy import and_,ForeignKey, Column, String, Boolean, desc
from hashstore.ndb.mixins import ReprIt, GuidPk, Cdt, Udt, \
    NameIt, ServersMixin
from hashstore.ndb import StringCast, IntCast
from hashstore.bakery import Cake, SaltedSha
from hashstore.utils import Stringable, EnsureIt

import enum

doctest=True

Base = GlueBase = declarative_base(name='GlueBase')


class PermissionType(enum.Enum):
    '''
    >>> PermissionType.Read_.info()
    'code:0 needs_cake expands->Read_'

         Read data identified by Cake which could be ether data or
         portal

    >>> PermissionType.Read_Any_Data.info()
    'code:1  expands->Read_Any_Data'

        Allows to read any data existing content based `Cake`.

    >>> PermissionType.Write_Any_Data.info()
    'code:2  expands->Read_Any_Data,Write_Any_Data'

        Allows to write any data and generate new content based `Cake`s.

    >>> PermissionType.Edit_Portal_.info()
    'code:3 needs_cake expands->Edit_Portal_,Read_,Read_Any_Data,Write_Any_Data'

        you can write any data, and edit portal to point to it.

    >>> PermissionType.Create_Portals.info()
    'code:4  expands->Create_Portals,Read_Any_Data,Write_Any_Data'

        Allows to create new portals. For all portals created
        `Own_Portal_` pemission will be assigned to the user.
    
    >>> PermissionType.Own_Portal_.info()
    'code:5 needs_cake expands->Edit_Portal_,Own_Portal_,Read_,Read_Any_Data,Write_Any_Data'

        read, write and grant rights to that portal

    >>> PermissionType.Read_Any_Portal.info()
    'code:6  expands->Read_Any_Portal'

        read any existing portal assuming that you know that
        portal's `Cake`

    >>> PermissionType.Admin.info()
    'code:42  expands->Admin,Create_Portals,Read_Any_Data,Read_Any_Portal,Write_Any_Data'

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

    def needs_cake(self):
        return self.name[-1] == '_'

    def info(self):
        expands = ','.join(sorted(map(lambda e: e.name, self.expand())))
        needs_cake = 'needs_cake' if self.needs_cake() else ''
        return "code:%d %s expands->%s" % (
            self.value, needs_cake, expands)


PermissionType.Write_Any_Data.expand_to = (
    PermissionType.Read_Any_Data,
    )
PermissionType.Edit_Portal_.expand_to = (
    PermissionType.Read_,
    PermissionType.Write_Any_Data,
    )
PermissionType.Create_Portals.expand_to = (
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


class User(GuidPk, NameIt, Cdt, Udt, ReprIt, GlueBase):
    email= Column(String, nullable=False)
    user_state = Column(IntCast(UserState), nullable=False)
    passwd = Column(StringCast(SaltedSha), nullable=False)
    full_name = Column(String, nullable=True)
    permissions = relationship(
        "Permission",
        order_by="Permission.id",
        back_populates = "user")

    def acls(self):
        if not hasattr(self, '_acls'):
            self._acls = set()
            for p in self.permissions:
                self._acls.update(p.expanded_acls())
        return self._acls


class Portal(GuidPk, NameIt, Cdt, Udt, GlueBase):
    latest = Column(StringCast(Cake), nullable=True)
    portal_type = Column(IntCast(PortalType), nullable=False,
                         default=PortalType.content)
    active = Column(Boolean, default=True)
    history = relationship("PortalHistory",
                           order_by=desc("PortalHistory.created_dt"),
                           back_populates = "portal")
    servers = relationship('Server', secondary="service_home")


class PortalHistory(GuidPk, NameIt, Cdt, GlueBase):
    portal_id = Column(None, ForeignKey('portal.id'))
    modified_by = Column(None, ForeignKey('user.id'))
    cake = Column(StringCast(Cake), nullable=False)
    portal = relationship("Portal", back_populates="history")


class Permission(GuidPk, NameIt, Cdt, Udt, GlueBase):
    user_id = Column(None, ForeignKey('user.id'))
    cake = Column(StringCast(Cake), nullable=True)
    permission_type = Column(IntCast(PermissionType), nullable=False)
    user = relationship("User", back_populates="permissions")

    def expanded_acls(self):
        for pt in self.permission_type.expand():
            yield Acl(None, pt, self.cake)


class Server(ServersMixin, GlueBase):
    seen_by = Column(None,ForeignKey('server.id'))
    services = relationship('Portal', secondary="service_home")


class ServiceHome(NameIt, GlueBase):
    server_id = Column(None, ForeignKey("server.id"), primary_key=True)
    service_id = Column(None, ForeignKey("portal.id"), primary_key=True)


class Acl(Stringable,EnsureIt):
    '''

    >>> wad = Acl('Write_Any_Data')
    >>> wad
    Acl('Write_Any_Data')

    >>> Acl('Read_')
    Traceback (most recent call last):
    ...
    ValueError: cake field is required for permission: Read_

    >>> r1 = Acl('Read_:1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV')
    >>> r1
    Acl('Read_:1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV')

    >>> wad != r1
    True

    '''
    def __init__(self, s, _pt=None, _cake=None):
        if s is None:
            self.permission_type = _pt
            self.cake = None
            if self.permission_type.needs_cake():
                self.cake = _cake
        else:
            p = s.split(':',2)
            self.permission_type = PermissionType[p[0]]
            self.cake = Cake.ensure_it(p[1]) if len(p) == 2 else None
        if self.permission_type.needs_cake() and self.cake is None:
            raise ValueError(
                'cake field is required for permission: %s'
                % self.permission_type.name)

    @staticmethod
    def cake_acls( cake, permission_types):
        return [Acl(None, pt, cake) for pt in permission_types]

    def __str__(self):
        tail = '' if self.cake is None else ':%s' % self.cake
        return self.permission_type.name + tail

    def __hash__(self):
        return hash(str(self))

    def __eq__(self,other):
        return str(self) == str(other)

    def __ne__(self,other):
        return str(self) != str(other)

    def condition(self):
        c = Permission.permission_type == self.permission_type
        return c if self.cake is None else \
            and_(c,Permission.cake == self.cake)
