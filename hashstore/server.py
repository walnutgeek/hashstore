#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import requests
import os
import time
import logging
import mimetypes
import signal
from hashstore.local_store import HashStore, AccessMode
from hashstore.udk import UDK, UDKBundle
import json
import six
from hashstore.utils import json_encoder, path_split_all

import tornado.web
import tornado.template
import tornado.ioloop
import tornado.httpserver
import tornado.gen as gen
import tornado.iostream

GIGABYTE = pow(1024, 3)

from hashstore.mount import Mount,FileNotFound

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class MountHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET']

    def initialize(self,mount):
        self.mount = mount

    def get(self, path):
        try:
            file = self.mount.file(path)
            mime,enc = file.mime_enc()
            if mime and enc:
                self.set_header('Content-Type', '{mime}; charset="{enc}"'.format(**locals()))
            elif mime:
                self.set_header('Content-Type', mime)
            content = file.render()
            if isinstance(content, six.string_types):
                self.write(content)
            else:
                while 1:
                    chunk = content.read(64*1024)
                    if not chunk:
                        break
                    self.write(chunk)
        except FileNotFound:
            raise tornado.web.HTTPError(404)
        self.finish()


def _fn_handler(content_fn):
    class _(tornado.web.RequestHandler):
        SUPPORTED_METHODS = ['GET']

        def get(self, path):
            self.write(content_fn())
            self.finish()
    return _


def _dummy_handler(content):
    return _fn_handler(lambda : content)


class HashPath:
    def __init__(self,path):
        self.path = path_split_all(path)
        if len(self.path) < 1:
            raise ValueError('no path: {}'.format(path))

    def __getitem__(self, i):
        return self.path[i]

    def __len__(self):
        return len(self.path)

    def need_to_be_resolved(self):
        return len(self) > 1

    def mime_enc(self):
        return mimetypes.guess_type(self.path[-1])

    def udk(self):
        return UDK.ensure_it(self.path[0])


@tornado.web.stream_request_body
class StreamHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['POST']

    def initialize(self,store):
        self.store = store

    def post(self):
        k = self.w.done()
        log.info('write_content: %s' % k)
        self.write(json_encoder.encode(k))
        self.finish()

    def prepare(self):
        auth_session = self.request.headers.get("Auth_session")
        self.w = self.store.writer(auth_session)

    def data_received(self, chunk):
        self.w.write(chunk)


class HashPathMixin:
    def _get_lookup(self, auth_session, hash_path):
        udk = hash_path.udk()
        is_directory = True
        if hash_path.need_to_be_resolved():
            for i in range(1, len(hash_path)):
                content = self.store.get_content( udk, auth_session=auth_session)
                bundle = UDKBundle(content)
                udk = bundle[hash_path[i]]
                is_directory = udk.named_udk_bundle
        self.udk = udk
        if self.store.access_mode == AccessMode.ALL_SECURE:
            self.store.check_auth_session(auth_session=auth_session)
        return self.store.lookup(self.udk), is_directory


class HashMountHandler(tornado.web.RequestHandler,HashPathMixin):
    SUPPORTED_METHODS = ['GET']

    def initialize(self,store):
        self.store = store

    @tornado.web.asynchronous
    @gen.coroutine
    def get(self, path):
        try:
            auth_session = self.request.headers.get("Auth_session")
            hash_path = HashPath(path)
            lookup,is_directory = self._get_lookup(auth_session, hash_path)
            if not lookup.found():
                raise tornado.web.HTTPError(404)

            file = self.mount.file(path)
            mime,enc = file.mime_enc()
            if mime and enc:
                self.set_header('Content-Type', '{mime}; charset="{enc}"'.format(**locals()))
            elif mime:
                self.set_header('Content-Type', mime)
            content = file.render()
            if isinstance(content, six.string_types):
                self.write(content)
            else:
                while 1:
                    chunk = content.read(64*1024)
                    if not chunk:
                        break
                    self.write(chunk)
        except FileNotFound:
            raise tornado.web.HTTPError(404)
        self.finish()

