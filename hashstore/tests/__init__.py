import logging
import os
import shutil
import six
import subprocess


def zzzetup(n,ensure_enpty = False):
    test_dir = os.path.join(os.path.abspath("test-out"), n)
    if ensure_enpty:
        ensure_no_dir(test_dir)
        ensure_dir(test_dir)
    return logging.getLogger(n), test_dir

def makedir(path, abs_path):
    os.makedirs(abs_path)

def make_recursive_link(path, abs_path):
    try:
        os.symlink(os.path.dirname(abs_path),abs_path)
    except:
        os.system('ls -l %s' % os.path.dirname(abs_path))

import random
import time

random_bytes = lambda l: six.binary_type().join(
    six.int2byte(random.randint(0, 255)) for _ in range(l))
reseed_random = lambda : int(time.clock() * 1000)

def random_content_fn(sz,reset_random):
    def do_content(path,abs_path):
        if reset_random is not None:
            random.seed(reset_random)
        open(abs_path,'w').write(random_bytes(sz))
    return do_content

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

def prep_mount(dir,file_set):
    ensure_no_dir(dir)
    for path,fn in file_set:
        abs_path = os.path.join(dir, path)
        d = os.path.dirname(abs_path)
        ensure_dir(d)
        fn(path,abs_path)


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



def run_bg(module, args = [], outfile = None):
    command = ['coverage', 'run', '-p', '-m']
    command.append(module)
    for arg in args:
        command.append(arg)
    f = open(outfile, 'w') if outfile is not None else None
    return subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT)


