"""
File Input Output Utils
"""
from typing import Optional

import os

def ensure_directory(directory: str)->None:
    if not (os.path.isdir(directory)):
        os.makedirs(directory)


class ConfigDir:
    def __init__(self, path:str, dir_name:str)->None:
        self.path = path
        self.dir_name = dir_name

    def dir_path(self)->str:
        return os.path.join(self.path, self.dir_name)

    def exists(self)->bool:
        return os.path.isdir(self.dir_path())

    def build(self)->None:
        """
        build necessary files in config directory
        """
        pass

    def ensure(self):
        ensure_directory(self.dir_path())


    @classmethod
    def lookup_up(cls:type, path:str, dir_name:str
                  ) -> Optional['ConfigDir']:
        """
        Lookup for `dir_name` up directory tree
        """
        while True:
            config_dir = cls(path, dir_name)
            if config_dir.exists():
                return config_dir
            if path != '/':
                head, tail = os.path.split(path)
                if head != '':
                    path = head
                    continue
            return None


def read_in_chunks(fp, chunk_size=65535):
    while True:
        data = fp.read(chunk_size)
        if not data:
            break
        yield data


def is_file_in_directory(file, dir):
    '''
    >>> is_file_in_directory('/a/b/c.txt', '/a')
    True
    >>> is_file_in_directory('/a/b/c.txt', '/a/')
    True
    >>> is_file_in_directory('/a/b/', '/a/b/')
    True
    >>> is_file_in_directory('/a/b/', '/a/b')
    True
    >>> is_file_in_directory('/a/b', '/a/b/')
    True
    >>> is_file_in_directory('/a/b', '/a/b')
    True
    >>> is_file_in_directory('/a/b', '/a//b')
    True
    >>> is_file_in_directory('/a//b', '/a/b')
    True
    >>> is_file_in_directory('/a/b/c.txt', '/')
    True
    >>> is_file_in_directory('/a/b/c.txt', '/aa')
    False
    >>> is_file_in_directory('/a/b/c.txt', '/b')
    False
    '''
    realdir = os.path.realpath(dir)
    dir = os.path.join(realdir, '')
    file = os.path.realpath(file)
    return file == realdir or os.path.commonprefix([file, dir]) == dir


def path_split_all(path: str, ensure_trailing_slash: bool = None):
    '''
    >>> path_split_all('/a/b/c')
    ['/', 'a', 'b', 'c']
    >>> path_split_all('/a/b/c/' )
    ['/', 'a', 'b', 'c', '']
    >>> path_split_all('/a/b/c', ensure_trailing_slash=True)
    ['/', 'a', 'b', 'c', '']
    >>> path_split_all('/a/b/c/', ensure_trailing_slash=True)
    ['/', 'a', 'b', 'c', '']
    >>> path_split_all('/a/b/c/', ensure_trailing_slash=False)
    ['/', 'a', 'b', 'c']
    >>> path_split_all('/a/b/c', ensure_trailing_slash=False)
    ['/', 'a', 'b', 'c']
    '''
    def tails(head):
        while(True):
            head,tail = os.path.split(head)
            if head == '/' and tail == '':
                yield head
                break
            yield tail
            if head == '':
                break
    parts = list(tails(path))
    parts.reverse()
    if ensure_trailing_slash is not None:
        if ensure_trailing_slash :
            if parts[-1] != '':
                parts.append('')
        else:
            if parts[-1] == '':
                parts = parts[:-1]
    return parts


class FileNotFound(Exception):
    def __init__(self, path):
        super(FileNotFound, self).__init__(path)

