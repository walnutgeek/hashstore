import hashlib
import os

import six
import sys

import hashstore.base_x as bx
import hashstore.utils as utils
import json
import enum

import logging
log = logging.getLogger(__name__)

BASE_ENCODING = bx.base_x(58)
TINY_ENCODING = bx.base_x(36)

class ID_Structure(enum.IntEnum):
    INLINE = 0
    SHA256 = 1
    GUID256 = 2
    TINYNAME = 3


class DataType(enum.IntEnum):
    JUST_DATA = 0
    WDF = 1
    CSV = 2
    TXT_WITH_CAKEURLS = 3


inline_max_bytes=33


def NOP_process_buffer(read_buffer):
    '''
    Does noting

    >>> NOP_process_buffer(b'')

    :param read_buffer: take bytes
    :return: nothing
    '''
    pass

if bytes == str:  # python2
    to_byte = chr
    to_int = ord
else:  # python3
    to_byte = lambda code: bytes([code])
    to_int = lambda b : b


def _header(id_structure,data_type):
    '''
    >>> _header(ID_Structure.INLINE,DataType.JUST_DATA)
    0
    >>> _header(ID_Structure.SHA256,DataType.TXT_WITH_CAKEURLS)
    49
    '''
    return (data_type.value << 4) | id_structure.value

def pack(id_structure, data_type, data_bytes):
    r'''
    >>> pack(ID_Structure.INLINE,DataType.JUST_DATA, b'ABC')
    b'\x00ABC'
    >>> pack(ID_Structure.SHA256,DataType.TXT_WITH_CAKEURLS,b'XYZ')
    b'1XYZ'
    '''
    return to_byte(_header(id_structure, data_type)) + data_bytes

def quick_hash(data):
    r'''
    Calculate hash on data buffer passed

    >>> quick_hash(b'abc')
    b'\xbax\x16\xbf\x8f\x01\xcf\xeaAA@\xde]\xae"#\xb0\x03a\xa3\x96\x17z\x9c\xb4\x10\xffa\xf2\x00\x15\xad'
    >>> quick_hash(u'abc')
    b'\xbax\x16\xbf\x8f\x01\xcf\xeaAA@\xde]\xae"#\xb0\x03a\xa3\x96\x17z\x9c\xb4\x10\xffa\xf2\x00\x15\xad'
    >>> quick_hash(5.7656)
    b'\x8e\x19\x10\xddb\xc3)\x84~i>\xbeL\x8a\x08\x96\x96\xa5sR0\x8c\x7f\xd7\xec\x0fa\x12\xfbA\xb9\xa3'
    >>> quick_hash('5.7656')
    b'\x8e\x19\x10\xddb\xc3)\x84~i>\xbeL\x8a\x08\x96\x96\xa5sR0\x8c\x7f\xd7\xec\x0fa\x12\xfbA\xb9\xa3'

    :param data: in bytes, or if not it will be converted to string first
                 and then to byte
    :return: digest
    '''
    return hashlib.sha256(utils.ensure_bytes(data)).digest()


def process_stream(fd,  process_buffer=NOP_process_buffer, chunk_size=65355):
    '''
    process stream to calculate hash, length of data,
    and if it is smaller then hash size, holds on to stream
    content to use it instead of hash.
    It allows
    :param fd: stream
    :param process_buffer: function  called on every chan
    :return:
    '''
    inline_data = six.binary_type()
    digest = hashlib.sha256()
    length = 0
    while True:
        read_buffer = fd.read(chunk_size)
        if len(read_buffer) <= 0:
            break
        length += len(read_buffer)
        digest.update(read_buffer)
        process_buffer(read_buffer)
        if length < inline_max_bytes:
            inline_data += read_buffer
    fd.close()
    if length >= inline_max_bytes:
        inline_data = None
    return digest.digest(), length, inline_data


