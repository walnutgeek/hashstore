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
    pass

def quick_hash(v):
    h = hashlib.sha256()
    h.update( utils.ensure_bytes(v) )
    return h.hexdigest()


def process_stream(fd, process_buffer=NOP_process_buffer):
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
    if length >= inline_max :
        inline_data = None
    return (digest, length, inline_data )


def calc_UDK_and_length_from_stream(fd, respect_inline_max=True,
                                    process_buffer=NOP_process_buffer):
    digest, length, inline_data = process_stream(fd, process_buffer)
    return UDK_from_digest_and_inline_data(digest, inline_data, respect_inline_max),length


def UDK_from_digest_and_inline_data(digest, buffer, respect_inline_max):
    if respect_inline_max and buffer is not None and len(buffer) < inline_max:
        return UDK('M' + utils.ensure_string(base64.b64encode(buffer)))
    else:
        return UDK(digest.hexdigest())


class UDK(utils.Stringable):
    def __init__(self, k):
        self.named_udk_bundle = False
        if k[:1] == 'X':
            self.named_udk_bundle = True
            k = k[1:]
        l = len(k)
        self.k = k
        if l == 64 :
            self.digest = k
        elif l > 64 or k[0] != 'M':
            raise ValueError('invalid udk: %r ' % k)

    @staticmethod
    def from_stream(fd, respect_inline_max=True):
        return calc_UDK_and_length_from_stream(fd, respect_inline_max)[0]

    @staticmethod
    def from_string(s, respect_inline_max=True):
        return UDK.from_stream(six.BytesIO(utils.ensure_bytes(s)), respect_inline_max)

    @staticmethod
    def from_file(file, respect_inline_max=True):
        return UDK.from_stream(open(file, 'rb'), respect_inline_max)

    def set_bundle(self):
        self.named_udk_bundle = True
        return self

    def strip_bundle(self):
        return UDK(self.k) if self.named_udk_bundle else self

    def __str__(self):
        return 'X'+self.k if self.named_udk_bundle else self.k

    def __hash__(self):
        if not(hasattr(self, '_hash')):
            self._hash = hash(self.hexdigest())
        return self._hash

    def has_data(self):
        return self.k[0] == 'M'

    def data(self):
        return base64.b64decode(self.k[1:])

    def hexdigest(self):
        try:
            return self.digest
        except:
            sha256,_,_ = process_stream(six.BytesIO(utils.ensure_bytes(self.data())))
            self.digest = sha256.hexdigest()
        return self.digest

    def __eq__(self, other):
            if not isinstance(other, UDK):
                return False
            return self.hexdigest() == other.hexdigest()


class NamedUDKs(utils.Jsonable):
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
        k, size = calc_UDK_and_length_from_stream(six.BytesIO(utils.ensure_bytes(content)))
        return k.set_bundle(), size, content


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
        return  self._index_of(k) >= 0

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


