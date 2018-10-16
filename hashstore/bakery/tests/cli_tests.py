from hashstore.tests import (
    TestSetup, file_set1, file_set2, prep_mount, update_mount,
    fileset1_cake, fileset2_cake)
import os

test = TestSetup(__name__,ensure_empty=True)
log = test.log



def test_hsi():
    '''
usage: hs.py [-h] [--debug]
              {login,logout,ls,find,scan,backup,pull,sync,create_portal,update_vtree,delete_in_vtree,server}
              ...

hashstore

positional arguments:
  {login,logout,ls,find,scan,backup,pull,sync,create_portal,update_vtree,delete_in_vtree,server}
    login               authorize client to interact with server
    logout              logout from server
    ls                  list directory as of last scan.
    find                find file with particular criteria.
    scan                scan tree and recalculate hashes for all changed files
    backup              save local files on remote server
    pull                download remote changes for a dir
    sync                backup and pull. Use dir_id as portal.
    create_portal       Create portal
    update_vtree        Update file in vtree
    delete_in_vtree     Delete path in vtree
    server              Server subcommands...

optional arguments:
  -h, --help            show this help message and exit
  --debug               set logging level to DEBUG. default is INFO
    '''
    test.run_script_and_wait('-h',expect_rc=0,
                             expect_read=test_hsi.__doc__)


def test_hsd():
    '''
usage: hs.py [-h] [--store_dir store_dir] [--debug]
             {initdb,add_user,remove_user,acl,backup,pull,start,stop} ...

hashstore server subcomands

positional arguments:
  {initdb,add_user,remove_user,acl,backup,pull,start,stop}
    initdb              initialize storage and set host specific parameters
    add_user
    remove_user
    acl                 Manage ACL
    backup              Backup dir
    pull                Restore dir
    start               start server
    stop                stop server

optional arguments:
  -h, --help            show this help message and exit
  --store_dir store_dir
                        a directory where hashstore data resides. Default is:
                        '.'.
  --debug               set logging level to DEBUG. default is INFO
    '''
    test.run_script_and_wait('server -h',expect_rc=0,
                             expect_read=test_hsd.__doc__)
    test.run_script_and_wait('server ',expect_rc=0,
                             expect_read=test_hsd.__doc__)


def test_scan_ls():
    files = os.path.join(test.dir, 'files')
    prep_mount(files, file_set1)

    test.run_script_and_wait('ls --dir %s' % files, expect_rc=1,
                             expect_read='''
                Traceback (most recent call last):
                ....
                ValueError: ... was not scanned
    ''' )

    test.run_script_and_wait('scan --dir %s' % files,expect_rc=0,
                             expect_read=fileset1_cake)

    test.run_script_and_wait('ls --dir %s' % files,expect_rc=0,
                             expect_read='''
        DirId: ...
        Cake: %s
        
          FILE  105000  too.sol
          DIR   10955   q
          DIR   1885    x
          DIR   1658    a
        total_size: 119498
        ''' % fileset1_cake)

    find_it = '2bg6Kulsn2wvvHOasBTQDI7qES4cgQUkB4GUgOIYs9Oa'
    test.run_script_and_wait('ls --cake --dir %s/x' % files,
                             expect_rc=0,
                             expect_read='''
        DirId: ...
        Cake: 34XHLt5jTMO6ALkRX1fvVE7CU0wAUu2nRbe3BasjZXHz
        
          DIR   1220  3kBWUQBPWaAakYFtDxdYBvLWkX3TWSguqVaY3OMyDz1Q  y
          FILE  555   {find_it}  1
        total_size: 1775
        '''.format(**locals()))

    test.run_script_and_wait('find --cake {find_it} --dir {files}'
                             .format(**locals()) ,
                             expect_rc=0,
                             expect_read='FILE  555 ...')

    update_mount(files, file_set2)


    test.run_script_and_wait('scan --dir %s' % files, expect_rc=0,
                             expect_read=fileset2_cake)

    test.run_script_and_wait('ls --dir %s' % files, expect_rc=0,
                             expect_read='''
          DirId: ...
          Cake: %s

            DIR   107941  x
            FILE  105000  too.sol
            DIR   10955   q
            DIR   1742    a
          total_size: 225638''' % fileset2_cake)

    store = os.path.join(test.dir, 'store')
    email = 'jon@doe.edu'
    pwd = '{SSHA}V5tjhtb8YXcHCDw2wuUHFe2xKrZOQ1mR'

    test.run_script_and_wait('server --store_dir {store} initdb'.format(**locals()),
                             expect_rc=0, expect_read='')
    test.run_script_and_wait('server --store_dir {store} add_user '
                             '--email {email} --password {pwd}'.format(**locals()),
                             expect_rc=0, expect_read='')
    acls = (
        ('Write_Any_Data+', 0, '''
        User: jon@doe.edu
        User.id: ...

        PermissionType.Write_Any_Data  
        '''),
        ('Read_+', 1, '''
        Traceback (most recent call last):
        ....
        ValueError: cake field is required for permission: Read_
        '''),
        ('Read_:1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV+', 0, '''
            User: jon@doe.edu
            User.id: ...
            
              PermissionType.Read_           1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV
              PermissionType.Write_Any_Data  

        '''),
        ('Read_:1yyAFLvoP5tMWKaYiQBbRMB5LIznJAz4ohVMbX2XkSvV-', 0, '''
            User: jon@doe.edu
            User.id: ...
            
              PermissionType.Write_Any_Data  
        ''')
    )
    for acl,rc,text in acls:
        test.run_script_and_wait('server --store_dir {store} acl '
                                 '--user {email} --acl {acl}'.format(**locals()),
                                 expect_rc=rc, expect_read=text)
    test.run_script_and_wait('server --store_dir {store} acl '
                             '--user {email}'.format(**locals()),
                             expect_rc = 0)

    test.run_script_and_wait('server --store_dir {store} backup --dir {files}'.format(**locals()),
                             expect_rc=0)

    test.run_script_and_wait('server --store_dir {store} remove_user '
                             '--user {email}'.format(**locals()),
                             expect_rc=0)

    pull_cake = fileset2_cake
    pull_dir = os.path.join(test.dir, 'pull')
    test.run_script_and_wait('server --store_dir {store} pull '
                             '--cake {pull_cake} --dir {pull_dir}'.format(**locals()),
                             expect_rc=0)

    test.run_script_and_wait('scan --dir {pull_dir}'.format(**locals()),
                             expect_rc=0, expect_read=fileset2_cake)

    pull_cake2 = fileset1_cake
    pull_dir2 = os.path.join(test.dir, 'pullpath')
    test.run_script_and_wait('server --store_dir {store} pull '
                             '--cake /{pull_cake2} --dir {pull_dir2}'.format(**locals()),
                             expect_rc=1,
                             expect_read='''
                                Traceback (most recent call last):
                                ....
                                hashstore.bakery.NotFoundError''')

    test.run_script_and_wait('server --store_dir {store} pull '
                             '--cake {pull_cake2} --dir {pull_dir2}'.format(**locals()),
                             expect_rc=1,
                             expect_read='''
                                Traceback (most recent call last):
                                ....
                                hashstore.bakery.NotFoundError''')

    test.run_script_and_wait('server --store_dir {store} pull '
                             '--cake /{pull_cake} --dir {pull_dir2}'.format(**locals()),
                             expect_rc=0)

    test.run_script_and_wait('scan --dir {pull_dir2}'.format(**locals()),
                             expect_rc=0, expect_read=fileset2_cake)
