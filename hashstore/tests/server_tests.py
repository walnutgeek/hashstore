import os
import time
from nose.tools import eq_,ok_,with_setup
from hashstore.local_store import AccessMode
import hashstore.mount as mount

from hashstore.tests import TestSetup, file_set1, file_set2, prep_mount, fileset1_udk, fileset2_udk

test = TestSetup(__name__,ensure_empty=True)
log = test.log


test_config = os.path.join(os.path.dirname(__file__), 'hashery.back-it-up')
substitutions = {'{test_dir}': test.dir}


def test_all_access_modes():
    def do_test(secure, use_config = True):
        test.reset_all_process()
        if secure == False:
            do_invitation = False
            server_opt = ' --insecure'
            access_mode = AccessMode.INSECURE
        else:
            if secure is None:
                server_opt = ''
                access_mode = AccessMode.WRITE_SECURE
            else:
                server_opt = ' --secure'
                access_mode = AccessMode.ALL_SECURE
            do_invitation = True
        store_dir=access_mode.name+'_' + ('conf' if use_config else 'cmd')

        insecured_read_access = access_mode == AccessMode.ALL_SECURE

        hashery_dir = os.path.join(test.dir, store_dir)
        os.makedirs(hashery_dir)
        files = os.path.join(test.dir, 'sfiles')
        prep_mount(files, file_set1)

        port = 9753
        yaml_config = hashery_dir + '.yaml'
        if use_config:
            open(yaml_config, 'w').write(
'''store_dir: {hashery_dir}
port: {port}
access_mode: {access_mode.name}
mounts:
  files: {files}
'''.format(**locals())
            )
            test.run_shash('d start --config '+yaml_config)
        else:
            test.run_shash('d start --store_dir {hashery_dir} --port {port}'
                       '{server_opt}'.format(**locals()))
        time.sleep(3)
        if do_invitation:
            invite_log = test.full_log_path(store_dir + '_invite.log')
            if use_config:
                rc,invitation = test.run_shash_and_wait(
                    'd invite --config ' + yaml_config, invite_log)
            else:
                rc,invitation = test.run_shash_and_wait(
                    'd invite --store_dir {hashery_dir}'.format(**locals()), invite_log)
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
        if use_config:
            test.run_shash_and_wait('d stop --config ' +yaml_config)
        else:
            test.run_shash_and_wait('d stop --port %d' % port)
        # test.wait_bg()
        # ok_(False)
    for use_config in (True, False):
        do_test(False, use_config)
        do_test(None, use_config)
        do_test(True, use_config)


def test_dummies():
    test.run_shash('nonsense')
