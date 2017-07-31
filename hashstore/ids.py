import hashlib
import os

import six
import sys

import hashstore.base_x as bx
import hashstore.utils as utils
from hashstore.new_db import varchar_type

import json
import enum

import logging
log = logging.getLogger(__name__)

BASE_ENCODING = bx.base_x(62)

TINY_ALPHABET = bx.alphabets[36]
TINY_ENCODING = bx.BaseX(TINY_ALPHABET)


class KeyStructure(enum.IntEnum):
    INLINE = 0
    SHA256 = 1
    GUID256 = 2
    TINYNAME = 3


def cast_to_tiny_alphabet(text):
    '''
    >>> cast_to_tiny_alphabet('ABC-325')
    'abc325'
    >>> cast_to_tiny_alphabet('ABC-2+3/%5')
    'abc235'
    >>> cast_to_tiny_alphabet('abc325')
    'abc325'
    '''
    return ''.join(filter(lambda c: c in TINY_ALPHABET, text.lower()))


class DataType(enum.IntEnum):
    UNCATEGORIZED = 0
    BUNDLE = 1
    TXT_WITH_CAKEURLS = 2


inline_max_bytes=32


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
    >>> _header(KeyStructure.INLINE,DataType.UNCATEGORIZED)
    0
    >>> _header(KeyStructure.SHA256,DataType.TXT_WITH_CAKEURLS)
    33
    '''
    return (data_type.value << 4) | id_structure.value

def pack_in_bytes(id_structure, data_type, data_bytes):
    r'''
    >>> pack_in_bytes(KeyStructure.INLINE,DataType.UNCATEGORIZED, b'ABC')
    b'\x00ABC'
    >>> pack_in_bytes(KeyStructure.SHA256,DataType.TXT_WITH_CAKEURLS,b'XYZ')
    b'!XYZ'
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
        if length <= inline_max_bytes:
            inline_data += read_buffer
    fd.close()
    if length > inline_max_bytes:
        inline_data = None
    return digest.digest(), length, inline_data


class Cake(utils.Stringable, utils.EnsureIt):
    '''
    Stands for Content Address Key.

    Content addressing scheme using SHA256. For small
    content ( <=32 bytes) data is embeded  in key. Base62 encoding is
    used to store header byte followed by hash digest or inlined data.
    header byte split in two halves: `KeyStructure` and `DataType`

    We allow future extension and use different type of hash algos.
    Currently we have 4 `KeyStructure` defined, leaving 12 more for
    future extension.

    >>> list(KeyStructure) #doctest: +NORMALIZE_WHITESPACE
    [<KeyStructure.INLINE: 0>, <KeyStructure.SHA256: 1>,
    <KeyStructure.GUID256: 2>, <KeyStructure.TINYNAME: 3>]

    >>> short_content = b'The quick brown fox jumps over'
    >>> short_k = Cake.from_bytes(short_content)
    >>> short_k.key_structure
    <KeyStructure.INLINE: 0>
    >>> short_k.has_data()
    True
    >>> short_k.data() is not None
    True
    >>> short_k.data() == short_content
    True
    >>> str(short_k)
    '01aMUQDApalaaYbXFjBVMMvyCAMfSPcTojI0745igi'

    Longer content is hashed with SHA256:

    >>> longer_content = b'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    >>> longer_k = Cake.from_bytes(longer_content)
    >>> longer_k.key_structure
    <KeyStructure.SHA256: 1>
    >>> longer_k.has_data()
    False
    >>> longer_k.data() is None
    True
    >>> str(longer_k)
    '1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV'


    Global Unique ID can be generated, it is 32 byte
    random sequence packed in same way.

    >>> guid = Cake.new_guid()
    >>> guid.key_structure
    <KeyStructure.GUID256: 2>
    >>> len(str(guid))
    44

    Also you can generate tinyname. It is shorter key, that easier
    to remember. But key space is much smaller so you cannot  generate
    them independently but rather validate them against tinyname to
    full Cake mapping.

    Generate tinyname at random:

    >>> tiny = Cake.tiny()
    >>> tiny.key_structure
    <KeyStructure.TINYNAME: 3>
    >>> len(str(tiny))
    6

    Or seed it from Cake:

    >>> tiny = Cake.tiny(cake=longer_k)
    >>> tiny.key_structure
    <KeyStructure.TINYNAME: 3>
    >>> str(tiny)
    'gPF18s'
    >>> tiny != guid
    True

    Or generate it from text:

    >>> tiny = Cake.tiny(text='ABC')
    >>> tiny.key_structure
    <KeyStructure.TINYNAME: 3>
    >>> str(tiny)
    'SCI'

    '''
    def __init__(self, s, id_structure = None, data_type = None,
                 codec = BASE_ENCODING):
        if id_structure is not None:
            self._data = s
            self.key_structure = id_structure
            self.data_type = data_type
        else:
            decoded = codec.decode(utils.ensure_string(s))
            header = to_int(decoded[0])
            self._data = decoded[1:]
            self.key_structure = KeyStructure(header & 0x0F)
            self.data_type = DataType(header >> 4)
        if self.key_structure not in \
                (KeyStructure.INLINE, KeyStructure.TINYNAME):
            l = len(self._data)
            if l != 32:
                 raise AssertionError('invalid CAKey: %r ' % s)


    @staticmethod
    def from_digest_and_inline_data(digest, buffer,
                                    data_type = DataType.UNCATEGORIZED):
        if buffer is not None and len(buffer) <= inline_max_bytes:
            return Cake(buffer, id_structure=KeyStructure.INLINE,
                        data_type=data_type)
        else:
            return Cake(digest, id_structure=KeyStructure.SHA256,
                        data_type=data_type)

    @staticmethod
    def from_stream(fd, data_type=DataType.UNCATEGORIZED):
        digest, _, inline_data = process_stream(fd)
        return Cake.from_digest_and_inline_data(digest, inline_data,
                                                data_type=data_type)

    @staticmethod
    def from_bytes(s, data_type=DataType.UNCATEGORIZED):
        return Cake.from_stream(six.BytesIO(s),
                                data_type=data_type)
    @staticmethod
    def from_file(file, data_type=DataType.UNCATEGORIZED):
        return Cake.from_stream(open(file, 'rb'), data_type=data_type)

    @staticmethod
    def new_guid(data_type = DataType.UNCATEGORIZED):
        return Cake(os.urandom(32), id_structure=KeyStructure.GUID256,
                    data_type = data_type)

    def has_data(self):
        return self.key_structure == KeyStructure.INLINE

    def data(self):
        return self._data if self.has_data() else None

    def digest(self):
        if not(hasattr(self, '_digest')):
            if self.has_data():
                self._digest = quick_hash(self._data)
            else:
                self._digest = self._data
        return self._digest

    @staticmethod
    def tiny(text=None, cake=None, data_type=DataType.UNCATEGORIZED):
        if text is not None:
            t_bytes=TINY_ENCODING.decode(cast_to_tiny_alphabet(text))
        elif cake is not None:
            t_bytes=cake.digest()[:4]
        else:
            t_bytes=os.urandom(4)
        return Cake(t_bytes, id_structure=KeyStructure.TINYNAME,
                    data_type = data_type)

    def hash_bytes(self):
        '''
        :raise AssertionError when Cake is not hash based
        :return: hash in bytes
        '''
        if self.key_structure != KeyStructure.SHA256:
            raise AssertionError("Not-hash %r %r" %
                                 (self.key_structure, self))

        return self._data


    def __str__(self):
        in_bytes = pack_in_bytes(self.key_structure, self.data_type,
                                 self._data)
        return BASE_ENCODING.encode(in_bytes)

    def __repr__(self):
        return "Cake(%r)" % self.__str__()

    def __hash__(self):
        if not(hasattr(self, '_hash')):
            self._hash = hash(self.digest())
        return self._hash

    def __eq__(self, other):
        if not isinstance(other, Cake):
            return False
        return self._data == other._data and \
               self.key_structure == other.key_structure and \
               self.data_type == other.data_type

    def __ne__(self, other):
        return not self.__eq__(other)


