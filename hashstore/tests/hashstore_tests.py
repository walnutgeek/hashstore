import sys
import logging
import os
import shutil

import hashstore.localstore as localstore
import hashstore.udk as udk
import datetime
from nose.tools import eq_,ok_,with_setup
import six


# to test if sniffer is not hanging uncomment next line & save
# raise Exception()

test_dir = os.path.join(os.path.abspath("test-out"),__name__)
if os.path.isdir(test_dir):
    shutil.rmtree(test_dir)
os.makedirs(test_dir)

log = logging.getLogger(__name__)

import random
random_bytes = lambda l: six.binary_type().join(
    six.int2byte(random.randint(0, 255)) for _ in range(l))

inline_udk = 'M2MJrQoJnyE16leiBSMGeQOj7z+ZPuuaveBlvnOn3et1CzowDuGbTqw=='
db_udk = '61a9a406b2e5790c6e80f5a33d6c773c456b8923deef63ace57192ab71e6cb98'
file_udk = 'f05c654b8b74611f575658ec4e9d26147b6395113be29d33f207f572a5057ea1'


def test_HashStore():
    hs = localstore.HashStore(os.path.join(test_dir,'test_HashStore'),True)
    not_existent = six.binary_type('afebac2a37799077d70427c6a28ed1d99754363e1f5dd0a2b28b962d8ae15263')

    def store():
        random.seed(0)
        s = random_bytes(40)
        eq_(len(s), 40)
        w0 = hs.writer()
        r0 = w0.write(s, done=True)
        eq_(inline_udk, str(r0))
        digest,_,_ = udk.process_stream(six.BytesIO(s))
        r0a = udk.UDK(digest.hexdigest())
        eq_(r0, r0a)
        eq_(False, r0 == 0 )
        eq_(False, r0a == 0 )
        eq_(False, str(r0) == str(r0a))
        eq_(hash(r0), hash(r0a))
        try:
            udk.UDK('Xabc')
            ok_(False)
        except ValueError:
            pass
        w1 = hs.writer()
        for _ in range(3):
            w1.write(random_bytes(100))
        r1 = w1.done()
        s1 = str(r1)
        eq_(db_udk, s1)
        w2 = hs.writer()
        for _ in range(100): # 100Mb
            w2.write(random_bytes(1000))
        w2.done()
        r2 = w2.done() # call done twice
        eq_(file_udk, str(r2))
        return r0, r1, r2
    r0, r1, r2 = store()
    #test recall
    random.seed(0)
    o0 = hs.get_content(r0)
    eq_(o0.read(40), random_bytes(40))
    eq_(0, len(o0.read()))
    o1=hs.get_content(r1)
    for _ in range(3):
        eq_(o1.read(100), random_bytes(100))
    eq_(0, len(o1.read()))
    o2 = hs.get_content(r2)
    for _ in range(100):
        eq_(o2.read(1000), random_bytes(1000))
    eq_(0, len(o2.read()))
    #store again
    store()
    #retrieve non existent
    eq_(None, hs.get_content(not_existent))
    udks = list(hs.iterate_udks())
    eq_(2,len(udks))
    random.seed(0)
    eq_(str(udk.UDK_from_string(random_bytes(40))), inline_udk)
    eq_(str(udk.UDK_from_file(os.path.join(hs.root, file_udk[0:3], file_udk[3:]))), file_udk)
    for u in udks:
        hs.delete(u)
    eq_(hs.delete(not_existent),False)
    eq_(hs.delete(inline_udk),False)
    udks = list(hs.iterate_udks())
    eq_(0,len(udks))
    # ok_(False)