class CAKe(utils.Stringable,utils.EnsureIt):
    '''
    Stands for Unique Data Key.

    It is content adressing scheme useing SHA256. For small
    content data is embeded in UDK using base64 encoding.

    >>> short_content = b'The quick brown fox jumps over'
    >>> short_udk = CAKe.from_string(short_content)
    >>> short_udk.has_data()
    True
    >>> short_udk.data() is not None
    True
    >>> short_udk.data() == short_content
    True

    In string representation there is 'M' in the beginging. It is used
    to mark that data packed inside of UDK.

    >>> str(short_udk)
    '1HuxUyn9dhY6MAdbABFto2Xu8k57zZD3GTt6v6hSx9'

    For longer content SHA256 hexdigest is used:

    >>> longer_content = b'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    >>> longer_udk = CAKe.from_string(longer_content)
    >>> longer_udk.has_data()
    False
    >>> longer_udk.data() is None
    True
    >>> str(longer_udk)
    'UQWZRF3zkgv5qwPNBjXD6DwqNYXYeDJAxbnFhizLM1Le'

    '''
    def __init__(self, s, id_structure = None, data_type = None):
        if id_structure is not None:
            self.digest = s
            self.id_structure = id_structure
            self.data_type = data_type
        else:
            decoded = BASE_ENCODING.decode(utils.ensure_string(s))
            header = to_int(decoded[0])
            self.digest = decoded[1:]
            self.id_structure = ID_Structure(header & 0x0F)
            self.data_type = DataType(header >> 4)
        if self.id_structure not in (ID_Structure.INLINE, ID_Structure.TINYNAME):
            l = len(self.digest)
            if l != 32:
                 raise ValueError('invalid CAKey: %r ' % s)

    @staticmethod
    def from_digest_and_inline_data(digest, buffer, data_type = DataType.JUST_DATA):
        if buffer is not None and len(buffer) < inline_max_bytes:
            return CAKe(buffer, id_structure=ID_Structure.INLINE,
                        data_type=data_type)
        else:
            return CAKe(digest, id_structure=ID_Structure.SHA256,
                        data_type=data_type)

    @staticmethod
    def from_stream(fd, data_type = DataType.JUST_DATA):
        digest, _, inline_data = process_stream(fd)
        return CAKe.from_digest_and_inline_data(digest, inline_data,
                                                data_type = data_type)

    @staticmethod
    def from_string(s, data_type = DataType.JUST_DATA):
        return CAKe.from_stream(six.BytesIO(utils.ensure_bytes(s)),
                                data_type = data_type)
    @staticmethod
    def from_file(file, data_type = DataType.JUST_DATA):
        return CAKe.from_stream(open(file, 'rb'), data_type = data_type)

    @staticmethod
    def guid(data_type = DataType.JUST_DATA):
        return CAKe(os.urandom(32), id_structure=ID_Structure.GUID256,
                    data_type = data_type)

    def __str__(self):
        return BASE_ENCODING.encode(pack(self.id_structure,
                                         self.data_type,self.digest))

    def __hash__(self):
        if not(hasattr(self, '_hash')):
            self._hash = hash(self.digest)
        return self._hash

    def has_data(self):
        return self.id_structure==ID_Structure.INLINE

    def data(self):
        return self.digest if self.has_data() else None

    def __eq__(self, other):
        if not isinstance(other, CAKe):
            return False
        return self.digest == other.digest and \
               self.id_structure == other.id_structure and \
               self.data_type == other.data_type

    def __ne__(self, other):
        return not self.__eq__(other)

