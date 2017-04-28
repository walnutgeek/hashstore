#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests
import os
import time
import logging
import mimetypes
import signal
from hashstore.local_store import HashStore
from hashstore.udk import UDK
import json
from hashstore.utils import json_encoder

import tornado.web
import tornado.template
import tornado.ioloop
import tornado.httpserver

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class HashPath:
    def __init__(self,path):
        log.info(path)
        self.path = path

    def mime_enc(self):
        return mimetypes.guess_type(self.path)

    def udk(self):
        return UDK.ensure_it(self.path[:64])


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
            resp = self.store.store_directories(
                req['directories'],
                mount_hash=req.get('root', None),
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

    def get(self, path):
        file = HashPath(path)
        mime,enc = file.mime_enc()
        if mime and enc:
            self.set_header('Content-Type', '{mime}; charset="{enc}"'.format(**locals()))
        elif mime:
            self.set_header('Content-Type', mime)
        auth_session = self.request.headers.get("Auth_session")
        content = self.store.get_content(file.udk(),auth_session=auth_session)
        while 1:
            chunk = content.read(64*1024)
            if not chunk:
                break
            self.write(chunk)
        self.finish()


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
    def __init__(self, store_root, port, secure):
        self.store = HashStore(store_root, secure=secure, init=False)
        self.port = port

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
        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(self.port)
        logging.info('StoreServer({0.store.root},secure={0.store.secure}) listening=0.0.0.0:{0.port}'.format(self) )
        tornado.ioloop.IOLoop.instance().start()


