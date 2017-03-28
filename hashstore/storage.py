import hashstore.local_store as localstore
import hashstore.udk as udk
import requests
import json
import six
from hashstore.utils import json_encoder
import logging
log = logging.getLogger(__name__)

methods_to_implement = ['store_directories', 'write_content', 'get_content']

class LocalStorage:
    def __init__(self, path_resolver, type, path):
        self.store = localstore.HashStore(path_resolver(path))

    def __getattr__(self, name):
        if name in methods_to_implement:
            return getattr(self.store, name)
        else:
            raise AttributeError('%s.%s is not delegated ' %
                                 (self.__class__.__name__, name) )


class RemoteStorage:
    def __init__(self, path_resolver, type, path):
        self.url = path_resolver(path)

    def store_directories(self,directories):
        data = json_encoder.encode({ str(k): v for k,v in six.iteritems(directories) } )
        url_store_directories = self.url + '.hashery/store_directories'
        r = requests.post(url_store_directories, data=data)
        text = r.text
        log.info(text)
        return json.loads(text)

    def write_content(self,fp):
        r = requests.post(self.url+'.hashery/write_content', data=fp)
        text = r.text
        log.info(text)
        return udk.UDK.ensure_it(json.loads(r.text))

    def get_content(self,k):
        if k.has_data():
            return six.BytesIO(k.data())
        url = self.url + '.hashery/' + str(k.strip_bundle())
        return requests.get(url, stream=True).raw



def factory(path_resolver, config_dict):
    '''

    :param path_resolver:
    :param config_dict:
    :return: destination instance
    '''
    constructor = globals()[config_dict['type'] + 'Storage']
    return constructor(path_resolver, **config_dict)
