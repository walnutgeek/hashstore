import os
import shutil

from hashstore.base_x import base_x,iseq
from hashstore.ids import Cake
from hashstore.new_db import varchar_type,Dbf
from hashstore.utils import binary_type, ensure_bytes, Stringable,\
    EnsureIt,ensure_directory


import logging
import hashlib


log = logging.getLogger(__name__)

MAX_NUM_OF_SHARDS = 8192
b36 = base_x(36)


def is_it_shard(shard_name):
    '''
    Test if directory name is can represent shard

    >>> is_it_shard('668')
    True
    >>> is_it_shard('6bk')
    False
    >>> is_it_shard('0')
    True

    logic should not be sensitive for upper case:
    >>> is_it_shard('5BK')
    True
    >>> is_it_shard('6BK')
    False
    >>> is_it_shard('')
    True
    >>> is_it_shard('.5k')
    False
    >>> is_it_shard('abcd')
    False
    '''
    shard_num = -1
    if len(shard_name) < 4:
        try:
            shard_num = b36.decode_int(shard_name.lower())
        except:
            pass
    return shard_num >= 0 and shard_num < MAX_NUM_OF_SHARDS


class ContentAddress(Stringable, EnsureIt):
    '''
    Content Address

    >>> a46 = Cake.from_bytes(b'a' * 46)
    >>> str(a46)
    '1mXcPcYpN8zZYdpM04hafWih3o1NQbr4q5bJtPYPq7Ev'
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
    '12XapfdmlTbFk68YtOwlzH6hoO8IaV3KOkPG9Ng33FXv'
    >>> from_id.match(a47)
    False
    '''
    def __init__(self, hash_or_cake_or_str):
        if hasattr(hash_or_cake_or_str, 'digest'):
            self.hash_bytes = hash_or_cake_or_str.digest()
            self._id = b36.encode(self.hash_bytes)
        elif isinstance(hash_or_cake_or_str, Cake):
            self.hash_bytes = hash_or_cake_or_str.hash_bytes()
            self._id = b36.encode(self.hash_bytes)
        else:
            self._id = hash_or_cake_or_str.lower()
            self.hash_bytes = b36.decode(self._id)
        b1, b2 = iseq(self.hash_bytes[:2])
        self.modulus = (b1*256+b2) % MAX_NUM_OF_SHARDS
        self.shard_name = b36._encode_int(self.modulus)

    def __str__(self):
        return self._id

    def __repr__(self):
        return "ContentAddress(%r)" % self.__str__()

    def match(self, cake):
        return cake.hash_bytes() == self.hash_bytes

    def __eq__(self, other):
        return isinstance(other, ContentAddress) and \
               self._id == other._id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._id)

ContentAddress_TYPE = varchar_type(ContentAddress)