class NamedCAKes(utils.Jsonable):
    '''
    sorted dictionary of names and corresponding UDKs

    >>> short_k = Cake.from_bytes(b'The quick brown fox jumps over')
    >>> longer_k = Cake.from_bytes(b'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')

    >>> udks = NamedCAKes()
    >>> udks['short'] = short_k
    >>> udks['longer'] = longer_k
    >>> len(udks)
    2

    >>> udks.keys()
    ['longer', 'short']
    >>> str(udks.cake())
    'gSKHC1OkVsHmrx1APDA4sq3iAwqg6wIXHVDqM3pPtwXR'
    >>> udks.size()
    117
    >>> udks.content()
    '[["longer", "short"], ["1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV", "01aMUQDApalaaYbXFjBVMMvyCAMfSPcTojI0745igi"]]'
    >>> udks.get_name_by_udk("1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV")
    'longer'
    '''
    def __init__(self,o=None):
        self.store = {}
        self._clear_cached()
        if o is not None:
            self.parse(o)

    def _clear_cached(self):
        self._inverse = None
        self._udk = None
        self._content = None
        self._size = None

    def inverse(self):
        if self._inverse is None:
            self._inverse = {v: k for k, v in six.iteritems(self.store)}
        return self._inverse

    def cake(self):
        if self._udk is None:
            self._build_content()
        return self._udk

    def content(self):
        if self._content is None:
            self._build_content()
        return self._content

    def size(self):
        if self._size is None:
            self._build_content()
        return self._size

    def _build_content(self):
        self._content = str(self)
        in_bytes = utils.ensure_bytes(self._content)
        self._size = len(in_bytes)
        self._udk = Cake.from_digest_and_inline_data(
            quick_hash(in_bytes),in_bytes,
            data_type=DataType.BUNDLE)

    def parse(self, o):
        self._clear_cached()
        if isinstance(o, six.string_types):
            names, udks = json.loads(o)
        elif type(o) in [list, tuple] and len(o) == 2:
            names, udks = o
        else:
            names, udks = json.load(o)
        self.store.update(zip(names, map(Cake.ensure_it, udks)))
        return self

    def __iter__(self):
        return iter(self.keys())

    def __setitem__(self, k, v):
        self._clear_cached()
        self.store[k] = Cake.ensure_it(v)

    def __delitem__(self, k):
        self._clear_cached()
        del self.store[k]

    def __getitem__(self, k):
        return self.store[k]

    def __len__(self):
        return len(self.store)

    def get_name_by_udk(self, k):
        return self.inverse()[Cake.ensure_it(k)]

    def keys(self):
        names = list(self.store.keys())
        names.sort()
        return names

    def get_udks(self, names=None):
        if names is None:
            names = self.keys()
        return [self.store[k] for k in names]

    def to_json(self):
        keys = self.keys()
        return [keys, self.get_udks(keys)]


Cake_TYPE = varchar_type(Cake)
