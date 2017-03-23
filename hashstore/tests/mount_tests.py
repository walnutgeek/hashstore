import six
import hashstore.mount as mount
import hashstore.udk as udk
from hashstore.utils import json_encoder
import json
from nose.tools import eq_,ok_,with_setup
from hashstore.tests import prep_mount,file_set1, zzzetup



# to test if sniffer is not hanging uncomment next line & save
# raise Exception()


log,test_dir = zzzetup(__name__)

prep_mount(test_dir,file_set1)

m = mount.MountDB(test_dir, scan_now=True)


def test_mount():
    eq_(str(m.last_hash), 'X88a9b058784619c42e4d630812a8d0a20cd112a1b97d9735c4542bf7ac0664c5')
    eq_(0, len(m.select('file', {'name': '1.sol'}))) # ignored file
    eq_(1, len(m.select('file', {'name': 'c'}))) # empty directory
    eq_(1, len(m.select('file', {'name': '2.b'})))
    eq_(1, len(m.select('file', {'name': 'too.sol'})))
    # ok_(False)

def test_group_by():
    for k,v in six.iteritems(mount.ScanTree(m).directories):
        digest = udk.process_stream(six.BytesIO(json_encoder.encode(v)))[0]
        ok_(k,digest.hexdigest())

    # ok_(False)
