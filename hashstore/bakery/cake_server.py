#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import requests
import os
import time
import signal

from hashstore.bakery.cake_store import StoreContext, GuestAccess
from hashstore.bakery.content import Content
from hashstore.bakery.ids import cake_or_path
from hashstore.utils import json_encoder, FileNotFound, ensure_bytes
import json
import tornado.web
import tornado.template
import tornado.ioloop
import tornado.httpserver
import tornado.gen as gen
from tornado.iostream import PipeIOStream
import logging
log = logging.getLogger(__name__)

GIGABYTE = pow(1024, 3)


class _StoreAccessMixin:

    def initialize(self, store):
        self.store = store
        self._ctx = None
        session_id = self.request.headers.get("UserSession")
        client_id = self.request.headers.get("ClientID")
        remote_ip = self.request.headers.get( "X-Real-IP") or \
                    self.request.remote_ip
        self.ctx().params['remote_ip'] = remote_ip
        try:
            self.access = self.ctx().validate_session(session_id,client_id)
        except:
            self.access = GuestAccess(self.ctx())

    def ctx(self):
        if self._ctx is None:
            self._ctx = StoreContext(self.store)
            self._ctx.__enter__()
        return self._ctx

    def close_ctx(self):
        if self._ctx is not None:
            self._ctx.__exit__(None,None,None)
            self._ctx = None

    def on_finish(self):
        self.close_ctx()


class _ContentHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET']

    @tornado.web.asynchronous
    @gen.coroutine
    def get(self, path):
        try:
            content=self.content(path)
            if content.mime is not None:
                self.set_header('Content-Type', content.mime)

            if content.has_file():
                self.stream = PipeIOStream(content.open_fd())
                self.stream.read_until_close(
                    callback=self.on_file_end,
                    streaming_callback=self.on_chunk)
            else:
                self.finish(content.get_data())

        except FileNotFound:
            self.send_error(404)

    def on_file_end(self, s):
        if s:
            self.write(s)
        self.finish()  # close connection

    def on_chunk(self, chunk):
        self.write(chunk)
        self.flush()


class GetCakeHandler(_ContentHandler, _StoreAccessMixin):

    def content(self, path):
        cake = cake_or_path(path, relative_to_root=True)
        return self.access.get_content(cake)


@tornado.web.stream_request_body
class StreamHandler(tornado.web.RequestHandler, _StoreAccessMixin):
    SUPPORTED_METHODS = ['POST']

    def post(self):
        k = self.w.done()
        log.info('write_content: %s' % k)
        self.write(json_encoder.encode(k))
        self.finish()

    def prepare(self):
        self.w = self.access.writer()

    def data_received(self, chunk):
        self.w.write(chunk)


class PostHandler(tornado.web.RequestHandler, _StoreAccessMixin):
    SUPPORTED_METHODS = ['POST']

    def post(self, path):
        log.debug("post: %s" % path)
        req = json.loads(self.request.body)
        res = self.access.process_api_call(req['call'], req['msg'])
        self.write(json_encoder.encode(res))
        self.finish()


def stop_server(signum, frame):
    tornado.ioloop.IOLoop.instance().stop()
    logging.info('Stopped!')


class CakeServer:
    def __init__(self, store, max_file_size = 20*GIGABYTE):
        self.store = store
        self.config = self.store.server_config()
        self.max_file_size = max_file_size

    def shutdown(self, wait_until_down):
        try:
            while True:
                response = requests.get('http://localhost:%d/.pid' %
                                        (self.config.port,))
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

        app_dir = os.path.join(os.path.dirname(__file__), 'app')

        class AppContentHandler(_ContentHandler):
            def content(self, path):
                return Content(file=os.path.join(app_dir, path))

        class IndexHandler(_ContentHandler):
            def content(self, _):
                return Content(file=os.path.join(app_dir, 'index.html'))

        class PidHandler(_ContentHandler):
            def content(self, _):
                return Content(data=ensure_bytes(str(os.getpid())),
                               mime='text/plain')

        store_ref = {'store': self.store}
        handlers = [
            (r'/\.up/stream$', StreamHandler, store_ref),
            (r'/\.up/post/(.*)$', PostHandler, store_ref),
            (r'/(\.pid)$', PidHandler,),
            (r'/\.raw/(.*)$', GetCakeHandler, store_ref),
            (r'/\.app/(.*)$', AppContentHandler, ),
            (r'(.*)$', IndexHandler,)
        ]
        application = tornado.web.Application(handlers)
        signal.signal(signal.SIGINT, stop_server)
        http_server = tornado.httpserver.HTTPServer(
            application, max_body_size=self.max_file_size)
        http_server.listen(self.config.port)
        logging.info('CakeServer({0.store.store_dir}) '
                     'listening=0.0.0.0:{0.config.port}'.format(self) )
        tornado.ioloop.IOLoop.instance().start()


