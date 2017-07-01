import json
from hashstore.mymime import MIME_WDF, MIME_UDK_BUNDLE, guess_type
from hashstore.db import DbFile
from hashstore.session import _session, _session_dbf
from hashstore.local_store import HashStore, AccessMode
from hashstore.udk import process_stream,\
    UDK,UDKBundle,UdkSet,quick_hash
from hashstore.client import RemoteStorage
from hashstore.utils import quict, path_split_all, reraise_with_msg, \
    read_in_chunks, ensure_directory, FileNotFound, _cacheable, \
    json_encoder, ensure_unicode
from collections import defaultdict
import os
import uuid

from hashstore.dir_scan import parse_ignore_specs, ignore_files, \
    check_if_path_should_be_ignored

import logging


log = logging.getLogger(__name__)


def md_link(link, text, slashes_around = True):
    if slashes_around:
        link = '/' + link + '/'
    return '[' + text + '](' +link+ ')'


class Content:
    def __init__(self, mime, fd, inline):
        log.info(mime)
        self.mime = mime
        self.fd=fd
        self.inline = inline

    def render(self,auth_session = None):
        return self

    @staticmethod
    def from_lookup(mime,lookup):
        fd = lookup.open_fd()
        if fd is not None:
            return Content(mime,fd,None)
        else:
            return Content(mime,None,lookup.stream().read())


def split_path(path):
    if '..' in path:
        raise FileNotFound(path)
    is_directory = None
    if path[-1:] == '/':
        is_directory = True
    path = path.strip('/')
    split = path_split_all(path)
    if len(split) == 1 and len(split[0]) == 0:
        return [], True
    return split, is_directory


class StorePath:
    def __init__(self, store, split, is_dir):
        self.store = store
        self.path = split
        self.root_udk = UDK.ensure_it(self.path[0])
        self.is_directory = is_dir
        if len(self.path) > 1:
            self.leaf_udk = None
        else:
            self.leaf_udk = self.root_udk

    def render(self, auth_session=None):
        lookup = self.lookup(auth_session=auth_session)
        if self.is_directory:
            mime = MIME_UDK_BUNDLE
        else:
            mime = guess_type(self.path[-1])
        return Content.from_lookup(mime, lookup)

    def root_udk(self):
        return UDK.ensure_it(self.path[0])

    def need_lookup(self):
        return self.leaf_udk is None

    def lookup(self, auth_session):
        if self.need_lookup():
            if self.store.access_mode == AccessMode.ALL_SECURE:
                self.store.check_auth_session(auth_session=auth_session)
            is_directory = True
            udk = self.root_udk
            if len(self.path) > 1:
                for i in range(1, len(self.path)):
                    content = self.store.get_content(udk, auth_session=auth_session)
                    bundle = UDKBundle(content)
                    udk = bundle[self.path[i]]
                    is_directory = udk.named_udk_bundle
            self.leaf_udk = udk
            self.is_directory = is_directory
        return self.store.lookup(self.leaf_udk)


class PathResover:
    def __init__(self,store_root, access_mode, mounts):
        self.store = HashStore(store_root, access_mode=access_mode,
                               init=False)
        self.mounts = dict(mounts or {})

    def path(self, path):
        split, is_dir = split_path(path)
        if len(split) > 0 :
            k = split[0]
            if k in self.mounts:
                return self.mounts[k].file(split[1:])
            else:
                try:
                    return StorePath(self.store,split,is_dir)
                except:
                    if len(k) > 0:
                        return self.query(k)
        return self.query('index')

    def query(self, q):
        @_session_dbf(self.store.dbf)
        def index(session=None):

            s = json_encoder.encode({'columns': [
                {'name': 'mount', 'type': 'link'},
                {'name': 'created', 'type': 'timestamp'},
            ]}) + '\n'

            for m in self.mounts.keys():
                s += json_encoder.encode([md_link(m, m), None]) + '\n'

            order_by = '1=1 order by created_dt desc limit 100'
            for row in session.dbf.select('push', {}, where=order_by):
                udk = str(row['mount_hash'])
                s += json_encoder.encode(
                    [md_link(udk, udk), row['created_dt']]) + '\n'
            return Content(MIME_WDF, None, s)
        return locals()[q]()


class Mount:
    def __init__(self,name, root):
        self.name = name
        self.root = os.path.abspath(root)

    def file(self, path):
        return File(self,path)

    def __str__(self):
        return self.root


class File:
    def __init__(self,mount,split):
        abs_path = os.path.join(mount.root, *split)
        if not os.path.exists(abs_path):
            raise FileNotFound(abs_path)
        self.mount = mount
        self.path = split
        self.abs_path = abs_path
        self.cache = {}

    def child(self, name):
        child_path = list(self.path)
        child_path.append(name)
        return File(self.mount, child_path)

    @_cacheable
    def isdir(self):
        return os.path.isdir(self.abs_path)

    @_cacheable
    def filename(self):
        return self.mount.name if len(self.path) == 0 else self.path[-1]

    @_cacheable
    def size(self):
        return 0 if self.isdir() else os.path.getsize(self.abs_path)

    @_cacheable
    def type(self):
        return 'dir' if self.isdir() else 'file'

    @_cacheable
    def link(self):
        path = '/' + self.mount.name + '/' + '/'.join(self.path)
        return path + ('/' if self.isdir() else '')

    @_cacheable
    def mime(self):
        return MIME_WDF if self.isdir() else guess_type(self.filename())

    def list_dir(self):
        if self.isdir():
            return [self.child(name) for name in os.listdir(self.abs_path)]
        return None

    def record(self):
        return [md_link(self.link(), self.filename(), slashes_around=False),
                self.size(),
                self.type(),
                self.mime()]

    COLUMNS = [
        {'name': 'filename', 'type': 'link'},
        {'name': 'size', 'type': 'number'},
        {'name': 'type', 'type': 'string'},
        {'name': 'mime', 'type': 'string'},
    ]

    def render(self, auth_session = None):
        if self.isdir():
            s = json_encoder.encode({'columns': self.COLUMNS}) + '\n'
            for f in self.list_dir():
                s += json_encoder.encode(f.record()) + '\n'
            return Content(MIME_WDF, None, s)
        fd = os.open(self.abs_path, os.O_RDONLY)
        return Content(self.mime(), fd, None)


