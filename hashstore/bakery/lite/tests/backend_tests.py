import os

from hashstore.bakery import NotFoundError
from hashstore.tests import TestSetup, seed, random_bytes
from ..node.blobs import BlobStore
from ..node import ContentAddress
from hashstore.bakery import Cake
from nose.tools import eq_,ok_,with_setup


# to test if sniffer is not hanging uncomment next line & save
# raise Exception()

test = TestSetup(__name__,ensure_empty=True)
log = test.log



inline_udk = 'nxtb5v6xupoxyvbds63goir59wlo9vfa8vk4xgas1a6g4f9bn'
db_udk = '3no3jb46qaff0a0pwg24lu0y8eq5ldmdich3su14mkcr76m8wo'
file_udk = '19gglgmrd4vuiagsr2duw9mz6tbdcku5xcawo6bg24k2wuenkl'

def test_LiteBackend():
    hs = BlobStore(os.path.join(test.dir, 'test_HashStore'))
    not_existent = '4no3jb46qaff0a0pwg24lu0y8eq5ldmdich3su14mkcr76m8wr'

    def store():
        seed(0)
        s = random_bytes(40)
        eq_(len(s), 40)
        w0 = hs.writer()
        r0 = w0.write(s, done=True)
        eq_(inline_udk, str(r0))
        r0a = ContentAddress(Cake.from_bytes(s))
        eq_(r0, r0a)
        eq_(False, r0 == 0 )
        eq_(False, r0a == 0 )
        eq_(hash(r0), hash(r0a))
        ok_(hs.lookup(Cake.from_bytes(s)).found())
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
    seed(0)
    o0 = hs.get_content(r0).stream()
    eq_(o0.read(40), random_bytes(40))
    eq_(0, len(o0.read()))
    o1=hs.get_content(r1).stream()
    for _ in range(3):
        eq_(o1.read(100), random_bytes(100))
    eq_(0, len(o1.read()))
    o2 = hs.get_content(r2).stream()
    for _ in range(100):
        eq_(o2.read(1000), random_bytes(1000))
    eq_(0, len(o2.read()))
    #store again
    store()

    #retrieve non existent
    try:
        hs.get_content(not_existent)
        ok_(False)
    except NotFoundError:
        pass
    all = list(hs)
    eq_(3,len(all))





