import mimetypes
import json
from six import itervalues
from os.path import join, dirname

from hashstore.utils import ensure_bytes, ensure_unicode

file_types = json.load(open(join(dirname(__file__), 'file_types.json')))

MIME_HS_BUNDLE = MIME_HSB = file_types['HSB']["mime"]
MIME_WDF = file_types['WDF']["mime"]


my_mime_dict = {
    conversion(ext): conversion(v['mime'])
        for v in itervalues(file_types) if 'ext' in v
            for ext in v['ext']
                for conversion in [ensure_unicode, ensure_bytes]
}



def guess_type(filename):
    '''

    >>> guess_type('abc.txt')
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
