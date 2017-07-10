import hashstore.udk as udk
import requests
import json
import six
from hashstore.utils import json_encoder
from hashstore.udk import quick_hash
import logging
log = logging.getLogger(__name__)


class RemoteStorage:
    def __init__(self, url):
        self.url = url
        self.headers = {}
        self.logged_in = False

    def register(self, mount_uuid, invitation=None, meta=None):
        response = self.post_meta_data('register',
                                   {'mount_uuid': mount_uuid,
                                    'invitation': invitation,
                                    'meta': meta})
        return json.loads(response)

    def login(self,mount_uuid,server_hash):
        response = self.post_meta_data('login', {'mount_uuid': mount_uuid})
        resp = json.loads(response)

        if server_hash != quick_hash(resp['server_uuid']):
            raise AssertionError('cannot validate server')
        self.headers['auth_session'] = str(resp['auth_session'])
        self.logged_in = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.logged_in:
            self.logout()

    def __enter__(self):
        return self

    def logout(self):
        return self.post_meta_data('logout', {})

    def store_directories(self,directories,mount_hash=None,auth_session=None):
        req = {
            'directories': {str(k): v for k,v in six.iteritems(directories)},
            'root': mount_hash
        }
        text = self.post_meta_data('store_directories', req)
        return json.loads(text)

    def post_meta_data(self, data_ptr, data):
        meta_url = self.url + '.up/post/' + data_ptr
        in_data = json_encoder.encode(data)
        r = requests.post(meta_url, headers=self.headers, data=in_data)
        out_data = r.text
        log.debug('{{ "url": "{meta_url}",\n'
                  'in: {in_data},\n'
                  'out: {out_data} }}'.format(**locals()))
        return out_data

    def write_content(self,fp):
        r = requests.post(self.url+'.up/stream', headers=self.headers, data=fp)
        return udk.UDK.ensure_it(json.loads(r.text))

    def get_content(self,k):
        if k.has_data():
            return six.BytesIO(k.data())
        url = self.url + '.raw/' + str(k.strip_bundle())
        return requests.get(url, headers=self.headers, stream=True).raw

