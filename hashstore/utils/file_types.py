import mimetypes
from typing import List
from os.path import join, dirname
from hashstore.utils import load_json_file
from hashstore.utils.smattr import SmAttr


class FileType(SmAttr):
    mime:str
    ext:List[str]


def read_file_types(json_file):
    load_json = load_json_file(json_file)
    return {n: FileType(v) for n,v in load_json.items()}


file_types = read_file_types(join(dirname(__file__), 'file_types.json'))

my_mime_dict = dict(
    (ext,ft.mime)
    for ft in file_types.values()
        for ext in ft.ext)

my_name_dict = dict(
    (ext,k)
    for k, ft in file_types.items()
        for ext in ft.ext )

WDF = 'WDF'
HSB = 'HSB'


def guess_name(filename):
    '''

    >>> guess_name('abc.txt')
    'TXT'
    >>> guess_name('abc.log')
    'LOG'
    >>> guess_name('abc.wdf')
    'WDF'
    >>> guess_name('abc.hsb')
    'HSB'
    >>> guess_name('.wdf')
    'BINARY'
    >>> guess_name('abc.html')
    'HTML'
    >>> guess_name('abc.bmp')
    'BINARY'

    :param filename: file path
    :return: name from `file_types`
    '''
    try:
        extension = extract_extension(filename)
        if extension:
            return my_name_dict[extension]
    except:
        pass
    return 'BINARY'


def guess_type(filename):
    '''
    guess MIME type

    >>> guess_type('abc.txt')
    'text/plain'
    >>> guess_type('abc.log')
    'text/plain'
    >>> guess_type('abc.wdf')
    'text/wdf'
    >>> guess_type('abc.hsb')
    'text/hsb'
    >>> guess_type('.wdf')
    >>> guess_type('abc.html')
    'text/html'
    >>> guess_type('abc.bmp') in ('image/x-ms-bmp', 'image/bmp')
    True

    :param filename: file path
    :return: mime type
    '''
    try:
        extension = extract_extension(filename)
        if extension:
            return my_mime_dict[extension]
    except:
        pass
    return mimetypes.guess_type(filename)[0]


def extract_extension(filename):
    '''

    >>> extract_extension('.txt')
    >>> extract_extension(None)
    >>> extract_extension('abc.txt')
    'txt'
    >>> extract_extension('a.html')
    'html'

    :param filename: file path
    :return: extension
    '''
    try:
        dot_p = filename.rindex('.')
        if dot_p > 0:
            return filename[dot_p+1:]
    except:
        pass
    return None

