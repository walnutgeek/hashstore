import six
import hashstore.mount as mount
import hashstore.udk as udk
from hashstore.utils import json_encoder,ensure_bytes
import json
from nose.tools import eq_,ok_,with_setup
from hashstore.tests import prep_mount,file_set1,update_mount, \
    file_set2,fileset2_udk, TestSetup, fileset1_udk



# to test if sniffer is not hanging uncomment next line & save
# raise Exception()


test = TestSetup(__name__,ensure_empty=True)
log = test.log

prep_mount(test.dir, file_set1)
m = mount.MountDB(test.dir, scan_now=True)


def test_mount():
    eq_(str(m.last_hash), fileset1_udk)
    eq_(0, len(m.select('file', {'name': '1.sol'}))) # ignored file
    eq_(1, len(m.select('file', {'name': 'c'})))  # empty directory
    eq_(1, len(m.select('file', {'name': '2.b'})))
    eq_(1, len(m.select('file', {'name': 'too.sol'})))
    # ok_(False)
    update_mount(test.dir, file_set2)

    m.scan()
    eq_(str(m.last_hash), fileset2_udk)

def test_group_by():
    for k,v in six.iteritems(mount.ScanTree(m).directories):
        digest = udk.process_stream(six.BytesIO(ensure_bytes(json_encoder.encode(v))))[0]
        ok_(k,digest)

    # ok_(False)
