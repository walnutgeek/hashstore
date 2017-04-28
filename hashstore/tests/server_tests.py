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
    test.run_shash_and_wait('stop --port %d' % port, 'shut.log')

    time.sleep(.5)


def test_secure():
    test.reset_all_process()
    hashery_dir = os.path.join(test.dir, 'secure')
    os.makedirs(hashery_dir)
    invite_log = test.full_log_path('invite.log')
    rc,invitation = test.run_shash_and_wait( 'invite --store_dir %s' % (hashery_dir), invite_log)
    eq_(rc, 0)
    invitation = open(invite_log).read().strip().split()[-1]
    eq_(len(invitation),36)
    eq_(sum(1 for c in invitation if '-' == c), 4)
    time.sleep(.1)
    log.info(invitation)
    port = 9753
    test.run_shash( 'start --store_dir {hashery_dir} --port {port}'.format(**locals()), 'secure_start.log')
    time.sleep(2)

    files = os.path.join(test.dir, 'sfiles')
    prep_mount(files, file_set1)
    test.run_shash_and_wait('register --url http://localhost:{port}/ --invitation {invitation} --dir {files}'.format(**locals()))
    _,h1 = test.run_shash_and_wait('backup --dir {files}'.format(**locals()))

    prep_mount(files, file_set2, keep_shamo=True)
    _,h2 = test.run_shash_and_wait('backup --dir {files}'.format(**locals()))
    eq_(h1, fileset1_udk)
    eq_(h2, fileset2_udk)
    f1 = os.path.join(test.dir, 'sfiles1')
    test.run_shash_and_wait('restore --dir {files} --udk {h1} --dest {f1}'.format(**locals()))

    f2 = os.path.join(test.dir, 'sfiles2')
    test.run_shash_and_wait('restore --dir {files} --udk {h2} --dest {f2}'.format(**locals()))

    _, s1 = test.run_shash_and_wait('scan --dir {f1}'.format(**locals()))
    _, s2 = test.run_shash_and_wait('scan --dir {f2}'.format(**locals()))
    eq_(s1, fileset1_udk)
    eq_(s2, fileset2_udk)
    test.run_shash_and_wait('stop --port %d' % port, 'secure_shut.log')
    # test.wait_bg()
    # ok_(False)


def test_dummies():
    test.run_shash('nonsense')
