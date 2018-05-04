#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import requests
import os
import time
import signal

import sys

from hashstore.bakery.cake_store import StoreContext, GuestAccess, \
    FROM_COOKIE
from hashstore.bakery import Content, cake_or_path, SaltedSha
from hashstore.utils import json_encoder, FileNotFound, ensure_bytes, \
    exception_message
from hashstore.utils.file_types import guess_type
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

        session_id = self.request.headers.get('UserSession')
        no_session_in_headers = session_id is None or \
                                session_id == FROM_COOKIE
        if no_session_in_headers:
            session_id = self.get_cookie("UserSession")

        client_id = self.request.headers.get('ClientID')
        remote_ip = self.request.headers.get('X-Real-IP') or \
                    self.request.remote_ip
        self.ctx().params['remote_ip'] = remote_ip
        try:
            self.access = self.ctx().validate_session(
                session_id, client_id)
        except:
            log.debug(exception_message())
            self.access = GuestAccess(self.ctx())

    def ctx(self):
        if self._ctx is None:
            self._ctx = StoreContext(self.store)
            self._ctx.__enter__()
        return self._ctx

    def close_ctx(self):
        if self._ctx is not None:
            self._ctx.__exit__(None, None, None)
            self._ctx = None

    def on_finish(self):
        self.close_ctx()


class _ContentHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET']

    @tornado.web.asynchronous
    @gen.coroutine
    def get(self, path):
        try:
            content = self.content(path)
            if content.mime is not None:
                mime = content.mime
            else:
                mime = guess_type(path)
                if mime is None:
                    mime = 'application/octet-stream'
            self.set_header('Content-Type', mime)
            if content.has_file():
                self.stream = PipeIOStream(content.open_fd())
                self.stream.read_until_close(
                    callback=self.on_file_end,
                    streaming_callback=self.on_chunk)
            else:
                self.finish(content.get_data())

        except FileNotFound:
            self.send_error(404)
        except:
            log.exception('error')
            self.send_error(500)

    def on_file_end(self, s):
        if s:
            self.write(s)
        self.finish()  # close connection

    def on_chunk(self, chunk):
        self.write(chunk)
        self.flush()


class GetCakeHandler(_StoreAccessMixin, _ContentHandler):
    def content(self, path):
        cake = cake_or_path(path[5:], relative_to_root=True)
        prefix = path[:5]
        content = self.access.get_content(cake)
        if 'data/' == prefix:
            return content
        elif 'info/' == prefix:
            return Content(data=json_encoder.encode(content),
                           mime='application/json')
        else:
            raise AssertionError('Unknown prefix: %s' % prefix)


@tornado.web.stream_request_body
class StreamHandler(_StoreAccessMixin, tornado.web.RequestHandler):
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


class PostHandler(_StoreAccessMixin, tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['POST']

    def post(self):
        req = json.loads(self.request.body)
        res = self.access.process_api_call(req['call'], req['msg'])

        self.write(json_encoder.encode(res))
        self.finish()


def stop_server(signum, frame):
    ioloop = tornado.ioloop.IOLoop.instance()
    # ioloop.stop()
    ioloop.add_callback(ioloop.stop)
    logging.info('Stopped!')


def _string_handler(s):
    class StringHandler(_ContentHandler):
        def content(self, _):
            return Content(data=ensure_bytes(s), mime='text/plain')

    return StringHandler


class CakeServer:
    def __init__(self, store, max_file_size=20 * GIGABYTE):
        self.store = store
        self.config = self.store.server_config()
        self.max_file_size = max_file_size

    def shutdown(self, wait_until_down):
        try:
            while True:
                response = requests.get('http://localhost:%d/-/pid' %
                                        (self.config.port,))
                pid = int(response.content)
                if pid:
                    log.warning('Stopping %d' % pid)
                    os.kill(pid, signal.SIGINT)
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
                return Content(file=os.path.join(app_dir, path))\
                    .guess_file_type()

        class IndexHandler(_ContentHandler):
            def content(self, _):
                return Content(file=os.path.join(app_dir, 'index.html'))\
                    .guess_file_type()

        pid = str(os.getpid())
        server_id = json_encoder.encode(
            (str(self.config.id),
             str(SaltedSha.from_secret(str(self.config.secret))))
        )

        store_ref = {'store': self.store}
        handlers = [
            (r'/-/(pid)$', _string_handler(pid),),
            (r'/-/(server_id)$', _string_handler(server_id),),
            (r'/-/api/up$', StreamHandler, store_ref),
            (r'/-/api/post$', PostHandler, store_ref),
            (r'/-/get/(.*)$', GetCakeHandler, store_ref),
            (r'/-/app/(.*)$', AppContentHandler,),
            (r'(.*)$', IndexHandler,)
            # - ~ _
        ]
        application = tornado.web.Application(handlers)
        signal.signal(signal.SIGINT, stop_server)
        http_server = tornado.httpserver.HTTPServer(
            application, max_body_size=self.max_file_size)
        http_server.listen(self.config.port)
        logging.info('CakeServer({0.store.store_dir}) '
                     'listening=0.0.0.0:{0.config.port}'.format(self))
        tornado.ioloop.IOLoop.instance().start()
        logging.info('Finished')
