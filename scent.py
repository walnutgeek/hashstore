import os
import sys

add_to_path = os.path.dirname(sys.argv[0])

from sniffer.api import *
import nose

@file_validator
def py_files(filename):
    return filename.endswith('.py') or filename.endswith('.yaml') or filename.endswith('.rst')


run_template = 'PATH=%s:$PATH; ' \
               'coverage run -p -m nose %s; RC=$?; ' \
               'coverage combine; coverage report -m; rm .coverage; ' \
               'exit $RC'


def run(case):
    return 0 == os.system(run_template % (add_to_path, case))


def execute_one_test(*args):
    #case = 'hashstore.tests.shash_tests'
    #case = 'hashstore.tests.hashstore_tests'
    case = 'hashstore.tests.udk_tests'
    return run(case)


@runnable
def execute_all_tests(*args):
    return run('')

# #@runnable
# def execute_sphinx(*args):
#     return 0 == os.system('cd docs; make')
