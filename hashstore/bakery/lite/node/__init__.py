import datetime
import enum

from sqlalchemy.orm import relationship

from hashkernel.bakery import Cake
from hashkernel import Stringable, EnsureIt
from hashstore.utils.db import StringCast, IntCast
from hashstore.bakery.lite.mixins import (
    ReprIt, NameIt, Cdt, Udt, CakePk,  PortalPkWithSynapseDefault,
    ServersMixin, Singleton)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    LargeBinary, Column, Integer, Boolean, ForeignKey, DateTime, String,
    Index, and_)
from typing import (Union, Any, Tuple, Set)

from hashkernel.hashing import (
    HashBytes, B36, shard_num, shard_name_int, SaltedSha, InetAddress)

MAX_NUM_OF_SHARDS = 8192


class ContentAddress(Stringable, EnsureIt):
    """
    case-insensitive address that used to store blobs
    of data in file system and in db
    >>> from hashkernel.bakery import Cake
    >>> a46 = Cake.from_bytes(b'a' * 46)
    >>> str(a46)
    '2lEWHXV2XeYyZnKNyQyGPt4poJhV7VeYCfeszHnLyFtx'
    >>> from_c = ContentAddress(a46)
    >>> str(from_c)
    '2jr7e7m1dz6uky4soq7eaflekjlgzwsvech6skma3ojl4tc0zv'
    >>> from_id = ContentAddress(str(from_c))
    >>> str(from_id)
    '2jr7e7m1dz6uky4soq7eaflekjlgzwsvech6skma3ojl4tc0zv'
    >>> from_id
    ContentAddress('2jr7e7m1dz6uky4soq7eaflekjlgzwsvech6skma3ojl4tc0zv')
    >>> from_id.hash_bytes == from_c.hash_bytes
    True
    >>> from_id.match(a46)
    True
    >>> a47 = Cake.from_bytes(b'a' * 47)
    >>> str(a47)
    '21EUi09ZvZAelgu02ANS9dSpK9oPsERF0uSpfEEZcdMx'
    >>> from_id.match(a47)
    False
    """

    def __init__(self, h: Union[HashBytes, str])->None:
        if isinstance(h, HashBytes):
            self._hash_bytes = h.hash_bytes()
            self._id = B36.encode(self._hash_bytes)
        else:
            self._id = h.lower()
            self._hash_bytes = B36.decode(self._id)
        shard_n = shard_num(self._hash_bytes, MAX_NUM_OF_SHARDS)
        self.shard_name = shard_name_int(shard_n)

    def __str__(self):
        return self._id

    def __repr__(self):
        return f"{type(self).__name__}({repr(self._id)})"

    def match(self, cake):
        return cake.hash_bytes() == self._hash_bytes

    def __eq__(self, other):
        return isinstance(other, ContentAddress) and \
               self._id == other._id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._id)

    def hash_bytes(self):
        return self._hash_bytes

HashBytes.register(ContentAddress)

#--- blobs

BlobBase:Any = declarative_base(name='BlobBase')


class Blob(NameIt, ReprIt, Cdt, BlobBase):
    blob_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(StringCast(ContentAddress), nullable=False)
    content = Column(LargeBinary)


blob_meta = BlobBase.metadata


blob = Blob.__table__


IncomingBase:Any = declarative_base(name='IncomingBase')


class Incoming(NameIt, ReprIt, Cdt, Udt, IncomingBase):
    incoming_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(StringCast(ContentAddress), nullable=True)
    new = Column(Boolean)


incoming = Incoming.__table__


incoming_meta = IncomingBase.metadata

#--- cake_shard

CakeShardBase:Any = declarative_base(name='CakeShardBase')

class BackLink(CakePk, NameIt, Cdt, Udt, CakeShardBase):
    referrer = Column(StringCast(Cake), nullable=False)

class Portal(CakePk, NameIt, Cdt, Udt, CakeShardBase):
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
    size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)
    mime = Column(String, nullable=True)
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

#--- glue
'''
`glue` - Data Model

Glues all pieces of system together.

`User` linked thru `Permission`s  to `Portal`s.
`Portal` points to  hash-based content address that changes when
underlying data is changes. `PortalHistory` or `VolatileTree`
tracks changes.

Underlaying data is served as `content` or used as `service`
configuration.

`Service` can reside on multiple  `Server` specified by
`ServiceHome`.

`Server` store server network address and identity.

'''

