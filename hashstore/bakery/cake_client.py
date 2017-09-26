import os
import requests
import json
from sqlalchemy import desc
from hashstore.bakery import RemoteError
from hashstore.bakery.ids import Cake, SaltedSha
from hashstore.ndb import Dbf
from hashstore.ndb.models.client_config import ClientConfigBase, \
    ClientKey, Server, MountSession
from hashstore.utils import json_encoder, normalize_url, \
    is_file_in_directory
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
        abspath = os.path.abspath(dir)
        with self.client_config_session() as session:
            for mount_session in session.query(MountSession)\
                    .order_by(desc(MountSession.path)).all():
                if is_file_in_directory(abspath, mount_session.path):
                    server = session.query(Server)\
                        .filter(Server.id == mount_session.server_id)\
                        .one()
                    return ClientUserSession(self, server.server_url,
                                             mount_session.id)


    def logout(self):
        pass


class ClientUserSession:
    def __init__(self, client, url, session_id=None):
        self.url = normalize_url(url)
        resp = requests.get(self.url+'.server_id')
        self.server_id, self.server_secret = (
            t.ensure_it(s) for t,s in
            zip((Cake, SaltedSha), json.loads(resp.text)) )
        self.client = client
        self.session_id = session_id
        self.client_id = self.client.get_client_id()
        self.init_headers()

        class AccessProxy:
            def __getattr__(_, item):
                def proxy_call(**kwargs):
                    resp = self.call_api({
                        'call': item,
                        'msg': kwargs})
                    if 'error' in resp:
                        raise RemoteError(resp['error'])
                    return resp['result']
                return proxy_call
        self.proxy = AccessProxy()

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
        result = self.proxy.login(email=email,
                                passwd = passwd,
                                client_id = self.client_id)
        self.email = email
        self.session_id = Cake.ensure_it(result)
        self.init_headers()

    def init_headers(self):
        self.headers = {}
        if self.session_id is not None:
            self.headers['UserSession'] = str(self.session_id)
            if self.client_id is not None:
                self.headers['ClientID'] = str(self.client_id)

    def create_mount_session(self, mount_dir):
        abspath = os.path.abspath(mount_dir)
        with self.client.client_config_session() as session:
            session.merge(Server(id=self.server_id,
                   server_url=self.url,
                   secret = self.server_secret))
            mount_session = session.query(MountSession)\
                .filter(MountSession.path == abspath).one_or_none()
            if mount_session is None:
                mount_session = MountSession(path=abspath)
                session.add(mount_session)
            mount_session.id = self.session_id
            mount_session.server_id = self.server_id
            mount_session.username = self.email
        print("Mount: "+ abspath)
        print(self.headers)


