import sys
import uuid
import logging
import os
import shutil
from hashstore.tests import TestSetup, seed, random_bytes
from hashstore.local_store import HashStore
from hashstore.utils import exception_message
import hashstore.udk as udk
import datetime
from nose.tools import eq_,ok_,with_setup
import six


# to test if sniffer is not hanging uncomment next line & save
# raise Exception()

test = TestSetup(__name__,ensure_empty=True)
log = test.log



inline_udk = 'MrC91wEP7w2cJ0xXyJFdG2FiMOsHmJ1euWFGlGU1ICZRz0PPF/k+vwA=='
db_udk = '92bef2cc149396cc1cd6f3fcbe458084f34eec66c75c115ce65bee082621c898'
file_udk = '32a987ad3ced40abe090804cf1da7cefc42722b5211bdbeed62430314646ecd5'

def test_SecureStore():
    hs = HashStore(os.path.join(test.dir,'test_SecureStore'),True, secure=True)

    def select_all(tbl):
        return hs.dbf.select(tbl, {}, '1=1')

    not_existent = 'afebac2a37799077d70427c6a28ed1d99754363e1f5dd0a2b28b962d8ae15263'

    invitation = hs.create_invitation("body")
    eq_(uuid.UUID, type(invitation))
    i_rs = select_all('invitation')
    eq_(1,len(i_rs))
    eq_(invitation,i_rs[0]['invitation_id'])
    eq_(False,i_rs[0]['used'])
    eq_('body',i_rs[0]['invitation_body'])

    remote_uuid = uuid.uuid4()
    mount_id = hs.register(remote_uuid, invitation)
    eq_(uuid.UUID, type(mount_id))
    i_rs = select_all( 'invitation')
    eq_(1,len(i_rs))
    eq_(invitation,i_rs[0]['invitation_id'])
    eq_(True,i_rs[0]['used'])

    m_rs = select_all('mount')
    eq_(1,len(m_rs))
    log.info(m_rs)
    eq_(mount_id,m_rs[0]['mount_id'])
    eq_(udk.quick_hash(remote_uuid),m_rs[0]['mount_session'])

    mount_id_none = hs.register(uuid.uuid4(),invitation) # invitation should work only once
    eq_(None, mount_id_none)
    m_rs = select_all('mount')
    eq_(1,len(m_rs)) # only one mount still

    mount_id_another = hs.register(uuid.uuid4(),hs.create_invitation()) # with another invitation
    ok_(mount_id_another is not None)

    m_rs = select_all('mount')
    eq_(2,len(m_rs)) # second mount created

    push_sess = hs.login(remote_uuid)
    log.info(push_sess)

    seed(1)
    s4k = random_bytes(4000)
    h4k = hs.writer(auth=str(push_sess)).write(s4k, done=True)
    try:
        hs.writer().write(s4k, done=True)
        ok_(False)
    except:
        eq_(exception_message(),'push_session is required')
    p100k = hs.writer(push_sess)
    for _ in range(10):
        p100k.write(random_bytes(10000))
    h100k = p100k.done()
    eq_(s4k, hs.get_content(h4k,auth = push_sess).read())
    eq_(['5694182274e5a6cab47ce45024b72f94dcfd7de584f2b4432fb3556ebb870fad',
         'b99268b77ce16d561a78b9a533349e46882f2df0b735e73d7441943074e214e5'],
        [str(k) for k in hs.iterate_udks(auth=push_sess)])
    hs.logout(push_session_id=push_sess)
    try:
        hs.writer(push_sess).write(s4k, done=True)
        ok_(False)
    except:
        eq_(exception_message(),'authetification error')


def test_HashStore():
    hs = HashStore(os.path.join(test.dir,'test_HashStore'),True, secure=False)
    not_existent = 'afebac2a37799077d70427c6a28ed1d99754363e1f5dd0a2b28b962d8ae15263'

    def store():
        seed(0)
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
    seed(0)
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
    seed(0)
    eq_(str(udk.UDK.from_string(random_bytes(40))), inline_udk)
    eq_(str(udk.UDK.from_file(os.path.join(hs.root, file_udk[0:3], file_udk[3:]))), file_udk)
    for u in udks:
        hs.delete(u)
    eq_(hs.delete(not_existent),False)
    eq_(hs.delete(inline_udk),False)
    udks = list(hs.iterate_udks())
    eq_(0,len(udks))
    # ok_(False)