#
# class UDKBundle(utils.Jsonable):
#     '''
#     sorted dictionary of names and corresponding UDKs
#
#     >>> short_udk = UDK.from_string('The quick brown fox jumps over the lazy dog')
#     >>> longer_udk = UDK.from_string('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')
#
#     >>> udks = UDKBundle()
#     >>> udks['short'] = short_udk
#     >>> udks['longer'] = longer_udk
#     >>> len(udks)
#     2
#
#     >>> udks.keys()
#     ['longer', 'short']
#     >>> udks_udk, size, content = udks.udk_content()
#     >>> str(udks_udk)
#     'X4453e495c259e32294f47a8592b5c187901c9ea13bdcc517e0994aa6f556986d'
#     >>> content
#     '[["longer", "short"], ["973153f86ec2da1748e63f0cf85b89835b42f8ee8018c549868a1308a19f6ca3", "MVGhlIHF1aWNrIGJyb3duIGZveCBqdW1wcyBvdmVyIHRoZSBsYXp5IGRvZw=="]]'
#     >>> no_bundle_marker = udks_udk.strip_bundle()
#     >>> str(no_bundle_marker)
#     '4453e495c259e32294f47a8592b5c187901c9ea13bdcc517e0994aa6f556986d'
#     >>> udks_udk == no_bundle_marker
#     True
#     >>> str(no_bundle_marker.ensure_bundle())
#     'X4453e495c259e32294f47a8592b5c187901c9ea13bdcc517e0994aa6f556986d'
#
#     '''
#     def __init__(self,o=None):
#         self.store = {}
#         self._clear_cached()
#         if o is not None:
#             self.parse(o)
#
#     def _clear_cached(self):
#         self._inverse = None
#         self._udk = None
#         self._content = None
#         self._size = None
#
#     def inverse(self):
#         if self._inverse is None:
#             self._inverse = {v: k for k, v in six.iteritems(self.store)}
#         return self._inverse
#
#     def udk(self):
#         if self._udk is None:
#             self._build_content()
#         return self._udk
#
#     def content(self):
#         if self._content is None:
#             self._build_content()
#         return self._content
#
#     def size(self):
#         if self._size is None:
#             self._build_content()
#         return self._size
#
#     def _build_content(self):
#         self._content = str(self)
#         in_bytes = utils.ensure_bytes(self._content)
#         self._size = len(in_bytes)
#         self._udk = UDK.from_digest_and_inline_data(
#             quick_hash(in_bytes),in_bytes, bundle=True)
#
#     def parse(self, o):
#         self._clear_cached()
#         if isinstance(o, six.string_types):
#             names, udks = json.loads(o)
#         elif type(o) in [list, tuple] and len(o) == 2:
#             names, udks = o
#         else:
#             names, udks = json.load(o)
#         self.store.update(zip(names, map(UDK.ensure_it, udks)))
#         return self
#
#     def __iter__(self):
#         return iter(self.keys())
#
#     def __setitem__(self, k, v):
#         self._clear_cached()
#         self.store[k] = UDK.ensure_it(v)
#
#     def __delitem__(self, k):
#         self._clear_cached()
#         del self.store[k]
#
#     def __getitem__(self, k):
#         return self.store[k]
#
#     def __len__(self):
#         return len(self.store)
#
#     def get_name_by_udk(self, k):
#         return self.inverse()[UDK.ensure_it(k)]
#
#
#     def keys(self):
#         names = list(self.store.keys())
#         names.sort()
#         return names
#
#     def get_udks(self, names=None):
#         if names is None:
#             names = self.keys()
#         return [self.store[k] for k in names]
#
#     def to_json(self):
#         keys = self.keys()
#         return [keys, self.get_udks(keys)]
#
#     def udk_content(self):
#         content = str(self)
#         in_bytes = utils.ensure_bytes(content)
#         return UDK.from_digest_and_inline_data(quick_hash(in_bytes), in_bytes, bundle=True), len(in_bytes), content
#
#
# class UdkSet(utils.Jsonable):
#     def __init__(self,o=None):
#         self.store = []
#         if o is not None:
#             self.parse(o)
#
#     def parse(self, o):
#         if isinstance(o, six.string_types):
#             udks = json.loads(o)
#         elif hasattr(o, 'read'):
#             udks = json.load(o)
#         else:
#             udks = o
#         for k in udks:
#             self.add(k)
#         return self
#
#     def _index_of(self,k):
#         l = len(self.store)
#         if l == 0:
#             return -1
#         else:
#             lo = 0
#             hi = l - 1
#             while True:
#                 i = lo + int((hi-lo)/2)
#                 s = self.store[i].k
#                 if s == k.k:
#                     return i
#                 if s > k.k:
#                     if i == lo:
#                         i = -1-i
#                         break
#                     hi = max(lo, i-1)
#                 else:
#                     if i == hi:
#                         i = -1-(i+1)
#                         break
#                     lo = min(hi, i+1)
#             return i
#
#     def add(self,k):
#         k = UDK.ensure_it(k).strip_bundle()
#         i = self._index_of(k)
#         to_add = i < 0
#         if to_add:
#             at = -(i + 1)
#             self.store.insert(at, k)
#         return to_add
#
#     def __contains__(self, k):
#         k = UDK.ensure_it(k).strip_bundle()
#         return self._index_of(k) >= 0
#
#     def __iter__(self):
#         return iter(self.store)
#
#     def __delitem__(self, k):
#         del self.store[k]
#
#     def __getitem__(self, k):
#         return self.store[k]
#
#     def __len__(self):
#         return len(self.store)
#
#     def to_json(self):
#         return self.store
#
#
