import mimetypes

MIME_HS_BUNDLE = 'application/hashstore+bundle'
MIME_WDF = 'text/wdf'

my_mimetypes = [
        (['.hs_bundle','.hsb'],    MIME_HS_BUNDLE),
        (['.wdf'],                 MIME_WDF),
]

my_mime_dict = {k: v[1] for v in my_mimetypes for k in v[0]}


def guess_type(filename):
    '''

    >>> guess_type('abc.txt')
    'text/plain'
    >>> guess_type('abc.wdf')
    'text/wdf'
    >>> guess_type('abc.hs_bundle')
    'application/hashstore+bundle'
    >>> guess_type('abc.hsb')
    'application/hashstore+bundle'
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
    '.txt'
    >>> extract_extension('a.html')
    '.html'

    :param filename: file path
    :return: extension
    '''
    try:
        dot_p = filename.rindex('.')
        if dot_p > 0:
            return filename[dot_p:]
    except:
        pass
    return None
