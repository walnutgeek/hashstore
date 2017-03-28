import os
from sniffer.api import *
import nose

@file_validator
def py_files(filename):
    return filename.endswith('.py') or filename.endswith('.yaml') or filename.endswith('.rst')

run_template = 'coverage run -p -m nose %s; RC=$?; ' \
               'coverage combine; coverage report -m; rm .coverage; ' \
               'exit $RC'

def execute_test(*args):
    case = 'hashstore.tests.shash_tests'
    # case = 'hashstore.tests.hashstore_tests'
    # case = 'hashstore.tests.udk_tests'
    return 0 == os.system(run_template % case)

@runnable
def execute_coverage(*args):
    return 0 == os.system( run_template % '')

# #@runnable
# def execute_sphinx(*args):
#     return 0 == os.system('cd docs; make')
