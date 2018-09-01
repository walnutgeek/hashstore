from hashstore.ndb import StringCast
from hashstore.ndb.mixins import ReprIt, NameIt, Cdt, Udt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import LargeBinary, Column, Integer, Boolean
from typing import (Union, Any)

from hashstore.utils import (Stringable, EnsureIt)
from hashstore.utils.hashing import (HashBytes, B36, shard_num,
                                     shard_name_int)
MAX_NUM_OF_SHARDS = 8192


class ContentAddress(Stringable, EnsureIt):
    """
    case-insensitive address that used to store blobs
    of data in file system and in db
    >>> from hashstore.bakery import Cake
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
            self.hash_bytes = h.hash_bytes()
            self._id = B36.encode(self.hash_bytes)
        else:
            self._id = h.lower()
            self.hash_bytes = B36.decode(self._id)
        shard_n = shard_num(self.hash_bytes, MAX_NUM_OF_SHARDS)
        self.shard_name = shard_name_int(shard_n)

    def __str__(self):
        return self._id

    def __repr__(self):
        return f"{type(self).__name__}({repr(self._id)})"

    def match(self, cake):
        return cake.hash_bytes() == self.hash_bytes

    def __eq__(self, other):
        return isinstance(other, ContentAddress) and \
               self._id == other._id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._id)


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
