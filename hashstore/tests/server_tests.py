import os
import time
from nose.tools import eq_,ok_,with_setup
from hashstore.local_store import AccessMode
from hashstore.udk import quick_hash

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

        secured_read_access = access_mode == AccessMode.ALL_SECURE

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
        if not(secured_read_access):
            import requests

            def get_and_match(url, hexdigest=None, grep=None, status_code=None):
                resp = requests.get(url)
                if status_code is not None:
                    eq_(resp.status_code, status_code)
                content = resp.content
                h = quick_hash(content)
                if hexdigest is not None:
                    eq_(h, hexdigest)
                if grep is not None:
                    for g in grep:
                        ok_(g in content)

            server_url = 'http://localhost:{port}/'.format(**locals())
            raw_url = server_url + '.raw/'
            get_and_match(raw_url + fileset1_udk + '/../abc',status_code=404)
            get_and_match(raw_url + fileset1_udk + '/',
                          hexdigest=fileset1_udk[1:])
            grep_index = [b'{"columns": [{"name": "mount", "type": "link"}']
            get_and_match(raw_url, grep = grep_index)
            get_and_match(raw_url +'index', grep = grep_index)
            get_and_match(raw_url+fileset1_udk+'/a/b/2',
                          hexdigest='8d6eaa485bc21f46df59127f4670a8ad7ae14d8ea2064efff49aae8e2a8fb8e4')
            grep_index_html = [b'<script src="/.app/hashstore.js"></script>']
            get_and_match(server_url +'.app/index.html', None, grep_index_html)
            get_and_match(server_url +'any/other/link', None, grep_index_html)
            if use_config:
                get_and_match(raw_url+'files/',None,[b'{"columns": [{"name": "filename", "type": "link"}, {"name": "size", "type": "number"}, {"name": "type", "type": "string"}, {"name": "mime", "type": "string"}]}\n'])
                get_and_match(raw_url+'files/a/b/2', '8d6eaa485bc21f46df59127f4670a8ad7ae14d8ea2064efff49aae8e2a8fb8e4')

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
    # do_test(None, True)


def test_dummies():
    test.run_shash('nonsense')
