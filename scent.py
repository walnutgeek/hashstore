import os
import sys

from sniffer.api import file_validator, runnable


@file_validator
def py_files(filename):
    return filename.endswith('.py') or filename.endswith(
        '.yaml') or filename.endswith('.rst')


run_envs = ['py6', 'py7']

mypy_modules = [
    'hashstore.bakery.tests.logic_test_module', 'hashstore.hs']

def activate_prefix(e):
    return '' if e == 'current' else f'. activate {e}; '

def run(case, envs, html=False):
    html = 'python -m coverage html;' if html else ''
    env_states = [
        0 == os.system(
            f'{activate_prefix(e)}'
            f'python -m coverage run -p -m nose {case}')
        for e in envs
    ]
    print(dict(zip(run_envs, env_states)))
    modules = ' '.join( f'-m {m}' for m in mypy_modules )
    mypy = 0 == os.system(
        f'{activate_prefix(run_envs[0])}'
        f'python -m mypy {modules} --ignore-missing-imports'
    )
    os.system(
        f'{activate_prefix(run_envs[0])}'
        f'python -m coverage combine; '
        f'python -m coverage report -m; {html} rm .coverage')
    return all(env_states) and mypy

"""
Tests to add:


"""

@runnable
def execute_some_tests(*args):
    case = ''
    case += ' hashstore.tests.utils_event_tests'
    case += ' hashstore.bakery.tests.logic_tests'
    case += ' hashstore.tests.utils_auto_wire_tests'
    case += ' hashstore.tests.smattr_tests'
    case += ' hashstore.bakery.tests.init_tests'
    case += ' hashstore.bakery.tests.cake_tree_tests'
    case += ' hashstore.bakery.lite.tests.backend_tests'
    case += ' hashstore.bakery.lite.tests.models_tests'
    case += ' hashstore.tests.db_tests'
    case += ' hashstore.tests.utils_auto_wire_tests'
    case += ' hashstore.tests.utils_fio_tests'
    case += ' hashstore.tests.utils_tests'
    case += ' hashstore.tests.utils_file_types_tests'
    case += ' hashstore.tests.base_x_tests'

    #=== slow tests
    # case += ' hashstore.tests.doc_tests'
    # case += ' hashstore.bakery.tests.cli_tests'
    # case += ' hashstore.bakery.tests.server_tests'
    return run(case, run_envs, html=True)


# #@runnable
# def execute_sphinx(*args):
#     return 0 == os.system('cd docs; make')

if __name__ == '__main__':
    envs = run_envs
    if len(sys.argv) > 1:
        envs = sys.argv[1:]
    if not(run('', envs, html=True)):
        raise SystemExit(-1)
