from nose.tools import eq_

from hashstore.bakery import SaltedSha, Cake, Role, KeyStructure
from hashstore.tests import TestSetup, file_set1, file_set2, \
    prep_mount, update_mount, fileset1_cake, fileset2_cake
import os
from time import sleep


class ServerSetup:
    def __init__(self, test, port=None, shutdown=True):
        self.test = test
        self.store = os.path.join(test.dir, 'store')
        self.port = 8765 if port is None else port
        self.shutdown = shutdown

    def do_shutdown(self):
        test.run_script_and_wait(
            'hsd --store_dir {self.store} stop'
                .format(**locals()), expect_rc=0)

    def run_server_tests(self):
        log = self.test.log
        mount = os.path.join(self.test.dir, 'mount')
        files = os.path.join(mount, 'files')
        pull = os.path.join(mount, 'pull')
        os.makedirs(mount, mode=0o755)
        email = 'jon@doe.edu'
        pwd = 'abc'
        pwdssha = str(SaltedSha.from_secret(pwd))

        test.run_script_and_wait(
            'hsd --store_dir {self.store} initdb '
            '--port {self.port}'.format(**locals()),
            expect_rc=0, expect_read='')

        server_id = self.test.run_script_in_bg(
            'hsd --debug --store_dir {self.store} start'
                .format(**locals()))

        prep_mount(files, file_set1)
        self.test.run_script_and_wait(
            'hsd --store_dir {self.store} add_user '
            '--email {email} --password {pwdssha}'.format(
                **locals()),
            expect_rc=0, expect_read='')
        acl = 'Create_Portals+'

        self.test.run_script_and_wait(
            'hsd --store_dir {self.store} acl '
            '--user {email} --acl {acl}'
            .format(**locals()),
            expect_rc=0, expect_read='''
                                    User: jon@doe.edu
                                    User.id: ...
    
                                    PermissionType.Create_Portals  
                                    '''
            )

        sleep(2)

        cake1, cake2 = fileset1_cake, fileset2_cake

        self.test.run_script_and_wait(
            'hsi login --url http://localhost:{self.port} '
            '--dir {mount} --email {email} '
            '--passwd {pwd} --default'.format(**locals()),
            expect_rc=0,
            expect_read="Mount: ... "
                        "{'UserSession': ... "
                        "'ClientID': ...")

        _, save_words = self.test.run_script_and_wait(
            'hsi create_portal --portal_type VTREE '
            '--portal_role NEURON', expect_rc=0,
            expect_read='''Portal: ...
            Cake: None
            ''',save_words=[])
        new_portal = Cake.ensure_it(save_words[0])
        eq_(new_portal.role, Role.NEURON)
        eq_(new_portal.key_structure, KeyStructure.PORTAL_VTREE)

        self.test.run_script_and_wait(
            'hsi update_vtree --cake_path /{new_portal!s}/x/y/2 '
            '--cake 2qt2ruOzhiWD6am3Hmwkh6B7aLEe77u9DbAYoLTAHeO4'
                .format(**locals()), expect_rc=0, expect_read=
                    'WARNING:__main__:Server does not have '
                    '2qt2ruOzhiWD6am3Hmwkh6B7aLEe77u9DbAYoLTAHeO4 stored.\n'
                    'CPath: ...\n'
                    'Cake: 2qt2ruOzhiWD6am3Hmwkh6B7aLEe77u9DbAYoLTAHeO4')

        self.test.run_script_and_wait(
            'hsi update_vtree --cake_path /{new_portal!s}/x/y/2 '
            '--file {files!s}/x/y/2'
                .format(**locals()), expect_rc=0, expect_read=
                    'CPath: ...\n'
                    'Cake: 2qt2ruOzhiWD6am3Hmwkh6B7aLEe77u9DbAYoLTAHeO4')

        _, save_words = self.test.run_script_and_wait(
            'hsi backup --dir {files}'
                .format(**locals()), expect_rc=0,
            expect_read='''....
            DirId: ...
            Cake: {cake1}'''.format(**locals()), save_words=[])
        dirId = save_words[0]

        update_mount(files, file_set2)

        self.test.run_script_and_wait(
            'hsi backup --dir {files}'
                .format(**locals()), expect_rc=0,
            expect_read='''....
            DirId: {dirId!s}
            Cake: {cake2}'''.format(**locals()))

        self.test.run_script_and_wait(
            'hsi pull --cake {dirId} --dir {pull}'
                .format(**locals()), expect_rc=0,
            expect_read='From: {dirId!s}\n'
                        'Cake: {cake2}\n'
                .format(**locals()))

        self.test.run_script_and_wait(
            'hsi scan --dir {pull}'
                .format(**locals()), expect_rc=0,
            expect_read=fileset2_cake)

        self.test.run_script_and_wait(
            'hsi update_vtree '
            '--cake_path /{new_portal!s}/x/y/1 '
            '--file {files!s}/x/y/1'
                .format(**locals()), expect_rc=0, expect_read=
                    'CPath: ...\n'
                    'Cake: 2S5IatGd3u7Z7u5cptzH3SXhru9ACPGJgdT32QduZ8Df')

        self.test.run_script_and_wait(
            'hsi update_vtree '
            '--cake_path /{new_portal!s}/x/y/1 '
            '--file {files!s}/x/y/3'
                .format(**locals()), expect_rc=0, expect_read=
                    'CPath: ...\n'
                    'Cake: 2qt2ruOzhiWD6am3Hmwkh6B7aLEe77u9DbAYoLTAHeO4')

        self.test.run_script_and_wait(
            'hsi update_vtree '
            '--cake_path /{new_portal!s}/x/z/3 '
            '--file {files!s}/x/y/3'
                .format(**locals()), expect_rc=0, expect_read=
                    'CPath: ...\n'
                    'Cake: 2qt2ruOzhiWD6am3Hmwkh6B7aLEe77u9DbAYoLTAHeO4')

        self.test.run_script_and_wait(
            'hsi delete_in_vtree --cake_path /{new_portal!s}/x/y/2 '
                .format(**locals()), expect_rc=0, expect_read=
                    'Deleted: /{new_portal!s}/x/y/2'.format(**locals()))


        self.test.run_script_and_wait(
            'hsi delete_in_vtree --cake_path /{new_portal!s}/x/z'
                .format(**locals()), expect_rc=0, expect_read=
                    'Deleted: /{new_portal!s}/x/z'.format(**locals()))

        self.test.run_script_and_wait(
            'hsi delete_in_vtree --cake_path /{new_portal!s}/x/z'
                .format(**locals()), expect_rc=0, expect_read=
                    'Not there: /{new_portal!s}/x/z'.format(**locals()))

        if self.shutdown:
            self.do_shutdown()
            self.test.wait_process(server_id, expect_rc=0)


if __name__ == '__main__':
    from sys import argv
    root = argv[1] if len(argv)>=2 else '.'
    port = int(argv[2]) if len(argv)>=3 else None
    test = TestSetup('server_tests', root=root,
                     ensure_empty=False, script_mode=True)
    setup = ServerSetup(test,port,shutdown=False)
    if len(argv)>=4:
        getattr(setup,argv[3])()
    else:
        setup.run_server_tests()
else:
    test = TestSetup(__name__, ensure_empty=True)


def test_server():
    ServerSetup(test).run_server_tests()




