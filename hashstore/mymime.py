import mimetypes

MIME_UDK_BUNDLE = 'application/shash+udk_bundle'
MIME_HTML_FRAGMENT = 'application/shash+html'
MIME_WDF = 'text/wdf'

my_mimetypes = [
        (['.udk_bundle'],    MIME_UDK_BUNDLE),
        (['.html_fragment'], MIME_HTML_FRAGMENT),
        (['.wdf'],           MIME_WDF),
]

my_mime_dict = {k: v[1] for v in my_mimetypes for k in v[0]}


def guess_type(filename):
    '''

    >>> guess_type('abc.txt')
    'text/plain'
    >>> guess_type('abc.wdf')
    'text/wdf'
    >>> guess_type('abc.html_fragment')
    'application/shash+html'
    >>> guess_type('abc.udk_bundle')
    'application/shash+udk_bundle'
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
