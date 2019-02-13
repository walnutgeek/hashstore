import json

from hs_build_tools.nose import eq_,ok_

from hashstore.kernel.bakery import Cake, CakeRole, CakeType, CakePath
from hashstore.tests import (sqlite_q, TestSetup, file_set1, file_set2,
    prep_mount, update_mount, fileset1_cake, fileset2_cake)
import os
from time import sleep
import urllib.request
import logging

from hashstore.kernel.hashing import SaltedSha

log = logging.getLogger(__name__)


def http_GET(u):

    out = urllib.request.urlopen(u).read()
    log.info(f'{u} -> {out if len(out) < 100 else len(out)}')
    return out


class ServerSetup:
    def __init__(self, test, port=None, shutdown=True):
        self.test = test
        self.store = os.path.join(test.dir, 'store')
        self.port = 8765 if port is None else port
        self.shutdown = shutdown

    def do_shutdown(self):
        self.test.run_script_and_wait(
            f'server --store_dir {self.store} stop',
            expect_rc=0)

    def run_server_tests(self):
        log = self.test.log
        mount = os.path.join(self.test.dir, 'mount')
        files = os.path.join(mount, 'files')
        pull = os.path.join(mount, 'pull')
        os.makedirs(mount, mode=0o755)
        email = 'jon@doe.edu'
        pwd = 'abc'
        pwdssha = str(SaltedSha.from_secret(pwd))

        self.test.run_script_and_wait(
            f'server --store_dir {self.store} initdb '
            f'--port 7623',
            expect_rc=0, expect_read='')

        server_db = os.path.join(self.store, "server.db")
        server_key = sqlite_q(server_db,'select * from server_key')
        eq_(len(server_key),1)
        eq_(server_key[0][3:],(None, 7623, 10))
        server_id = server_key[0][1]

        self.test.run_script_and_wait(
            f'server --store_dir {self.store} initdb '
            f'--port {self.port}',
            expect_rc=0, expect_read='')

        server_key = sqlite_q(server_db,'select * from server_key')
        eq_(len(server_key),1)
        eq_(server_key[0][3:],(None, 8765, 10))
        eq_(server_id, server_key[0][1])

        server_id = self.test.run_script_in_bg(
            f'server --debug --store_dir {self.store} start')

        prep_mount(files, file_set1)
        self.test.run_script_and_wait(
            f'server --store_dir {self.store} add_user '
            f'--email {email} --password {pwdssha}',
            expect_rc=0, expect_read='')
        acl = 'Create_Portals+'

        self.test.run_script_and_wait(
            f'server --store_dir {self.store} acl '
            f'--user {email} --acl {acl}',
            expect_rc=0, expect_read='''
                                    User: jon@doe.edu
                                    User.id: ...
    
                                    PermissionType.Create_Portals  
                                    '''
            )

        sleep(2)

        pid = int(http_GET(f'http://localhost:{self.port}/-/pid'))
        config_id, ssha_from_secret = json.loads(http_GET(
            f'http://localhost:{self.port}/-/server_id'))
        ok_( b'/-/app/' in http_GET(f'http://localhost:{self.port}/') )
        ok_( len(http_GET(f'http://localhost:{self.port}/favicon.ico'))
             > 33000 )
        ok_( len(http_GET(f'http://localhost:{self.port}/-/app/app.js'))
             > 1000000 )


        cake1, cake2 = fileset1_cake, fileset2_cake

        self.test.run_script_and_wait(
            'login --url http://localhost:{self.port} '
            '--dir {mount} --email {email} '
            '--passwd {pwd} --default'.format(**locals()),
            expect_rc=0,
            expect_read="Mount: ... "
                        "ClientID: ... "
                        "UserSession: ... ")

        _, save_words = self.test.run_script_and_wait(
            'create_portal --portal_type VTREE '
            '--portal_role NEURON', expect_rc=0,
            expect_read='''Portal: ...
            Cake: None
            ''',save_words=[])
        new_portal = Cake.ensure_it(save_words[0])
        eq_(new_portal.header.role, CakeRole.NEURON)
        eq_(new_portal.header.type, CakeType.VTREE)

        self.test.run_script_and_wait(
            f'update_vtree --cake_path /{new_portal!s}/x/y/2 '
            f'--cake 2IsihvsxHhiUrp5otlJ4f1olJldHAzNHOLaMuIPXnm9P'
            , expect_rc=0, expect_read=
                'WARNING:hs: Server does not have '
                '2IsihvsxHhiUrp5otlJ4f1olJldHAzNHOLaMuIPXnm9P stored.\n'
                'CPath: ...\n'
                'Cake: 2IsihvsxHhiUrp5otlJ4f1olJldHAzNHOLaMuIPXnm9P')

        self.test.run_script_and_wait(
            f'update_vtree --cake_path /{new_portal!s}/x/y/2 '
            f'--file {files!s}/x/y/2',
            expect_rc=0, expect_read=
                    'CPath: ...\n'
                    'Cake: 2IsihvsxHhiUrp5otlJ4f1olJldHAzNHOLaMuIPXnm9P')
        rpaths = []
        for portal_type in [ 'VTREE', 'PORTAL' ]:
            _, save_words = self.test.run_script_and_wait(
                'backup --dir {files} --portal_type {portal_type}'
                    .format(**locals()), expect_rc=0,
                expect_read=f'''....
                DirId: ...
                RemotePath: ...
                Cake: {cake1}'''.format(**locals()), save_words=[])
            dirId = save_words[0]
            rpaths.append(CakePath(save_words[1]))
        update_mount(files, file_set2)

        for i,rpath in enumerate(rpaths):
            stored = rpath.root
            self.test.run_script_and_wait(
                f'backup --dir {files} --remote_path {rpath!s}',
                expect_rc=0,
                expect_read=f'''....
                DirId: {dirId!s}
                RemotePath: /{stored!s}/
                Cake: {cake2}''')

            outx = os.path.join(mount, 'out%d' % i)
            match_cake = cake2 if i == 1 else 'None'
            self.test.run_script_and_wait(
                f'pull --cake {stored!s} --dir {outx}',
                expect_rc=0,
                expect_read='From: ...\n'
                            f'Cake: {match_cake}\n')

            self.test.run_script_and_wait(
                f'scan --dir {outx}',
                expect_rc=0,
                expect_read=fileset2_cake)

        self.test.run_script_and_wait(
            'update_vtree '
            '--cake_path /{new_portal!s}/x/y/1 '
            '--file {files!s}/x/y/1'
                .format(**locals()), expect_rc=0, expect_read=
                    'CPath: ...\n'
                    'Cake: 2f3WYb52iUTL1WqN55lZ6Md8zl9Rk7vNlSs0nzECYQmh')

        self.test.run_script_and_wait(
            'update_vtree '
            '--cake_path /{new_portal!s}/x/y/1 '
            '--file {files!s}/x/y/3'
                .format(**locals()), expect_rc=0, expect_read=
                    'CPath: ...\n'
                    'Cake: 2IsihvsxHhiUrp5otlJ4f1olJldHAzNHOLaMuIPXnm9P')

        self.test.run_script_and_wait(
            'update_vtree '
            '--cake_path /{new_portal!s}/x/z/3 '
            '--file {files!s}/x/y/3'
                .format(**locals()), expect_rc=0, expect_read=
                    'CPath: ...\n'
                    'Cake: 2IsihvsxHhiUrp5otlJ4f1olJldHAzNHOLaMuIPXnm9P')

        self.test.run_script_and_wait(
            'delete_in_vtree --cake_path /{new_portal!s}/x/y/2 '
                .format(**locals()), expect_rc=0, expect_read=
                    'Deleted: /{new_portal!s}/x/y/2'.format(**locals()))


        self.test.run_script_and_wait(
            'delete_in_vtree --cake_path /{new_portal!s}/x/z'
                .format(**locals()), expect_rc=0, expect_read=
                    'Deleted: /{new_portal!s}/x/z'.format(**locals()))

        self.test.run_script_and_wait(
            'delete_in_vtree --cake_path /{new_portal!s}/x/z'
                .format(**locals()), expect_rc=0, expect_read=
                    'Not there: /{new_portal!s}/x/z'.format(**locals()))

        if self.shutdown:
            self.do_shutdown()
            self.test.wait_process(server_id, expect_rc=[0,2])


def test_server():
    test = TestSetup(__name__, ensure_empty=False)
    server=ServerSetup(test)
    # on windows if server kept running you cannot erase dir, 
    # then uncomment bellow:
    # server.do_shutdown()
    test.ensure_empty()
    server.run_server_tests()


if __name__ == '__main__':
    from sys import argv
    root = argv[1] if len(argv)>=2 else '.'
    port = int(argv[2]) if len(argv)>=3 else None
    setup = ServerSetup( 
        TestSetup('server_tests', root=root, ensure_empty=False, script_mode=True),
        port, shutdown=False)
    if len(argv)>=4:
        getattr(setup,argv[3])()
    else:
        setup.run_server_tests()



