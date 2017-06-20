import hashlib
import six
import base64
import hashstore.utils as utils
import json

inline_max=46

db_max=65535

EMPTY_HASH = hashlib.sha256().hexdigest()

def mime64_size(sz):
    code_size = int((sz * 4) / 3)
    mod = sz % 3
    padding_size = 4 - mod if mod > 0 else 0
    return code_size + padding_size

import logging
log = logging.getLogger(__name__)


def NOP_process_buffer(read_buffer):
    '''
    Does noting

    >>> NOP_process_buffer(b'')

    :param read_buffer: take bytes
    :return: nothing
    '''
    pass


def quick_hash(data):
    '''
    Calculate hash on data buffer passed

    >>> quick_hash(b'abc')
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    >>> quick_hash(u'abc')
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    >>> quick_hash(5.7656)
    '8e1910dd62c329847e693ebe4c8a089696a57352308c7fd7ec0f6112fb41b9a3'
    >>> quick_hash('5.7656')
    '8e1910dd62c329847e693ebe4c8a089696a57352308c7fd7ec0f6112fb41b9a3'

    :param data: in bytes, or if not it will be converted to string first
                 and then to byte
    :return: hexdigest
    '''
    h = hashlib.sha256()
    h.update(utils.ensure_bytes(data))
    return h.hexdigest()


def process_stream(fd, process_buffer=NOP_process_buffer):
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
        read_buffer = fd.read(db_max)
        if len(read_buffer) <= 0:
            break
        length += len(read_buffer)
        digest.update(read_buffer)
        process_buffer(read_buffer)
        if length < inline_max:
            inline_data += read_buffer
    fd.close()
    if length >= inline_max:
        inline_data = None
    return digest.hexdigest(),length,inline_data


class UDK(utils.Stringable,utils.EnsureIt):
    '''
    Stands for Unique Data Key.

    It is content adressing scheme useing SHA256. For small
    content data is embeded in UDK using base64 encoding.

    >>> short_content = 'The quick brown fox jumps over the lazy dog'
    >>> short_udk = UDK.from_string(short_content)
    >>> short_udk.has_data()
    True
    >>> short_udk.data() is not None
    True

    In string representation there is 'M' in the beginging. It is used
    to mark that data packed inside of UDK.

    >>> str(short_udk)
    'MVGhlIHF1aWNrIGJyb3duIGZveCBqdW1wcyBvdmVyIHRoZSBsYXp5IGRvZw=='

    For longer content SHA256 hexdigest is used:

    >>> longer_content = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    >>> longer_udk = UDK.from_string(longer_content)
    >>> longer_udk.has_data()
    False
    >>> longer_udk.data() is None
    True
    >>> str(longer_udk)
    '973153f86ec2da1748e63f0cf85b89835b42f8ee8018c549868a1308a19f6ca3'

    '''
    def __init__(self, k , bundle = False):
        k = utils.ensure_string(k)
        self.named_udk_bundle = False
        if k[:1] == 'X':
            self.named_udk_bundle = True
            k = k[1:]
        elif bundle:
            self.named_udk_bundle = True
        l = len(k)
        self.k = k
        if l == 64:
            self.digest = k
        elif l > 64 or k[0] != 'M':
            raise ValueError('invalid udk: %r ' % k)

    @staticmethod
    def from_digest_and_inline_data(hexdigest, buffer, bundle = False):
        if buffer is not None and len(buffer) < inline_max:
            return UDK('M' + utils.ensure_string(base64.b64encode(buffer)), bundle=bundle)
        else:
            return UDK(hexdigest, bundle=bundle)

    @staticmethod
    def from_stream(fd, bundle=False):
        digest, _, inline_data = process_stream(fd)
        return UDK.from_digest_and_inline_data(digest, inline_data, bundle=bundle)

    @staticmethod
    def from_string(s, bundle=False):
        return UDK.from_stream(six.BytesIO(utils.ensure_bytes(s)), bundle=bundle)

    @staticmethod
    def from_file(file, bundle=False):
        return UDK.from_stream(open(file, 'rb'), bundle=bundle)

    def strip_bundle(self):
        return UDK(self.k) if self.named_udk_bundle else self

    def ensure_bundle(self):
        return self if self.named_udk_bundle else UDK(self.k, True)

    @staticmethod
    def nomalize(k):
        return UDK.ensure_it(k).strip_bundle()

    def __str__(self):
        return 'X'+self.k if self.named_udk_bundle else self.k

    def __hash__(self):
        if not(hasattr(self, '_hash')):
            self._hash = hash(self.hexdigest())
        return self._hash

    def has_data(self):
        return self.k[0] == 'M'

    def data(self):
        return base64.b64decode(self.k[1:]) if self.has_data() else None

    def hexdigest(self):
        try:
            return self.digest
        except:
            self.digest = quick_hash(self.data())
        return self.digest

    def __eq__(self, other):
            if not isinstance(other, UDK):
                return False
            return self.hexdigest() == other.hexdigest()

    def __ne__(self, other):
        return not self.__eq__(other)


