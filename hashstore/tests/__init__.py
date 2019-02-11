#!/usr/bin/python
# -*- coding: utf-8 -*-
from logging import getLogger
import os
import shutil
import subprocess
import sys
from hashstore.kernel.misc.nose import doctest_it,assert_text,eq_,ok_
import random
import time


pyenv = 'py%d' % sys.version_info.minor


class TestSetup:
    def __init__(self, name, log_name=None, root=None,
                 ensure_empty=False, script_mode=False):
        self.script_mode=script_mode
        self.log = getLogger(name if log_name is None else log_name)
        if root is None:
            root = os.path.abspath("test-out")
        self.dir = os.path.join(root, pyenv, name)
        self.home = os.path.join(self.dir, 'home')
        if ensure_empty:
            self.ensure_empty()
        self.processes = {}
        self.counter = 0

    def ensure_empty(self):
        ensure_no_dir(self.dir)
        ensure_dir(self.dir)
        ensure_dir(self.home)

    def run_script_and_wait(self, cmd, log_file=None, expect_rc=None,
                            expect_read = None, save_words=None):
        p_id = self.run_script_in_bg(cmd, log_file)
        rc, logtext = self.wait_process(p_id,expect_read=expect_read,
                                        expect_rc=expect_rc,
                                        save_words=save_words)
        split = logtext.strip().split()
        last_value = split[-1] if len(split) else None
        return rc, (last_value if save_words is None else save_words)

    def run_script_in_bg(self, cmd, log_file=None):
        p_id = self.counter
        self.counter += 1
        if log_file is None:
            cmd_name = next(n for n in (cmd+' log').split()
                            if not('-' in n or '/' in n or '.' in n))
            log_file = '{cmd_name}{p_id:03d}.log'.format(**locals())
        if os.path.isabs(log_file):
            path = log_file
        else:
            path = self.file_path(log_file)
        popen = run_bg(cmd.split(), self.home, path,
                       script_mode=self.script_mode)
        self.processes[p_id] = (popen, cmd ,path)
        return p_id

    def reset_all_process(self):
        self.processes = {}

    def wait_all(self, print_all_logs=True):
        for p_id in self.processes:
            self.wait_process(p_id, print_all_logs)

    def wait_process(self, p_id, print_all_logs=False,
                     expect_rc=None, expect_read=None,
                     save_words=None):
        p, cmd, logpath = self.processes[p_id]
        # print('waiting on :{cmd}\npid={p_id}\nlog={logpath}\n'.format(**locals()))
        rc = p.wait()
        logtext = open(logpath).read()
        if expect_rc is not None:
            if not isinstance(expect_rc,list):
                expect_rc = [expect_rc]
            ok_(rc in expect_rc, logtext)
        if expect_read is not None:
            assert_text(logtext, expect_read, save_words=save_words)
        if print_all_logs:
            print('{cmd}\nrc:{rc}\n{logtext}\n'.format(**locals()))
        return rc, logtext

    def file_path(self, file):
        return os.path.join(self.dir, file)


def makedir(dir, path, abs_path):
    if not os.path.isdir(abs_path):
        os.makedirs(abs_path)


def make_recursive_link(dir, path, abs_path):
    try:
        os.symlink(os.path.dirname(abs_path),abs_path)
    except:
        pass
        #os.system('ls -l %s' % os.path.dirname(abs_path))


def randint_repeat(start, end, repeat):
    return (random.randint(start, end) for _ in range(repeat))


def random_bytes(l):
    return bytes(randint_repeat(0,255,l))


def reseed_random():
    return int(time.clock() * 1000)


def seed(a):
    random.seed(a, version=2)

seed(0)


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
    'mynbi'

    :param l: length
    :return:
    '''
    return ''.join(map(chr, randint_repeat(97, 122, l)))


def text_fn(content):
    def do_text_fn(dir, path, abs_path):
        open(abs_path,'wb').write(content)
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
    ('q/.ignore', text_fn(b"*.sol\np\nz/\n")),
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
fileset1_cake = '379d7vSiMyDQdNF4aTI9leckwVafthEoGK4ioSAR8Qws' #'hozMa8oJozEdgOSKXayFcrEwuGaGfW2rxBUeS6MKEdaK'
fileset2_cake = '3evUZ7xNg2E3qvndSLZu8EfIuGK9KoljwwlJbl6mKClH'#'hAHMGpM0Etn1TGntqB434ckKJzQKUxwLDvfnjz9feiqk'


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


def run_bg(args=[], home=None, outfile=None, script_mode = False):
    from subprocess import STDOUT
    env = None
    if home is not None:
        env = os.environ
        env['HOME'] = home
    command = ['hs'] if script_mode else [ 'python', '-m'
        'coverage', 'run', '-p', '-m', 'hashstore.hs']
    for arg in args:
        if arg is not None and arg.strip() != '':
            command.append(arg)
    
    fp = None
    if outfile is not None and os.path.isdir(os.path.dirname(outfile)):
        fp = open(outfile, 'w')
    return subprocess.Popen(command, env=env, stdout=fp, stderr=STDOUT)


def sqlite_q(path, select, *params):
    import sqlite3
    with sqlite3.connect(path) as conn:
        return list(conn.execute(select,params))


if __name__ == '__main__':
    import sys
    doctest_it(sys.modules[__name__])