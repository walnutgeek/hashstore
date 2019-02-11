import timeit
from os import urandom
from hashstore.kernel.base_x import base_x
B62 = base_x(62)
encode_samples = [urandom(64) for i in range(100)]
decode_samples = [B62.encode(s) for s in encode_samples]


def encode():
    for sample in encode_samples:
        B62.encode(sample)


def decode():
    for sample in decode_samples:
        B62.decode(sample)


def do_timing(fn):
    print( fn )
    print( timeit.repeat(fn+"()", "from __main__ import "+fn,
                         number=100))


if __name__ == '__main__':
    do_timing('encode')
    do_timing('decode')
