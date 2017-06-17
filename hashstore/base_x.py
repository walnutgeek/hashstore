'''
Base_X encoding is just like base58, but allow to use flexible alphabet.

https://en.wikipedia.org/wiki/Base58

Quite clever algorithm is taken literaly from python base58 project
https://github.com/keis/base58 (MIT license)

and list of alphabets is taken from
https://github.com/cryptocoinjs/base-x (MIT license)

I believe MIT license is compatible with Apache (if I am wrong,
file bug, don't sue me), so consider this file dual licensed
under Apache and MIT.
'''

# --- original comments form base58
# Implementations of Base58 and Base58Check endcodings that are compatible
# with the bitcoin network.

# This module is based upon base58 snippets found scattered over many bitcoin
# tools written in python. From what I gather the original source is from a
# forum post by Gavin Andresen, so direct your praise to him.
# This module adds shiny packaging and support for python3.
# ---


from hashlib import sha256

alphabets = {
2:	'01' ,
8:	'01234567',
11:	'0123456789a',
16:	'0123456789abcdef',
32:	'0123456789ABCDEFGHJKMNPQRSTVWXYZ',
36:	'0123456789abcdefghijklmnopqrstuvwxyz',
58:	'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz',
62:	'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
64:	'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
66:	'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~',
}


if bytes == str:  # python2
    iseq = lambda s: map(ord, s)
    bseq = lambda s: ''.join(map(chr, s))
else:  # python3
    iseq = lambda s: s
    bseq = bytes

cached_instances = {}

def base_x(alphabet_id):
    '''
    lazy initialization for BaseX instance

    >>> base_x(58).encode(b'the quick brown fox jumps over the lazy dog')
    '9aMVMYHHtr2a2wF61xEqKskeCwxniaf4m7FeCivEGBzLhSEwB6NEdfeySxW'
    >>> base_x(58).decode('9aMVMYHHtr2a2wF61xEqKskeCwxniaf4m7FeCivEGBzLhSEwB6NEdfeySxW')
    b'the quick brown fox jumps over the lazy dog'

    >>> base_x(58).encode_check(b'the quick brown fox jumps over the lazy dog')
    'y7WFhoXCMz3M46XhLVWLAfYXde92zQ8FTnKRxzWNmBYTDa67791CqkFDJgmtRff3'
    >>> base_x(58).decode_check('y7WFhoXCMz3M46XhLVWLAfYXde92zQ8FTnKRxzWNmBYTDa67791CqkFDJgmtRff3')
    b'the quick brown fox jumps over the lazy dog'
    >>> base_x(58).decode_check('9aMVMYHHtr2a2wF61xEqKskeCwxniaf4m7FeCivEGBzLhSEwB6NEdfeySxW')
    Traceback (most recent call last):
    ...
    ValueError: Invalid checksum


    :param alphabet_id: reference to predefined alphabet from
                        `alphabets` dictionary
    :return: BaseX
    '''
    if alphabet_id not in cached_instances:
        cached_instances[alphabet_id] = BaseX(alphabets[alphabet_id])
    return cached_instances[alphabet_id]

class BaseX:
    def __init__(self, alphabet):
        self.alphabet = alphabet
        self.size = len(alphabet)

    def encode_int(self, i):
        '''Encode an integer'''
        string = ""
        while i:
            i, idx = divmod(i, self.size)
            string = self.alphabet[idx] + string
        return string

    def encode(self, v):
        '''Encode a string'''
        if not isinstance(v, bytes):
            raise TypeError("a bytes-like object is required, not '%s'" %
                            type(v).__name__)

        origlen = len(v)
        v = v.lstrip(b'\0')
        count_of_nulls = origlen - len(v)

        p, acc = 1, 0
        for c in iseq(reversed(v)):
            acc += p * c
            p <<= 8

        result = self.encode_int(acc)

        return (self.alphabet[0] * count_of_nulls + result)

    def decode_int(self, v):
        '''Decode a string into integer'''

        decimal = 0
        for char in v:
            decimal = decimal * self.size + self.alphabet.index(char)
        return decimal

    def decode(self, v):
        '''Decode string'''

        if not isinstance(v, str):
            v = v.decode('ascii')

        #strip null bytes
        origlen = len(v)
        v = v.lstrip(self.alphabet[0])
        count_of_nulls = origlen - len(v)

        acc = self.decode_int(v)

        result = []
        while acc > 0:
            acc, mod = divmod(acc, 256)
            result.append(mod)

        return (b'\0' * count_of_nulls + bseq(reversed(result)))

    def encode_check(self, v):
        '''Encode a string with a 4 character checksum'''

        digest = sha256(sha256(v).digest()).digest()
        return self.encode(v + digest[:4])

    def decode_check(self, v):
        '''Decode and verify the checksum '''

        result = self.decode(v)
        result, check = result[:-4], result[-4:]
        digest = sha256(sha256(result).digest()).digest()

        if check != digest[:4]:
            raise ValueError("Invalid checksum")

        return result
