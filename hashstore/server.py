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
from hashstore.utils import json_encoder, path_split_all

import tornado.web
import tornado.template
import tornado.ioloop
import tornado.httpserver
import tornado.gen as gen
import tornado.iostream

GIGABYTE = pow(1024, 3)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


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


class HasheryHandler(tornado.web.RequestHandler):
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
        hash_path = HashPath(path)
        udk = hash_path.udk()
        auth_session = self.request.headers.get("Auth_session")
        if hash_path.need_to_be_resolved():
            for i in range(1, len(hash_path)) :
                bundle = UDKBundle(self.store.get_content(udk,auth_session=auth_session))
                udk = bundle[hash_path[i]]
        mime,enc = hash_path.mime_enc()
        if mime and enc:
            self.set_header('Content-Type', '{mime}; charset="{enc}"'.format(**locals()))
        elif mime:
            self.set_header('Content-Type', mime)
        self.udk = udk
        if self.store.access_mode == AccessMode.ALL_SECURE:
            self.store.check_auth_session(auth_session=auth_session)
        lookup = self.store.lookup(self.udk)
        fd = lookup.fd()
        if fd is not None:
            self.stream = tornado.iostream.PipeIOStream(lookup.fd())
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


def create_handler(get_content):
    class Handler(tornado.web.RequestHandler):
        SUPPORTED_METHODS = ['GET']

        def get(self, path):
            self.write(get_content())
            self.finish()
    return Handler


def stop_server(signum, frame):
    tornado.ioloop.IOLoop.instance().stop()
    logging.info('Stopped!')


class StoreServer:
    def __init__(self, store_root, port, secure, max_file_size = 20*GIGABYTE):
        self.store = HashStore(store_root, access_mode=AccessMode.from_bool(secure), init=False)
        self.port = port
        self.max_file_size = max_file_size

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
        application = tornado.web.Application([
            (r'/\.hashery/write_content$', StreamHandler, {'store': self.store}),
            (r'/\.hashery/(.*)$', HasheryHandler, {'store': self.store}),
            (r'/(\.pid)$', create_handler(lambda: '%d' % os.getpid()),),
        ])
        signal.signal(signal.SIGINT, stop_server)
        http_server = tornado.httpserver.HTTPServer(application, max_body_size=self.max_file_size)
        http_server.listen(self.port)
        logging.info('StoreServer({0.store.root},secure={0.store.access_mode}) listening=0.0.0.0:{0.port}'.format(self) )
        tornado.ioloop.IOLoop.instance().start()


