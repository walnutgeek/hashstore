"""
File Input Output Utils
"""
from typing import Optional,Union
from pathlib import Path

import os


def ensure_path(path:Union[str,Path])->Path:
    if isinstance(path, Path):
        return path
    return Path(path)


def ensure_directory(directory: str)->bool:
    """
    Ensure that directory exists.

    :param directory:
    :return: True if directory was created
    """
    if not (os.path.isdir(directory)):
        os.makedirs(directory)
        return True
    return False



class ConfigDir:
    """
    search for config directory in parent directories
    (simular pattern like .git directory)
    """
    def __init__(self, path:str, dir_name:Optional[str]=None)->None:
        self.path = path
        if dir_name is None:
            dir_name = type(self).__dir_name__ #type:ignore
        self.dir_name = dir_name

    def dir_path(self)->str:
        return os.path.join(self.path, self.dir_name)

    def exists(self)->bool:
        return os.path.isdir(self.dir_path())

    def build(self)->None:
        """
        Build necessary files in config directory.
        """
        pass

    def ensure(self):
        if ensure_directory(self.dir_path()):
            self.build()


    @classmethod
    def lookup_up(cls: type,
                  path: Union[str,Path],
                  dir_name: Optional[str]=None
                  ) -> Optional['ConfigDir']:
        """
        Lookup for `dir_name` up directory tree
        """
        if dir_name is None:
            dir_name = cls.__dir_name__ #type:ignore
        path = ensure_path(path)
        for p in (path, *path.parents):
            config_dir = cls(p, dir_name)
            if config_dir.exists():
                return config_dir
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



