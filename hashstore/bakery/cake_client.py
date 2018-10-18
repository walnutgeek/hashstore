import os
import requests
import json
from sqlalchemy import desc
from hashstore.bakery import RemoteError, Cake, Content
from hashstore.bakery.lite.node import ContentAddress
from hashstore.utils.file_types import BINARY_MIME
from hashstore.utils.fio import is_file_in_directory
from hashstore.utils.hashing import SaltedSha
from hashstore.utils.db import Dbf
from hashstore.bakery.lite.client import ClientConfigBase, \
    ClientKey, Server, MountSession
from hashstore.utils import (
    json_encoder, normalize_url, json_decode)
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
            def client_session(mount_session):
                server = session.query(Server) \
                    .filter(Server.id == mount_session.server_id) \
                    .one()
                return ClientUserSession(self, server.server_url,
                                         mount_session.id)
            default_mount = None
            for mount_session in session.query(MountSession)\
                    .order_by(desc(MountSession.path)).all():
                if is_file_in_directory(abspath, mount_session.path):
                    return client_session(mount_session)
                if mount_session.default:
                    default_mount = mount_session
            if default_mount is not None:
                return client_session(mount_session)



    def logout(self):
        pass


class ClientUserSession:
    def __init__(self, client, url, session_id=None):
        self.url = normalize_url(url)
        resp = requests.get(self.url+'-/server_id')
        self.server_id, self.server_secret = (
            t.ensure_it(s) for t,s in
            zip((Cake, SaltedSha), json.loads(resp.text)) )
        self.client = client
        self.session_id = session_id
        self.client_id = self.client.get_client_id()
        self.init_headers()

        class AccessProxy:
            def write_content(_, fp):
                r = requests.post(self.url + '-/api/up',
                                  headers=self.headers, data=fp)
                log.debug('text: {r.text}'.format(**locals()))
                return ContentAddress.ensure_it(json_decode(r.text))

            def get_content(_, cake_or_path, skinny=True):
                if isinstance(cake_or_path, Cake):
                    if cake_or_path.has_data():
                        return Content.from_data_and_role(
                            data=cake_or_path.data(),
                            role=cake_or_path.header.role
                        )
                if skinny:
                    info = {'mime': BINARY_MIME }
                else:
                    resp = self.get_response('-/get/info', cake_or_path)
                    info = json_decode(resp.text)
                return Content(
                    stream_fn=(lambda:self.get_stream(cake_or_path)),
                    **info)

            def __getattr__(_, item):
                def proxy_call(**kwargs):
                    resp = self.post_json({
                        'call': item,
                        'msg': kwargs})
                    if 'error' in resp:
                        raise RemoteError(resp['error'])
                    return resp['result']
                return proxy_call
        self.proxy = AccessProxy()

    def post_json(self, data, endpoint='-/api/post'):
        meta_url = self.url + endpoint
        in_data = json_encoder.encode(data)
        r = requests.post(meta_url, headers=self.headers, data=in_data)
        out_data = r.text
        log.debug('{{ "url": "{meta_url}",\n'
                  '"in": {in_data},\n'
                  '"out": {out_data} }}'.format(**locals()))
        return json_decode(out_data)

    def get_response(self, endpoint , cake_or_path, do_stream=False):
        if isinstance(cake_or_path, Cake):
            endpoint += '/'
        meta_url = self.url + endpoint + str(cake_or_path)
        return requests.get(meta_url, headers=self.headers,
                            stream=do_stream)

    def get_stream(self, cake_or_path):
        return self.get_response('-/get/data', cake_or_path,
                                 do_stream=True).raw

    def login(self, email, passwd):
        result = self.proxy.login(email=email,
                                  passwd=passwd,
                                  client_id=self.client_id)
        self.email = email
        self.session_id = Cake.ensure_it(result)
        self.init_headers()

    def init_headers(self):
        self.headers = {}
        if self.session_id is not None:
            self.headers['UserSession'] = str(self.session_id)
            if self.client_id is not None:
                self.headers['ClientID'] = str(self.client_id)

    def create_mount_session(self, mount_dir, default=False):
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
            mount_session.default = default
            if default:
                session.query(MountSession)\
                    .filter(MountSession.id != self.session_id,
                            MountSession.default == True )\
                    .update({MountSession.default: False})

        def print_header(n):
            print(n+': '+self.headers.get(n))
        print("Mount: "+ abspath)
        print_header('ClientID')
        print_header('UserSession')


