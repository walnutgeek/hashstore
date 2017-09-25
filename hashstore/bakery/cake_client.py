import os
import requests
import json

from hashstore.bakery import CredentialsError
from hashstore.bakery.ids import Cake, SaltedSha
from hashstore.ndb import Dbf
from hashstore.ndb.models.client_config import ClientConfigBase, \
    ClientKey
from hashstore.utils import json_encoder, normalize_url
import logging
log = logging.getLogger(__name__)


class CakeClient:
    def __init__(self, home_dir = None):
        if home_dir is None:
            home_dir = os.environ['HOME']
        self.config_dir = os.path.join(home_dir, '.hashstore_client')
        config = os.path.join(self.config_dir, 'config.db')
        self.clntcfg_db = Dbf(ClientConfigBase.metadata, config)

    def client_config_session(self):
        return self.clntcfg_db.session_scope()

    def initdb(self):
        os.makedirs(self.config_dir, mode=0o700)
        self.clntcfg_db.ensure_db()
        os.chmod(self.clntcfg_db.path, 0o600)
        with self.client_config_session() as session:
            session.add(ClientKey())

    def has_db(self):
        return self.clntcfg_db.exists()

    def client_key(self):
        with self.client_config_session() as session:
            return session.query(ClientKey).one()

    def get_client_id(self):
        return self.client_key().id if self.has_db() else None

    def check_mount_session(self, dir):
        pass

    def logout(self):
        pass




class ClientUserSession:
    def __init__(self, client, url):
        self.url = normalize_url(url)
        log.debug(self.url)
        resp = requests.get(self.url+'.server_id')
        self.server_id, self.secret_ssha = (
            t.ensure_it(s) for t,s in
            zip((Cake, SaltedSha), json.loads(resp.text)) )
        self.headers = {}
        self.client = client
        self.session_id = None

    def call_api(self, data):
        meta_url = self.url + '.api/post'
        in_data = json_encoder.encode(data)
        r = requests.post(meta_url, headers=self.headers, data=in_data)
        out_data = r.text
        log.debug('{{ "url": "{meta_url}",\n'
                  '"in": {in_data},\n'
                  '"out": {out_data} }}'.format(**locals()))
        return json.loads(out_data)

    def login(self, email, passwd):
        client_id = self.client.get_client_id()
        resp = self.call_api({
            'call': 'login',
            'msg': {'email': email,
                    'passwd': passwd,
                    'client_id': client_id}})
        if 'error' in resp:
            raise CredentialsError(resp['error'])
        self.session_id = Cake.ensure_it(resp['result'])
        self.headers = {}
        self.headers['UserSession'] = self.session_id
        if client_id is not None:
            self.headers['ClientID'] = client_id

    def info(self):
        print(self.headers)