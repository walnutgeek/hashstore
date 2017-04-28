import logging
import os
import shutil
import subprocess


class TestSetup:
    def __init__(self, name, ensure_empty = False):
        self.log = logging.getLogger(name)
        self.dir = os.path.join(os.path.abspath("test-out"), name)
        if ensure_empty:
            ensure_no_dir(self.dir)
            ensure_dir(self.dir)
        self.processes = {}
        self.counter = 0

    def run_shash_and_wait(self, cmd, log_file = None):
        p_id = self.run_shash(cmd,log_file)
        popen, cmd, logpath = self.processes[p_id]
        rc = popen.wait()
        return rc, open(logpath).read().strip().split()[-1]

    def run_shash(self, cmd, log_file = None):
        p_id = self.counter
        self.counter += 1
        if log_file is None:
            cmd_name = cmd.split()[0]
            log_file = '{cmd_name}{p_id:03d}.log'.format(**locals())
        if os.path.isabs(log_file):
            path = log_file
        else:
            path = self.full_log_path(log_file)
        popen = run_bg('hashstore.shash', cmd.split(), path)
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

    def full_log_path(self, log_file):
        return os.path.join(self.dir, log_file)


def makedir(path, abs_path):
    os.makedirs(abs_path)

def make_recursive_link(path, abs_path):
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

def random_content_fn(sz,reset_random):
    def do_content(path,abs_path):
        if reset_random is not None:
            seed(reset_random)
        open(abs_path,'wb').write(random_bytes(sz))
    return do_content


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
    def do_content(path,abs_path):
        open(abs_path,'w').write(content)
    return do_content


file_set1 = (
    ('a/b/c', makedir ),
    ('a/1', random_content_fn(300, 0) ),
    ('a/b/2', random_content_fn(555, None)),
    ('a/b/3', random_content_fn(555, None)),
    ('x/y/1', random_content_fn(555, None)),
    ('x/y/2', random_content_fn(555, None)),
    ('too.sol', random_content_fn(105000, None)),
    ('q/x/y/2.b', random_content_fn(555, None)),
    ('x/y/2', random_content_fn(555, None)),
    ('x/1', random_content_fn(555, None)),
    ('q/x/y/1.sol', random_content_fn(105000, reseed_random())),
    ('q/p/2', random_content_fn(555, None)),
    ('q/z/2', random_content_fn(555, None)),
    ('.svn/q/z/2', random_content_fn(555, None)),
    ('q/.ignore', text_fn("*.sol\np\nz/\n")),
    ('q/link', make_recursive_link)
)

file_set2 = (
    ('a/b/c', makedir ),
    ('a/tiny', random_content_fn(30, 0) ),
    ('a/1', random_content_fn(300, 0) ),
    ('a/b/2', random_content_fn(555, None)),
    ('a/b/3', random_content_fn(555, None)),
    ('x/y/1', random_content_fn(555, None)),
    ('x/y/2', random_content_fn(555, None)),
    ('too.sol', random_content_fn(105000, None)),
    ('q/x/y/2.b', random_content_fn(555, None)),
    ('x/y/3', random_content_fn(555, None)),
    ('x/22', random_content_fn(556, None)),
    ('x/33', random_content_fn(106000, None)),
    ('q/x/y/1.sol', random_content_fn(105000, reseed_random())),
    ('q/p/2', random_content_fn(555, None)),
    ('q/z/2', random_content_fn(555, None)),
    ('.svn/q/z/2', random_content_fn(555, None)),
    ('q/.ignore', text_fn("*.sol\np\nz/\n")),
    ('q/link', make_recursive_link)
)


def prep_mount(dir, file_set, keep_shamo=False):
    shamo_file = os.path.join(dir,'.shamo')

    shamo_content = None
    if os.path.exists(shamo_file) and keep_shamo:
        with open(shamo_file,'rb') as f:
            shamo_content = f.read()

    ensure_no_dir(dir)

    if shamo_content:
        ensure_dir(dir)
        with open(shamo_file, 'wb') as f:
            f.write(shamo_content)

    for path,fn in file_set:
        abs_path = os.path.join(dir, path)
        d = os.path.dirname(abs_path)
        ensure_dir(d)
        fn(path,abs_path)

fileset1_udk = 'X43bc953618b4d3d627fce6a0cb348e3ca48276783e6d9716fb7ca08c3901255c'
fileset2_udk = 'X6daf310cc565d3741521b8858cb6694039fd6825d1277de0271da0adcef467f8'

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


def run_bg(module, args=[], outfile=None):
    command = ['coverage', 'run', '-p', '-m']
    command.append(module)
    for arg in args:
        command.append(arg)
    f = open(outfile, 'w') if outfile is not None else None
    return subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT)