class HasheryHandler(tornado.web.RequestHandler,HashPathMixin):
    SUPPORTED_METHODS = ['GET','POST']

    def initialize(self,store):
        self.store = store

    def post(self, path):
        print("post: %s" % path)
        auth_session = self.request.headers.get("Auth_session")
        remote_ip = self.request.headers.get( "X-Real-IP") or \
                    self.request.remote_ip
        req = json.loads(self.request.body)
        if path == 'store_directories' :
            mount_hash = req.get('root', None)
            resp = self.store.store_directories(
                req['directories'],
                mount_hash=mount_hash,
                auth_session=auth_session)
            self.write(json_encoder.encode(resp))
        elif path == 'register':
            mount_meta =  {}
            if req['meta']:
                mount_meta.update(**req['meta'])
            mount_meta['remote_ip'] = remote_ip
            server_uuid = self.store.register(
                req['mount_uuid'], req['invitation'],
                json.dumps(mount_meta))
            self.write(json_encoder.encode(server_uuid))
        elif path == 'login':
            auth_session,server_uuid=self.store.login(req['mount_uuid'])
            json_data = json_encoder.encode({'auth_session': auth_session,
                                          'server_uuid': server_uuid})
            self.write(json_data)
        elif path == 'logout':
            self.store.logout(auth_session=auth_session)
        self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def get(self, path):
        auth_session = self.request.headers.get("Auth_session")
        hash_path = HashPath(path)
        lookup,is_dir = self._get_lookup(auth_session, hash_path)
        if not lookup.found():
            raise tornado.web.HTTPError(404)
        mime,enc = hash_path.mime_enc()
        if mime and enc:
            self.set_header('Content-Type', '{mime}; charset="{enc}"'.format(**locals()))
        elif mime:
            self.set_header('Content-Type', mime)

        fd = lookup.open_fd()
        if fd is not None:
            self.stream = tornado.iostream.PipeIOStream(fd)
            self.stream.read_until_close(callback=self.on_file_end,
                                         streaming_callback=self.on_chunk)
        else:
            self.on_chunk(lookup.stream().read())
            self.on_file_end(None)


    def on_file_end(self, s):
        if s:
            self.write(s)
        self.finish()  # close connection

    def on_chunk(self, chunk):
        self.write(chunk)
        self.flush()

def stop_server(signum, frame):
    tornado.ioloop.IOLoop.instance().stop()
    logging.info('Stopped!')


pid_route = (r'/(\.pid)$', _dummy_handler(str(os.getpid())))

app_dir = os.path.join(os.path.dirname(__file__),'app')
app_mount = Mount(app_dir)
app_route = (r'/\.app/(.*)$', MountHandler, {'mount': app_mount})

def _load_index():
    index = os.path.join(app_dir, 'index.html')
    with open(index, 'rb') as f:
        return f.read()

index_route = (r'(.*)$', _fn_handler(_load_index),)


class StoreServer:
    def __init__(self, store_root, port, secure, mounts = None, max_file_size = 20*GIGABYTE):
        self.store = HashStore(store_root, access_mode=AccessMode.from_bool(secure), init=False)
        self.port = port
        self.max_file_size = max_file_size
        self.mounts = dict(mounts or {})

    def create_invitation(self, message = ''):
        return str(self.store.create_invitation(message))

    def shutdown(self, wait_until_down):
        try:
            while True:
                response = requests.get('http://localhost:%d/.pid' % (self.port,))
                pid = int(response.content)
                if pid:
                    log.warn('Stopping %d' % pid)
                    os.kill(pid,signal.SIGINT)
                    if wait_until_down:
                        time.sleep(2)
                    else:
                        break
                else:
                    break
        except:
            pass


    def run_server(self):
        self.store.initialize()
        store_ref = {'store': self.store}

        handlers = [
            (r'/\.hashery/write_content$', StreamHandler, store_ref),
            (r'/\.hashery/(.*)$', HasheryHandler, store_ref),
            pid_route,
            app_route,
        ]
        if self.mounts:
            mount_names = list(self.mounts.keys())
            handlers.append((r'/(\.mounts)$', _dummy_handler( json_encoder.encode(mount_names)),))
            for mount_name in self.mounts:
                mount = self.mounts[mount_name]
                handlers.append((r'/\.raw/'+ mount_name + r'/(.*)$', MountHandler, {'mount': mount}) )
                handlers.append((r'/\.raw/(.*)$', HashMountHandler, store_ref))

        handlers.append(index_route)
        application = tornado.web.Application(handlers)
        signal.signal(signal.SIGINT, stop_server)
        http_server = tornado.httpserver.HTTPServer(application, max_body_size=self.max_file_size)
        http_server.listen(self.port)
        logging.info('StoreServer({0.store.root},{0.store.access_mode}) listening=0.0.0.0:{0.port}'.format(self) )
        tornado.ioloop.IOLoop.instance().start()


