import mimetypes
import attr
from six import itervalues, text_type
from os.path import join, dirname
from hashstore.utils import (
    ensure_bytes, ensure_string,
    DictKey, load_json_file,
    type_required as required,
    type_list_of as list_of,
    create_dict_converter )

@attr.s
class FileType(DictKey):
    mime=attr.ib(**required(text_type))
    ext=attr.ib(**list_of(text_type))

def read_file_types(json_file):
    local = load_json_file(json_file)
    return create_dict_converter(FileType)(local)


file_types = read_file_types(join(dirname(__file__), 'file_types.json'))

my_mime_dict = dict(
    (cvt(ext),cvt(ft.mime))
    for ft in itervalues(file_types)
        for ext in ft.ext
            for cvt in [ensure_string, ensure_bytes])

my_name_dict = dict(
    (cvt(ext),ft._key_)
    for ft in itervalues(file_types)
        for ext in ft.ext
            for cvt in [ensure_string, ensure_bytes])

WDF = 'WDF'
HSB = 'HSB'

def guess_name(filename):
    '''

    >>> guess_name('abc.txt')
    u'TXT'
    >>> guess_name('abc.log')
    u'LOG'
    >>> guess_name('abc.wdf')
    u'WDF'
    >>> guess_name('abc.hsb')
    u'HSB'
    >>> guess_name('.wdf')
    u'BINARY'
    >>> guess_name('abc.html')
    u'HTML'

    :param filename: file path
    :return: name from `file_types`
    '''
    try:
        extension = extract_extension(filename)
        if extension:
            return my_name_dict[extension]
    except:
        pass
    return u'BINARY'


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

