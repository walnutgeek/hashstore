import os

from sniffer.api import *

@file_validator
def py_files(filename):
    return filename.endswith('.py') or filename.endswith('.yaml') or filename.endswith('.rst')


run_envs = ['py3']

env_template = '. activate %s; coverage run -p -m nose %s'

combine_cmd = '. activate py3; coverage combine; coverage report -m; {html} rm .coverage'


def run(case, envs=run_envs, html=False):
    html = 'coverage html;' if html else ''
    env_states = [0 == os.system(env_template % (e, case)) for e in envs]
    print(dict(zip(run_envs,env_states)))
    os.system(combine_cmd.format(**locals()))
    return all(env_states)

@runnable
def execute_one_test(*args):
    case = ''
    # case += ' hashstore.bakery.tests.cli_tests'
    case += ' hashstore.bakery.tests.init_tests'
    # case += ' hashstore.bakery.tests.logic_tests'
    # case += ' hashstore.bakery.tests.cake_tree_tests'
    case += ' hashstore.bakery.tests.server_tests'
    # case += ' hashstore.bakery.tests.backend_tests'
    # case += ' hashstore.tests.ndb_models_tests'
    # case += ' hashstore.tests.ndb_tests'
    # case += ' hashstore.tests.utils_tests'
    # case += ' hashstore.tests.utils_file_types_tests'
    # case += ' hashstore.tests.utils.base_x_tests'
    # case += ' hashstore.tests.doc_tests'
    return run(case, [ 'py3'], html=True)


# #@runnable
# def execute_sphinx(*args):
#     return 0 == os.system('cd docs; make')

if __name__ == '__main__':
    run('', html=True)