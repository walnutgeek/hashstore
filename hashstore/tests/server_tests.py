import os
import time
from nose.tools import eq_,ok_,with_setup

import hashstore.mount as mount

from hashstore.tests import TestSetup, file_set1, file_set2, prep_mount, fileset1_udk, fileset2_udk

test = TestSetup(__name__,ensure_empty=True)
log = test.log


test_config = os.path.join(os.path.dirname(__file__), 'hashery.back-it-up')
substitutions = {'{test_dir}': test.dir}


def test_all_access_modes():
    def do_test(secure):
        test.reset_all_process()
        if secure == False:
            store_dir = 'insecure2'
            do_invitation = False
            server_opt = ' --insecure'
        else:
            if secure is None:
                store_dir = 'write'
                server_opt = ''
            else:
                store_dir = 'secure'
                server_opt = ' --secure'
            do_invitation = True

        hashery_dir = os.path.join(test.dir, store_dir)
        os.makedirs(hashery_dir)

        files = os.path.join(test.dir, 'sfiles')
        prep_mount(files, file_set1)

        port = 9753
        test.run_shash('start --store_dir {hashery_dir} --port {port}'
                       '{server_opt}'.format(**locals()))
        time.sleep(2)
        if do_invitation:
            invite_log = test.full_log_path(store_dir + '_invite.log')
            rc,invitation = test.run_shash_and_wait(
                'invite --store_dir {hashery_dir}'.format(**locals()), invite_log)
            eq_(rc, 0)
            invitation = open(invite_log).read().strip().split()[-1]
            eq_(len(invitation),36)
            eq_(sum(1 for c in invitation if '-' == c), 4)

            time.sleep(.1)
            log.info(invitation)

            test.run_shash_and_wait('register --url http://localhost:{port}/ '
                                    '--invitation {invitation} '
                                    '--dir {files}'.format(**locals()))
        else:
            test.run_shash_and_wait('register --url http://localhost:{port}/ '
                                    '--dir {files}'.format(**locals()))

        _,h1 = test.run_shash_and_wait('backup --dir {files}'.format(**locals()))

        prep_mount(files, file_set2, keep_shamo=True)
        _,h2 = test.run_shash_and_wait('backup --dir {files}'.format(**locals()))
        eq_(h1, fileset1_udk)
        eq_(h2, fileset2_udk)
        f1 = os.path.join(test.dir, 'sfiles1')
        test.run_shash_and_wait('restore --dir {files} --udk {h1} '
                                '--dest {f1}'.format(**locals()))

        f2 = os.path.join(test.dir, 'sfiles2')
        test.run_shash_and_wait('restore --dir {files} --udk {h2} '
                                '--dest {f2}'.format(**locals()))

        _, s1 = test.run_shash_and_wait('scan --dir {f1}'.format(**locals()))
        _, s2 = test.run_shash_and_wait('scan --dir {f2}'.format(**locals()))
        eq_(s1, fileset1_udk)
        eq_(s2, fileset2_udk)
        test.run_shash_and_wait('stop --port %d' % port)
        # test.wait_bg()
        # ok_(False)
    do_test(False)
    do_test(None)
    do_test(True)


def test_dummies():
    test.run_shash('nonsense')