GlueBase: Any = declarative_base(name='GlueBase')


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
    Read_ = (0, ())
    Read_Any_Data = (1, ())
    Write_Any_Data = (2, ('Read_Any_Data',))
    Edit_Portal_ = (3, ('Read_', 'Write_Any_Data'))
    Create_Portals = (4, ('Write_Any_Data',))
    Own_Portal_ = (5, ('Edit_Portal_', 'Write_Any_Data'))
    Read_Any_Portal = (6, ())
    Admin = (
    42, ('Write_Any_Data', 'Read_Any_Portal', 'Create_Portals'))

    def __init__(self, code: int, implies: Tuple[str]) -> None:
        self.code = code
        self.implies = implies
        self.expands: Set[PermissionType] = set()

    def _expand(self) -> Set['PermissionType']:
        expands = set()
        expands.add(self)
        for n in self.implies:
            pt = PermissionType[n]
            if pt not in expands:
                expands.update(pt._expand())
        return expands

    def needs_cake(self):
        return self.name[-1] == '_'

    def info(self):
        expands = ','.join(sorted(map(lambda e: e.name, self.expands)))
        needs_cake = 'needs_cake' if self.needs_cake() else ''
        return f'code:{self.code} {needs_cake} expands->{expands}'


for pt in PermissionType:
    pt.expands = pt._expand()


class UserState(enum.Enum):
    disabled = 0
    active = 1
    invitation = 2


class UserType(enum.Enum):
    guest = 0
    normal = 1
    system = 999


class User(PortalPkWithSynapseDefault, NameIt, Cdt, Udt, ReprIt,
           GlueBase):
    email = Column(String, nullable=False)
    user_state = Column(IntCast(UserState), nullable=False)
    user_type = Column(IntCast(UserType), nullable=False,
                       default=UserType.normal)
    passwd = Column(StringCast(SaltedSha), nullable=False)
    full_name = Column(String, nullable=True)
    permissions = relationship("Permission", order_by="Permission.id",
                               back_populates="user")

    def acls(self, force_refresh=False):
        if force_refresh or not hasattr(self, '_acls'):
            self._acls = set()
            for p in self.permissions:
                self._acls.update(p.expanded_acls())
        return self._acls


class Permission(PortalPkWithSynapseDefault, NameIt, Cdt, Udt,
                 GlueBase):
    user_id = Column(None, ForeignKey('user.id'))
    cake = Column(StringCast(Cake), nullable=True)
    permission_type = Column(
        IntCast(PermissionType, lambda pt: pt.code),
        nullable=False)
    user = relationship("User", back_populates="permissions")

    def expanded_acls(self):
        for pt in self.permission_type.expands:
            yield Acl(None, pt, self.cake)


class Server(ServersMixin, GlueBase):
    seen_by = Column(None, ForeignKey('server.id'))


class Acl(Stringable, EnsureIt):
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
            p = s.split(':', 2)
            self.permission_type = PermissionType[p[0]]
            self.cake = Cake.ensure_it(p[1]) if len(p) == 2 else None
        if self.permission_type.needs_cake() and self.cake is None:
            raise ValueError(
                'cake field is required for permission: %s'
                % self.permission_type.name)

    @staticmethod
    def cake_acls(cake, permission_types):
        return [Acl(None, pt, cake) for pt in permission_types]

    def __str__(self):
        tail = '' if self.cake is None else ':%s' % self.cake
        return self.permission_type.name + tail

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return str(self) != str(other)

    def condition(self):
        c = Permission.permission_type == self.permission_type
        return c if self.cake is None else \
            and_(c, Permission.cake == self.cake)

#--- server_config

ServerConfigBase:Any = declarative_base(name='ServerConfigBase')


class ServerKey(Singleton, ServerConfigBase):
    secret = Column(StringCast(Cake), default=Cake.new_portal())
    external_ip = Column(StringCast(InetAddress), nullable=True)
    port = Column(Integer, nullable=False)
    num_cake_shards = Column(Integer, nullable=False)


class UserSession(PortalPkWithSynapseDefault, NameIt, Cdt, Udt,
                  ReprIt, ServerConfigBase):
    user = Column(StringCast(Cake), nullable=False)
    client = Column(StringCast(SaltedSha), nullable= True)
    remote_host = Column(String, nullable=True)
    active = Column(Boolean, nullable=False)


class DirMount(NameIt, CakePk, Cdt, Udt, ReprIt, ServerConfigBase):
    path = Column(String, index=True, nullable=False, unique=True)
