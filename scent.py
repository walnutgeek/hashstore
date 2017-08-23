import os

from sniffer.api import *

@file_validator
def py_files(filename):
    return filename.endswith('.py') or filename.endswith('.yaml') or filename.endswith('.rst')

run_envs = [ 'py2', 'py3' ]
env_template = '. activate %s; coverage run -p -m nose %s'
combine_cmd = '. activate py2; coverage combine; coverage report -m; rm .coverage'


def run(case,envs=run_envs):
    env_states = [0 == os.system(env_template % (e, case)) for e in envs]
    print(dict(zip(run_envs,env_states)))
    os.system(combine_cmd)
    return all(env_states)

@runnable
def execute_one_test(*args):
    case = ''
    # case += ' hashstore.tests.shash_tests'
    # case += ' hashstore.tests.server_tests'
    # case += ' hashstore.tests.local_store_tests'
    # case += ' hashstore.bakery.tests.backend_tests'
    # case += ' hashstore.tests.ndb_models_tests'
    # case += ' hashstore.tests.ndb_tests'
    # case += ' hashstore.tests.content_address_tests'
    case += ' hashstore.tests.ids_tests'
    case += ' hashstore.tests.utils_tests'
    case += ' hashstore.tests.cli_tests'
    # case += ' hashstore.tests.mymime_tests'
    # case += ' hashstore.tests.base_x_tests'
    # case += ' hashstore.tests.udk_tests'
    # case += ' hashstore.tests.dir_scan_tests'
    # case += ' hashstore.tests.doc_tests'
    return run(case, ['py2', 'py3'])

def execute_all_tests(*args):
    return run('')

# #@runnable
# def execute_sphinx(*args):
#     return 0 == os.system('cd docs; make')

if __name__ == '__main__':
    run('')