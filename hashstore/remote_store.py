#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
        self.w = self.store.writer()

    def data_received(self, chunk):
        self.w.write(chunk)


class HasheryHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET','POST']

    def initialize(self,store):
        self.store = store

    def post(self, path):
        log.info("post: %s" % path)
        if path == 'store_directories' :
            r = self.store.store_directories(json.loads(self.request.body))
            self.write(json_encoder.encode(r))
        elif path == 'register':
            x_real_ip = self.request.headers.get("X-Real-IP")
            remote_ip = x_real_ip or self.request.remote_ip
            mount_uuid,mount_path = json.loads(self.request.body)
            self.store.register(mount_uuid,mount_path,remote_ip)
        self.finish()

    def get(self, path):
        file = HashPath(path)
        mime,enc = file.mime_enc()
        if mime and enc:
            self.set_header('Content-Type', '{mime}; charset="{enc}"'.format(**locals()))
        elif mime:
            self.set_header('Content-Type', mime)
        content = self.store.get_content(file.udk())
        while 1:
            chunk = content.read(64*1024)
            if not chunk:
                break
            self.write(chunk)
        self.finish()


def stop_server(signum, frame):
    tornado.ioloop.IOLoop.instance().stop()
    logging.info('Stopped!')


def shutdown(port, wait_until_down):
    import requests
    try:
        while True:
            response = requests.get('http://localhost:%d/.pid' % (port,))
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


def create_handler(get_content):
    class Handler(tornado.web.RequestHandler):
        SUPPORTED_METHODS = ['GET']

        def get(self, path):
            self.write(get_content())
            self.finish()
    return Handler


def run_server(store_root, port):
    logging.info('mount: %s' % store_root)
    store = HashStore(store_root)
    application = tornado.web.Application([
        (r'/\.hashery/write_content$', StreamHandler, {'store': store}),
        (r'/\.hashery/(.*)$', HasheryHandler, {'store': store}),
        (r'/(\.pid)$', create_handler(lambda: '%d' % os.getpid()),),
    ])
    signal.signal(signal.SIGINT, stop_server)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)
    logging.info('Serving HTTP on 0.0.0.0 port %d ...' % port)
    tornado.ioloop.IOLoop.instance().start()


