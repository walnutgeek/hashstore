import os
import time
from nose.tools import eq_,ok_,with_setup

import hashstore.mount as mount

from hashstore.tests import TestSetup, file_set1, file_set2, prep_mount, fileset1_udk, fileset2_udk

test = TestSetup(__name__,ensure_empty=True)
log = test.log


test_config = os.path.join(os.path.dirname(__file__), 'hashery.back-it-up')
substitutions = {'{test_dir}': test.dir}

import hashstore.backup

def test_backup():
    hashery_dir = os.path.join(test.dir, 'insecure')
    os.makedirs(hashery_dir)
    port = 9753
    test.run_shash( 'start --insecure --store_dir %s --port %d' % (hashery_dir, port), 'noauth_start.log')
    time.sleep(2)
    files = os.path.join(test.dir, 'files')
    prep_mount(files, file_set1)
    b = hashstore.backup.Backup.from_config(test_config, os.path.join(test.dir,'backup.db'), substitutions)
    v1 = b.backup()
    prep_mount(files, file_set2)
    v2 = b.backup()
    eq_(str(v1[files]), fileset1_udk)
    eq_(str(v2[files]), fileset2_udk)
    f1 = os.path.join(test.dir, 'files1')
    b.restore(v1[files], f1)
    f2 = os.path.join(test.dir, 'files2')
    b.restore(v2[files], f2)
    eq_(str(mount.MountDB(f1).scan()[1]), fileset1_udk)
    eq_(str(mount.MountDB(f2).scan()[1]), fileset2_udk)
    test.run_shash('stop --port %d' % port, 'shut.log').wait()
    time.sleep(.5)


def test_secure():
    hashery_dir = os.path.join(test.dir, 'secure')
    os.makedirs(hashery_dir)
    invite_log = test.full_log_path('invite.log')
    rc = test.run_shash( 'invite --store_dir %s' % (hashery_dir), invite_log).wait()
    eq_(rc, 0)
    invitation = open(invite_log).read().strip()
    eq_(len(invitation),36)
    eq_(sum(1 for c in invitation if '-' == c), 4)
    time.sleep(.1)
    log.info(invitation)
    port = 9753
    test.run_shash( 'start --store_dir %s --port %d' % (hashery_dir, port), 'secure_start.log')
    time.sleep(2)

    # files = os.path.join(test.dir, 'sfiles')
    # prep_mount(files, file_set1)
    # b = hashstore.backup.Backup.from_config(test_config, os.path.join(test.dir,'backup.db'), substitutions)
    # v1 = b.backup()
    # prep_mount(files, file_set2)
    # v2 = b.backup()
    # eq_(str(v1[files]), fileset1_udk)
    # eq_(str(v2[files]), fileset2_udk)
    # f1 = os.path.join(test.dir, 'sfiles1')
    # b.restore(v1[files], f1)
    # f2 = os.path.join(test.dir, 'sfiles2')
    # b.restore(v2[files], f2)
    # eq_(str(mount.MountDB(f1).scan()[1]), fileset1_udk)
    # eq_(str(mount.MountDB(f2).scan()[1]), fileset2_udk)
    test.run_shash('stop --port %d' % port, 'secure_shut.log').wait()


def test_dummies():
    test.run_shash('register')
    test.run_shash('backup')
    test.run_shash('nonsense')
