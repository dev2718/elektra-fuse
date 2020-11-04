#!/usr/bin/env python3

import kdb
from util import ls, key_type, file_contents, size_of_file, update_key_value, create_key, get_meta_map, update_meta_map, delete_key, is_directory_empty, has_meta, get_meta, set_meta, os_path_to_elektra_path, dir_file_special_name

import errno, stat
from time import time
from pathlib import Path

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
import logging, subprocess

startup_time = time()

#fuse references: https://www.cs.hmc.edu/~geoff/classes/hmc.cs135.201109/homework/fuse/fuse_doc.html
#                 https://libfuse.github.io/doxygen/structfuse__operations.html#a729e53d36acc05a7a8985a1a3bbfac1e
#TODO: permission handling, maybe see fuse 'default_permissions'

class ElektraFuse(LoggingMixIn, Operations):
    'Elektra as a FUSE-Filesystem'

    def __init__(self):
        self.fd = 0

    def _new_fd(self):
        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        is_value_of_file = Path(path).name == dir_file_special_name

        is_dir, is_file = key_type(path)

        if is_value_of_file:
            mode = stat.S_IFREG
            #resolve to real key
            path = str(Path(path).parent)
        elif not is_dir and not is_file:
            mode = errno.ENOENT
        elif is_dir and is_file:
            mode = stat.S_IFDIR
        elif is_dir:
            mode = stat.S_IFDIR
        elif is_file and has_meta(path, "fuse-directory"):
            mode = stat.S_IFDIR
        elif is_file:
            mode = stat.S_IFREG

        if mode == stat.S_IFREG:
            try:
                filesize = size_of_file(path) 
            except KeyError: #key does not exist
                mode = ENOENT

        if mode == stat.S_IFDIR:
            return dict(
                st_mode = (mode | 0o755),
                st_ctime = startup_time, #correct times currently not supported
                st_mtime = startup_time,
                st_atime = startup_time,
                st_nlink = 2)
        elif mode == stat.S_IFREG:
            return dict(
                st_mode = (mode | 0o755),
                st_size = filesize,
                st_ctime = startup_time,
                st_mtime = startup_time,
                st_atime = startup_time,
                st_nlink = 1) #TODO: maybe consider key.getReferenceCounter?
        else:
            raise FuseOSError(mode)
        
    def open(self, path, flags):
        return self._new_fd() #not used but nessecary

    def read(self, path, size, offset, fh):
        return file_contents(path)[offset:offset+size]

    def write(self, path, data, offset, fh):

        try:
            old_value = file_contents(path)
            new_value = old_value[:offset] + data + old_value[offset + len(data):]

            update_key_value(path, new_value)

            return len(data)
        except KeyError:
            raise FuseOSError(errno.ENOENT)
        except kdb.KDBException:
            raise FuseOSError(errno.EROFS) #TODO differentiate between validation error, write only keys etc


    def truncate(self, path, length, fh=None):
        old_value = file_contents(path)
        new_value = old_value[:length].ljust(length, '\x00'.encode('UTF-8')) #if length increased, fill new space with zeros
        update_key_value(path, new_value)

    def readdir(self, path, fh):
        if path == "/":
            return ['.', '..', 'system', 'user']

        dir_set, file_set = ls(path)
        dir_list = list(dir_set)
        file_list = list(file_set)

        return ['.', '..'] + dir_list + file_list

    def create(self, path, mode):
        if path.count('/') <= 1:
            raise FuseOSError(errno.EROFS) #cannot create key in top level directory (reserved for /user, /system ...)

        create_key(path) #TODO: consider mode arguement
        #TODO: maybe consider possible error codes as in https://linux.die.net/man/2/
        
        return self._new_fd()

    def mkdir(self, path, mode):
        self.create(path, mode)
        set_meta(path, "fuse-directory", "")  # 'hack' to enable creation of empty folders (these would otherwise automatically become files)


    def getxattr(self, path, name, position=0):
        try:
            return get_meta_map(path)[name].encode("UTF-8")
        except KeyError:
            raise FuseOSError(errno.ENODATA)

    def listxattr(self, path):
        return get_meta_map(path).keys()

    def removexattr(self, path, name):
        meta_map = get_meta_map(path)

        try:
            del meta_map[name]
            update_meta_map(path, meta_map)
        except KeyError:
            raise FuseOSError(errno.ENODATA)

    def setxattr(self, path, name, value, options, position=0):
        meta_map = get_meta_map(path)
        try:
            meta_map[name] = value.decode("UTF-8")
        except UnicodeDecodeError:
            meta_map[name] = '' #meta keys cannot contain binary data (apparantly) (TODO: check)
        update_meta_map(path, meta_map)

    def unlink(self, path):
        #delete_key(path) keyset.cut behaved unexpected and deleted child keys => using kdb directly

        returncode = subprocess.run(["kdb", "rm", os_path_to_elektra_path(path)]).returncode
        if returncode != 0:
            raise FuseOSError(errno.EROFS) #TODO: differentiate between different error

    def rmdir(self, path):
        if not is_directory_empty(path):
            raise FuseOSError(errno.ENOTEMPTY)
        else:
            self.unlink(path)

    def rename(self, old_path, new_path):
        #clumsy to implement using the python api => using kdb directly
        returncode = subprocess.run(["kdb", "mv", "-r", os_path_to_elektra_path(old_path), os_path_to_elektra_path(new_path)]).returncode
        if returncode != 0:
            raise FuseOSError(errno.EROFS) #TODO: differentiate between different error

    def chmod(self, path, mode):
        return 0 #TODO

    def chown(self, path, uid, gid):
        return 0 #TODO

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mount', default="/root/mount")
    parser.add_argument('-f', '--foreground', default=False)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(ElektraFuse(), args.mount, foreground=args.foreground, allow_other=True)