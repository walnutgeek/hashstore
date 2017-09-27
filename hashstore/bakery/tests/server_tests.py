from hashstore.bakery.ids import SaltedSha
from hashstore.tests import TestSetup, file_set1, file_set2, \
    prep_mount, update_mount, fileset1_cake, fileset2_cake
import os
from time import sleep

test = TestSetup(__name__,ensure_empty=True)
log = test.log

def test_server():
    files = os.path.join(test.dir, 'files')
    store = os.path.join(test.dir, 'store')
    port=8765
    email = 'jon@doe.edu'
    pwd = 'abc'
    pwdssha = str(SaltedSha.from_secret(pwd))


    test.run_script_and_wait('hsd --store_dir {store} initdb '
                             '--port {port}'.format(**locals()),
                             expect_rc=0, expect_read='')

    server_id = test.run_script_in_bg('hsd --debug --store_dir {store} start'
                                      .format(**locals()))

    prep_mount(files, file_set1)
    test.run_script_and_wait('hsd --store_dir {store} add_user '
                             '--email {email} --password {pwdssha}'.format(**locals()),
                             expect_rc=0, expect_read='')
    acl = 'Create_Portals+'

    test.run_script_and_wait('hsd --store_dir {store} acl '
                             '--user {email} --acl {acl}'
                             .format(**locals()),
                             expect_rc=0, expect_read='''
                                User: jon@doe.edu
                                User.id: ...
                        
                                PermissionType.Create_Portals  
                                '''
                             )

    sleep(2)

    test.run_script_and_wait('hsi login --url http://localhost:{port} '
                             '--dir {files} --email {email} '
                             '--passwd {pwd}' .format(**locals()),
                             expect_rc=0,
                             expect_read="Mount: ... "
                                         "{'UserSession': ... "
                                         "'ClientID': ..." )

    test.run_script_and_wait('hsi backup --dir {files}'
                             .format(**locals()), expect_rc=0,
                             expect_read='''....
                             DirId: ...
                             Cake: '''+fileset1_cake )

    test.run_script_and_wait('hsd --store_dir {store} stop'
                          .format(**locals()), expect_rc=0)

    test.wait_process(server_id, expect_rc=0)

    # update_mount(files, file_set2)


