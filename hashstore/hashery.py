#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import logging
import mimetypes
import signal
from hashstore.localstore import HashStore
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
        l = 0
        if buffer is not None:
            l = len(chunk)
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


def shutdown(port,do_shutdown):
    try:
        import urllib2
        response = urllib2.urlopen('http://localhost:%d/.pid' % (port,))
        pid = int(response.read())
        logging.info('Stopping %d' % pid)
        os.kill(pid,signal.SIGINT)
        if not do_shutdown:
            import time
            time.sleep(2)
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


def _args_parser():
    import argparse

    parser = argparse.ArgumentParser(description='Run hashery')
    parser.add_argument('--port', metavar='N', type=int, nargs='?',
                        default=7532, help='a port to listen')
    parser.add_argument('--dir', metavar='dir', nargs='?',
                        default='.', help='a directory for hashstore')
    parser.add_argument('--shutdown', action='store_true',
                        help='shutdown server')

    return parser

def main():
    parser = _args_parser()
    args = parser.parse_args()
    shutdown(args.port,args.shutdown)
    if not args.shutdown:
        run_server(args.dir, args.port)

if __name__ == '__main__':
    main()