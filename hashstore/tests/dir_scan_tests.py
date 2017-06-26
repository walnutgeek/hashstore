from hashstore.tests import doctest_it
from nose.tools import eq_,ok_
import os
import hashstore.dir_scan
import time

from hashstore.tests import TestSetup, file_set1, file_set2, \
    prep_mount, fileset1_udk, fileset2_udk, update_mount

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_scan():
    files = os.path.join(test.dir, 'sfiles')
    prep_mount(files, file_set1)
    eq_(str(hashstore.dir_scan.DirScan(files).udk()), fileset1_udk)

    time.sleep(1.01)
    update_mount(files, file_set2)
    eq_(str(hashstore.dir_scan.DirScan(files).udk()), fileset2_udk)
    # ok_(False)


def test_docs():
    doctest_it(hashstore.dir_scan)
