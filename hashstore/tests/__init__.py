#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import os
import shutil
import subprocess
from nose.tools import eq_,ok_
import sys, re
from doctest import OutputChecker, DocTestRunner, DocTestFinder

pyenv = 'py' + sys.version[0]

class TestSetup:
    def __init__(self, name, ensure_empty = False):
        self.log = logging.getLogger(name)
        test_out = os.path.abspath("test-out")
        self.dir = os.path.join(test_out, pyenv, name)
        self.home = os.path.join(test_out, pyenv, 'home')
        if ensure_empty:
            ensure_no_dir(self.dir)
            ensure_dir(self.dir)
            ensure_dir(self.home)
        self.processes = {}
        self.counter = 0

    def run_shash_and_wait(self, cmd, log_file=None, expect_rc=None):
        p_id = self.run_shash(cmd,log_file)
        popen, cmd, logpath = self.processes[p_id]
        rc = popen.wait()
        read = open(logpath).read()
        split = read.strip().split()
        if expect_rc is not None:
            if expect_rc != rc:
                print(read)
                eq_(expect_rc, rc)
        return rc, split[-1] if len(split) else None

    def run_shash(self, cmd, log_file=None):
        p_id = self.counter
        self.counter += 1
        executable = 'hashstore.shash'
        if 'd ' == cmd[:2]:
            cmd = cmd[2:]
            executable = 'hashstore.shashd'
        if log_file is None:
            cmd_name = cmd.split()[0]
            log_file = '{cmd_name}{p_id:03d}.log'.format(**locals())
        if os.path.isabs(log_file):
            path = log_file
        else:
            path = self.file_path(log_file)
        popen = run_bg(executable, cmd.split(), self.home, path)
        self.processes[p_id] = (popen, cmd ,path)
        return p_id

    def reset_all_process(self):
        self.processes = {}

    def wait_bg(self, print_all_logs=True):
        for p_id in self.processes:
            p, cmd, logpath = self.processes[p_id]
            rc = p.wait()
            logtext = open(logpath).read()
            if print_all_logs:
                print('{cmd}\nrc:{rc}\n{logtext}\n'.format(**locals()))

    def file_path(self, file):
        return os.path.join(self.dir, file)


def makedir(dir, path, abs_path):
    if not os.path.isdir(abs_path):
        os.makedirs(abs_path)


def make_recursive_link(dir, path, abs_path):
    try:
        os.symlink(os.path.dirname(abs_path),abs_path)
    except:
        os.system('ls -l %s' % os.path.dirname(abs_path))

import numpy.random as np_rnd
import time
import array

random_bytes = lambda l: array.array('B', np_rnd.randint(0, 255,l)).tostring()

reseed_random = lambda : int(time.clock() * 1000)


def seed(a):
    np_rnd.seed(a)

def random_content_fn(sz, reset_random):
    def _(dir, path, abs_path):
        if reset_random is not None:
            seed(reset_random)
        b = random_bytes(sz)
        open(abs_path,'wb').write(b)
    return _

def move(src):
    def _(dir, path,abs_path):
        shutil.move(os.path.join(dir,src),abs_path)
    return _

def delete(dir, path, abs_path):
    os.remove(abs_path)


def random_small_caps(l):
    '''
    produce string of random small caps letters

    >>> seed(0)
    >>> random_small_caps(5)
    'mpvad'

    :param l: length
    :return:
    '''
    return ''.join(map(chr, 97 + np_rnd.randint(0, 25, l)))


def text_fn(content):
    def do_text_fn(dir, path, abs_path):
        open(abs_path,'w').write(content)
    return do_text_fn


file_set1 = (
    ('a/b/c', makedir ),
    ('a/1', random_content_fn(300, 0) ),
    ('a/b/2', random_content_fn(555, None)),
    ('a/b/3', random_content_fn(555, None)),
    ('x/y/1', random_content_fn(555, None)),
    ('x/y/2', random_content_fn(555, None)),
    ('too.sol', random_content_fn(105000, None)),
    ('q/x/y/2.b', random_content_fn(555, None)),
    ('x/1', random_content_fn(555, 5)),
    ('q/x/палка_в/колесе.bin', random_content_fn(10000, None)),
    # all this get ignored
    ('q/x/y/1.sol', random_content_fn(105000, reseed_random())),
    ('q/p/2', random_content_fn(555, None)),
    ('q/z/2', random_content_fn(555, None)),
    ('.svn/q/z/2', random_content_fn(555, None)),
    ('q/.ignore', text_fn("*.sol\np\nz/\n")),
    ('q/link', make_recursive_link)
)

#changes to file_set1
file_set2 = (
    ('a/tiny', random_content_fn(30, 0) ),
    ('x/22', random_content_fn(556, 5)),
    ('x/33', random_content_fn(106000, None)),
    ('x/y/3', move('x/y/2')),
    ('x/1', delete),
)

def prep_mount(dir, file_set, keep_shamo=False):
    ensure_no_dir(dir)
    update_mount(dir, file_set)


def update_mount(dir, file_set):
    for path, fn in file_set:
        abs_path = os.path.join(dir, path)
        d = os.path.dirname(abs_path)
        ensure_dir(d)
        fn(dir, path, abs_path)


fileset1_udk = 'X7cb3ecebc582de3d18c6d12fb6109402718cf11ad06cb4ec4c1d7be23998f60f'
fileset2_udk = 'Xf4eec87b810074535c8be8624ebb72129446c7936f10e62643f2e16e6fe081f7'

def ensure_dir(d):
    if not os.path.isdir(d):
        os.makedirs(d)


def ensure_no_dir(dir):
    if os.path.isdir(dir):
        shutil.rmtree(dir)
        for _ in range(30):
            time.sleep(.01)
            if os.path.isdir(dir):
                shutil.rmtree(dir)
            else:
                break


def run_bg(module,  args=[], home=None, outfile=None):
    from subprocess import STDOUT
    env = None
    if home is not None:
        env = os.environ
        env['HOME'] = home
    command = ['coverage', 'run', '-p', '-m']
    command.append(module)
    for arg in args:
        command.append(arg)
    fp = open(outfile, 'w') if outfile is not None else None
    return subprocess.Popen(command, env=env, stdout=fp, stderr=STDOUT)


class Py23DocChecker(OutputChecker):
    def check_output(self, want, got, optionflags):
        if sys.version_info[0] < 3:
            want = re.sub("b'(.*?)'", "'\\1'", want)
        return OutputChecker.check_output(self, want, got, optionflags)

def doctest_it(m):
    name = m.__name__
    # Find, parse, and run all tests in the given module.
    finder = DocTestFinder(exclude_empty=False)
    runner = DocTestRunner(verbose=None, optionflags=0,
                           checker=Py23DocChecker())
    for test in finder.find(m, name, globs=None, extraglobs=None):
        runner.run(test)
    runner.summarize()
    ok_(runner.tries > 0, 'There is not doctests in module')
    eq_(runner.failures, 0)
