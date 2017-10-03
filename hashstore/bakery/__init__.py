from hashstore.utils import Stringable, EnsureIt, Jsonable
from six import BytesIO, string_types, iteritems, binary_type
import hashlib
import os
import sys
import hashstore.utils as utils
import base64
from hashstore.utils.base_x import base_x,iseq
import json
import enum

import logging
from hashstore.utils import path_split_all

log = logging.getLogger(__name__)

if bytes == str:  # python2
    to_byte = chr
    to_int = ord
else:  # python3
    to_byte = lambda code: bytes([code])
    to_int = lambda b : b

B62 = base_x(62)
B36 = base_x(36)

TINY_ALPHABET = B36.alphabet

MAX_NUM_OF_SHARDS = 8192


def is_it_shard(shard_name):
    '''
    Test if directory name can represent shard

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
            shard_num = B36.decode_int(shard_name.lower())
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
            self._id = B36.encode(self.hash_bytes)
        elif isinstance(hash_or_cake_or_str, Cake):
            self.hash_bytes = hash_or_cake_or_str.hash_bytes()
            self._id = B36.encode(self.hash_bytes)
        else:
            self._id = hash_or_cake_or_str.lower()
            self.hash_bytes = B36.decode(self._id)
        b1, b2 = iseq(self.hash_bytes[:2])
        self.modulus = (b1*256+b2) % MAX_NUM_OF_SHARDS
        self.shard_name = B36._encode_int(self.modulus)

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


class Content(Jsonable):
    JSONABLE_FIELDS='size created_dt mime'.split()

    def __init__(self, data=None, file=None, stream_fn=None,
                 mime='application/octet-stream', created_dt=None,
                 size=None, data_type=None, lookup=None):
        self.mime = mime
        if data is None and file is None and stream_fn is None:
            raise AssertionError('define data or file or stream_fn')
        self.data = data
        self.file = file
        self.stream_fn = stream_fn
        self.data_type = data_type
        if lookup is None:
            self.size = size
            self.created_dt = created_dt
        else:
            self.size = lookup.size
            self.created_dt = lookup.created_dt

    def set_data_type(self, copy_from):
        if hasattr(copy_from, 'data_type'):
            self.data_type = copy_from.data_type
        return self

    def has_data(self):
        return self.data is not None

    def get_data(self):
        return self.data if self.has_data() else self.stream().read()

    def stream(self):
        if self.has_data():
            return BytesIO(self.data)
        elif self.file is not None:
            return open(self.file, 'rb')
        else:
            return self.stream_fn()

    def has_file(self):
        return self.file is not None

    def open_fd(self):
        return os.open(self.file,os.O_RDONLY)

    def to_json(self):
        return { k:getattr(self,'k') for k in self.JSONABLE_FIELDS}


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


inline_max_bytes=32


def NOP_process_buffer(read_buffer):
    '''
    Does noting

    >>> NOP_process_buffer(b'')

    :param read_buffer: take bytes
    :return: nothing
    '''
    pass



def _header(id_structure,data_type):
    '''
    >>> _header(KeyStructure.INLINE,DataType.UNCATEGORIZED)
    0
    >>> _header(KeyStructure.SHA256,DataType.BUNDLE)
    17
    '''
    return (data_type.value << 4) | id_structure.value

def pack_in_bytes(id_structure, data_type, data_bytes):
    r'''
    >>> pack_in_bytes(KeyStructure.INLINE,DataType.UNCATEGORIZED, b'ABC')
    b'\x00ABC'
    >>> pack_in_bytes(KeyStructure.SHA256,DataType.BUNDLE, b'XYZ')
    b'\x11XYZ'
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
    inline_data = binary_type()
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
    content ( <=32 bytes) data is embeded  in key.  Header byte is
    followed by hash digest or inlined data. header byte split in two
    halves: `KeyStructure` and `DataType`. Base62 encoding is
    used to encode bytes.

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
    >>> len(longer_k.hash_bytes())
    32
    >>> len(longer_k.digest())
    32
    >>> len(set([hash(longer_k) , hash(longer_k)]))
    1

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
                 codec = B62):
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
            if len(self._data) != 32:
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
        return Cake.from_stream(BytesIO(s),
                                data_type=data_type)
    @staticmethod
    def from_file(file, data_type=DataType.UNCATEGORIZED):
        return Cake.from_stream(open(file, 'rb'), data_type=data_type)

    @staticmethod
    def new_guid(data_type=DataType.UNCATEGORIZED):
        return Cake(os.urandom(32), id_structure=KeyStructure.GUID256,
                    data_type=data_type)

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
            t_bytes=B36.decode(cast_to_tiny_alphabet(text))
        elif cake is not None:
            t_bytes=cake.digest()[:4]
        else:
            t_bytes=os.urandom(4)
        return Cake(t_bytes, id_structure=KeyStructure.TINYNAME,
                    data_type = data_type)

    def is_resolved(self):
        return self.key_structure == KeyStructure.SHA256

    def is_portal(self):
        return self.key_structure in (KeyStructure.TINYNAME,
                                      KeyStructure.GUID256)

    def hash_bytes(self):
        '''
        :raise AssertionError when Cake is not hash based
        :return: hash in bytes
        '''
        if not self.is_resolved():
            raise AssertionError("Not-hash %r %r" %
                                 (self.key_structure, self))

        return self._data

    def __str__(self):
        in_bytes = pack_in_bytes(self.key_structure, self.data_type,
                                 self._data)
        return B62.encode(in_bytes)

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
    >>> udks.get_name_by_cake("1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV")
    'longer'
    '''
    def __init__(self,o=None):
        self.store = {}
        self._clear_cached()
        if o is not None:
            self.parse(o)

    def _clear_cached(self):
        self._inverse = None
        self._cake = None
        self._content = None
        self._size = None
        self._in_bytes = None

    def inverse(self):
        if self._inverse is None:
            self._inverse = {v: k for k, v in iteritems(self.store)}
        return self._inverse

    def cake(self):
        if self._cake is None:
            self._build_content()
        return self._cake

    def content(self):
        if self._content is None:
            self._build_content()
        return self._content

    def in_bytes(self):
        if self._content is None:
            self._build_content()
        return self._in_bytes

    def size(self):
        if self._size is None:
            self._build_content()
        return self._size

    def _build_content(self):
        self._content = str(self)
        self._in_bytes = utils.ensure_bytes(self._content)
        self._size = len(self._in_bytes)
        self._cake = Cake.from_digest_and_inline_data(
            quick_hash(self._in_bytes),self._in_bytes,
            data_type=DataType.BUNDLE)

    def parse(self, o):
        self._clear_cached()
        if isinstance(o, string_types):
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

    def get_name_by_cake(self, k):
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


class CakePath(utils.Stringable, utils.EnsureIt):
    '''
    >>> root = CakePath('/SCI')
    >>> root
    CakePath('/SCI/')
    >>> absolute = CakePath('/SCI/x/y')
    >>> absolute
    CakePath('/SCI/x/y')
    >>> relative = CakePath('y/z')
    >>> relative
    CakePath('y/z')
    >>> relative.make_absolute(absolute)
    CakePath('/SCI/x/y/y/z')
    >>> CakePath('/10Bd/r/f').make_absolute(absolute)
    CakePath('/10Bd/r/f')

    '''
    def __init__(self, s, _root = None, _path = []):
        if s is  None:
            self.root = _root
            self.path = _path
        else:
            split = path_split_all(s, ensure_trailing_slash=False)
            if split[0] == '/' :
                self.root = Cake(split[1])
                self.path = split[2:]
            else:
                self.root = None
                self.path = split

    def child(self, name):
        path = list(self.path)
        path.append(name)
        return CakePath(None, _path=path, _root=self.root)

    def relative(self):
        return self.root is None

    def make_absolute(self, current_cake_path):
        if self.relative():
            path = list(current_cake_path.path)
            path.extend(self.path)
            return CakePath( None ,
                             _root=current_cake_path.root,
                             _path=path)
        else:
            return self

    def __str__(self):
        if self.relative():
            return self.path_join()
        else:
            return '/%s/%s' % (self.root, self.path_join())

    def path_join(self):
        return '/'.join(self.path)


def cake_or_path(s, relative_to_root=False):
    if isinstance(s, Cake) or isinstance(s, CakePath):
        return s
    elif s[:1] == '/':
        return CakePath(s)
    elif relative_to_root and '/' in s:
        return CakePath('/'+s)
    else:
        return Cake(s)

SSHA_MARK='{SSHA}'


class SaltedSha(utils.Stringable, utils.EnsureIt):
    '''
    >>> ssha = SaltedSha.from_secret('abc')
    >>> ssha.check_secret('abc')
    True
    >>> ssha.check_secret('zyx')
    False
    >>> ssha = SaltedSha('{SSHA}5wRHUQxypw7C4AVd4yZRW/8pXy2Gwvh/')
    >>> ssha.check_secret('abc')
    True
    >>> ssha.check_secret('Abc')
    False
    >>> ssha.check_secret('zyx')
    False
    >>> str(ssha)
    '{SSHA}5wRHUQxypw7C4AVd4yZRW/8pXy2Gwvh/'
    >>> ssha
    SaltedSha('{SSHA}5wRHUQxypw7C4AVd4yZRW/8pXy2Gwvh/')

    '''
    def __init__(self, s, _digest=None, _salt=None):
        if s is None:
            self.digest = _digest
            self.salt = _salt
        else:
            len_of_mark = len(SSHA_MARK)
            if SSHA_MARK == s[:len_of_mark]:
                challenge_bytes = base64.b64decode(s[len_of_mark:])
                self.digest = challenge_bytes[:20]
                self.salt = challenge_bytes[20:]
            else:
                raise AssertionError('cannot init: %r' % s)

    @staticmethod
    def from_secret(secret):
        secret = utils.ensure_bytes(secret)
        h=hashlib.sha1(secret)
        salt = os.urandom(4)
        h.update(salt)
        return SaltedSha(None, _digest=h.digest(), _salt=salt)

    def check_secret(self, secret):
        secret = utils.ensure_bytes(secret)
        h=hashlib.sha1(secret)
        h.update(self.salt)
        return self.digest == h.digest()

    def __str__(self):
        encode = base64.b64encode(self.digest + self.salt)
        return SSHA_MARK + utils.ensure_string(encode)


class InetAddress(utils.Stringable, utils.EnsureIt):

    def __init__(self, k):
        self.k = k

    def __str__(self):
        return self.k


class RemoteError(ValueError): pass

class CredentialsError(ValueError): pass

class NotAuthorizedError(ValueError): pass

class NotFoundError(ValueError): pass
