#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import requests
import os
import time
import logging
import signal
from hashstore.mount import PathResover, Content, split_path
import six
from hashstore.utils import json_encoder
import json
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


def _dummy_handler(content):
    return _raw_handler(lambda h,p: Content('text/plain',None,content))


@tornado.web.stream_request_body
class StreamHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['POST']

    def initialize(self,resolver):
        self.store = resolver.store

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


class PostHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['POST']

    def initialize(self,resolver):
        self.store = resolver.store

    def post(self, path):
        log.debug("post: %s" % path)
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
                json_encoder.encode(mount_meta))
            self.write(json_encoder.encode(server_uuid))
        elif path == 'login':
            auth_session,server_uuid=self.store.login(req['mount_uuid'])
            json_data = json_encoder.encode({
                'auth_session': auth_session,
                'server_uuid': server_uuid })
            self.write(json_data)
        elif path == 'logout':
            self.store.logout(auth_session=auth_session)
        self.finish()


def _raw_handler(content_fn):
    class RawHandler(tornado.web.RequestHandler):
        SUPPORTED_METHODS = ['GET']

        @tornado.web.asynchronous
        @gen.coroutine
        def get(self, path):
            try:
                content=content_fn(self,path)
                if content.mime is not None:
                    self.set_header('Content-Type', content.mime)
                if content.fd is not None:
                    self.stream = tornado.iostream.PipeIOStream(content.fd)
                    self.stream.read_until_close(
                        callback=self.on_file_end,
                        streaming_callback=self.on_chunk)
                else:
                    self.finish(content.inline)
            except FileNotFound:
                self.send_error(404)

        def on_file_end(self, s):
            if s:
                self.write(s)
            self.finish()  # close connection

        def on_chunk(self, chunk):
            self.write(chunk)
            self.flush()
    return RawHandler


def stop_server(signum, frame):
    tornado.ioloop.IOLoop.instance().stop()
    logging.info('Stopped!')


class StoreServer(PathResover):
    def __init__(self, store_root, port, access_mode, mounts,
                 max_file_size = 20*GIGABYTE):
        PathResover.__init__(self, store_root, access_mode, mounts)
        self.port = port
        self.max_file_size = max_file_size

    def create_invitation(self, message = ''):
        return str(self.store.create_invitation(message))

    def shutdown(self, wait_until_down):
        try:
            while True:
                response = requests.get('http://localhost:%d/.pid' %
                                        (self.port,))
                pid = int(response.content)
                if pid:
                    log.warning('Stopping %d' % pid)
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
        resolver_ref = {'resolver': self}

        app_dir = os.path.join(os.path.dirname(__file__), 'app')
        app_mount = Mount('.app', app_dir)

        def app_content_fn(_,path):
            split, is_dir = split_path(path)
            file = app_mount.file(split)
            return file.render()

        def hash_and_mount_content_fn(handler,path):
            auth_session = handler.request.headers.get("Auth_session")
            file = self.path(path)
            return file.render(auth_session=auth_session)

        def _load_index(h, path):
            index = os.path.join(app_dir, 'index.html')
            fd = os.open(index, os.O_RDONLY)
            return Content('text/html', fd, None)

        handlers = [
            (r'/\.up/stream$', StreamHandler, resolver_ref),
            (r'/\.up/post/(.*)$', PostHandler, resolver_ref),
            (r'/\.raw/(.*)$', _raw_handler(hash_and_mount_content_fn) ),
            (r'/(\.pid)$', _dummy_handler(str(os.getpid()))),
            (r'/\.app/(.*)$', _raw_handler(app_content_fn)),
            (r'(.*)$', _raw_handler(_load_index),)
        ]
        application = tornado.web.Application(handlers)
        signal.signal(signal.SIGINT, stop_server)
        http_server = tornado.httpserver.HTTPServer(application, max_body_size=self.max_file_size)
        http_server.listen(self.port)
        logging.info('StoreServer({0.store.root},{0.store.access_mode}) listening=0.0.0.0:{0.port}'.format(self) )
        tornado.ioloop.IOLoop.instance().start()