class UDKBundle(utils.Jsonable):
    '''
    sorted dictionary of names and corresponding UDKs

    >>> short_udk = UDK.from_string('The quick brown fox jumps over the lazy dog')
    >>> longer_udk = UDK.from_string('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')

    >>> udks = UDKBundle()
    >>> udks['short'] = short_udk
    >>> udks['longer'] = longer_udk
    >>> len(udks)
    2

    >>> udks.keys()
    ['longer', 'short']
    >>> udks_udk, size, content = udks.udk_content()
    >>> str(udks_udk)
    'X4453e495c259e32294f47a8592b5c187901c9ea13bdcc517e0994aa6f556986d'
    >>> content
    '[["longer", "short"], ["973153f86ec2da1748e63f0cf85b89835b42f8ee8018c549868a1308a19f6ca3", "MVGhlIHF1aWNrIGJyb3duIGZveCBqdW1wcyBvdmVyIHRoZSBsYXp5IGRvZw=="]]'
    >>> no_bundle_marker = udks_udk.strip_bundle()
    >>> str(no_bundle_marker)
    '4453e495c259e32294f47a8592b5c187901c9ea13bdcc517e0994aa6f556986d'
    >>> udks_udk == no_bundle_marker
    True
    >>> str(no_bundle_marker.ensure_bundle())
    'X4453e495c259e32294f47a8592b5c187901c9ea13bdcc517e0994aa6f556986d'

    '''
    def __init__(self,o=None):
        self.store = {}
        self.inverse = None
        if o is not None:
            self.parse(o)

    def parse(self, o):
        self.inverse = None
        if isinstance(o, six.string_types):
            names, udks = json.loads(o)
        elif type(o) in [list, tuple] and len(o) == 2:
            names, udks = o
        else:
            names, udks = json.load(o)
        self.store.update(zip(names, map(UDK.ensure_it, udks)))
        return self

    def __iter__(self):
        return iter(self.keys())

    def __setitem__(self, k, v):
        self.inverse = None
        self.store[k] = UDK.ensure_it(v)

    def __delitem__(self, k):
        self.inverse = None
        del self.store[k]

    def __getitem__(self, k):
        return self.store[k]

    def __len__(self):
        return len(self.store)

    def get_name_by_udk(self, k):
        if self.inverse is None:
            self.inverse = { v : k for k,v in six.iteritems(self.store)}
        return self.inverse[UDK.ensure_it(k)]

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

    def udk_content(self):
        content = str(self)
        in_bytes = utils.ensure_bytes(content)
        return UDK.from_digest_and_inline_data(quick_hash(in_bytes), in_bytes, bundle=True), len(in_bytes), content


class UdkSet(utils.Jsonable):
    def __init__(self,o=None):
        self.store = []
        if o is not None:
            self.parse(o)

    def parse(self, o):
        if isinstance(o, six.string_types):
            udks = json.loads(o)
        elif hasattr(o, 'read'):
            udks = json.load(o)
        else:
            udks = o
        for k in udks:
            self.add(k)
        return self

    def _index_of(self,k):
        l = len(self.store)
        if l == 0:
            return -1
        else:
            lo = 0
            hi = l - 1
            while True:
                i = lo + int((hi-lo)/2)
                s = self.store[i].k
                if s == k.k:
                    return i
                if s > k.k:
                    if i == lo:
                        i = -1-i
                        break
                    hi = max(lo, i-1)
                else:
                    if i == hi:
                        i = -1-(i+1)
                        break
                    lo = min(hi, i+1)
            return i

    def add(self,k):
        k = UDK.ensure_it(k).strip_bundle()
        i = self._index_of(k)
        to_add = i < 0
        if to_add:
            at = -(i + 1)
            self.store.insert(at, k)
        return to_add

    def __contains__(self, k):
        k = UDK.ensure_it(k).strip_bundle()
        return self._index_of(k) >= 0

    def __iter__(self):
        return iter(self.store)

    def __delitem__(self, k):
        del self.store[k]

    def __getitem__(self, k):
        return self.store[k]

    def __len__(self):
        return len(self.store)

    def to_json(self):
        return self.store


