'''
Code that give compilation error in py3, so it
moved to separeate file and not even invoked
'''
def _raise_it(etype, new_exception, traceback):
    raise etype, new_exception, traceback
