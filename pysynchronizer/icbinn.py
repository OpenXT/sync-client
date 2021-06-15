#
# Copyright (c) 2013 Citrix Systems, Inc.
# Copyright (c) 2021 Daniel P. Smith, Apertus Solutions LLC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


from os.path import join
from pathlib import Path

from .errors import InsufficientIcbinnPaths, IcbinnConnectError, PlatformError, IcbinnError, TargetStateError
from .xenstore import Xenstore
from .oxt_dbus import OXTDBusApi
from .singleton import Singleton
from .utils import uuid_to_dbus_path

from pyicbinn import icbinn_clnt_create_argo, icbinn_close, icbinn_lock
from pyicbinn import icbinn_mkdir, icbinn_open, icbinn_pwrite, icbinn_rand
from pyicbinn import icbinn_readent, icbinn_rename, icbinn_stat, icbinn_pread
from pyicbinn import icbinn_unlink

ICBINN_SERVER_PORT = 4878
ICBINN_SERVER_DOMAIN_ID = 0
ICBINN_MAXDATA = 65536
ICBINN_FILE = 0
ICBINN_DIRECTORY = 1
ICBINN_UNKNOWN = 2
ICBINN_LTYPE_RDLCK = 0
ICBINN_LTYPE_WRLCK = 1
ICBINN_LTYPE_UNLCK = 2
ICBINN_RANDOM = 0
ICBINN_URANDOM = 1

DISK_DIR = 'disks'
ENCRYPT_SNAPSHOTS = 'encrypt_snapshots'
STATUS_OKAY = 0
STATUS_INTERNAL_EXCEPTION = 1
STATUS_FAILED = 2
DOWNLOAD_BLOCK_SIZE = 512 * 1024
ENCRYPTION_KEY_BYTES = 64
PROGRESS_INTERVAL = 1
DISK_TYPE_ISO = 'iso'
DISK_TYPE_VHD = 'vhd'
DISK_TYPES = [DISK_TYPE_ISO, DISK_TYPE_VHD]
RPC_PREFIX = 'rpc:'

class Icbinn(Singleton):
    def __init__(self):
        uuid_node = Path('/sys/hypervisor/uuid')
        if uuid_node.exists():
            syncvm_object_path = uuid_to_dbus_path('/vm/', uuid_node.read_text().strip())
        else:
            syncvm_object_path = Xenstore.read('vm').rstrip().replace('-', '_')

        paths = OXTDBusApi.open_vm(syncvm_object_path).get_property('icbinn-path').split(',')

        if len(paths) != 2:
            raise InsufficientIcbinnPaths(2, paths)

        self.storage = IcbinnRemote(paths[0], server_port=ICBINN_SERVER_PORT + 0)
        # Unused at this time, commenting out to save on unnecessary Argo connections
        #self.config = IcbinnRemote(paths[1], server_port=ICBINN_SERVER_PORT + 1)

class IcbinnRemote(object):
    def __init__(self, mount_point,
                 server_domain_id=ICBINN_SERVER_DOMAIN_ID,
                 server_port=ICBINN_SERVER_PORT):
        self.mount_point = mount_point

        try:
            self.icbinn = icbinn_clnt_create_argo(server_domain_id,
                                                 server_port)
        except Exception as exc:
            raise IcbinnConnectError("failed to connect to icbinn server at "
                                     "(%d, %d): icbinn_clnt_create_argo "
                                     "failed: %r" % (server_domain_id,
                                                     server_port, exc))
        if self.icbinn is None:
            raise IcbinnConnectError("failed to connect to icbinn server at "
                                     "(%d, %d): icbinn_clnt_create_argo "
                                     "failed" % (server_domain_id,
                                                 server_port))

    def exists(self, path):
        try:
            res = self.stat(path)
        except IcbinnError:
            return False
        return res[1] in [ICBINN_FILE, ICBINN_DIRECTORY]

    def listdir(self, path):
        files = []
        while True:
            entry = icbinn_readent(self.icbinn, str(path), len(files))
            if entry is None:
                break
            files.append(entry[0])
        return files

    def mkdir(self, path):
        if icbinn_mkdir(self.icbinn, str(path)) < 0:
            raise PlatformError("error creating icbinn directory '%s': "
                                "icbinn_mkdir failed" % path)

    def makedirs(self, path, timeout=10):
        # avoid leading and trailing slash confusion
        segs = [x for x in path.split('/') if x]
        for here in [join(*segs[0:y]) for y in range(1, len(segs) + 1)]:
            # if the segment exists, continue
            if self.exists(here):
                continue
            try:
                self.mkdir(here)
            except PlatformError:
                pass
        if not self.stat(path)[1] == ICBINN_DIRECTORY:
            raise PlatformError("unable to create %s over icbinn"
                                % (here))

    def open(self, path, mode):
        return IcbinnFile(self.icbinn, path, mode)

    def rename(self, src, dst):
        if icbinn_rename(self.icbinn, str(src), str(dst)) < 0:
            raise IcbinnError("error renaming icbinn file '%s' to '%s': "
                              "icbinn_rename failed" % (src, dst))

    def stat(self, path):
        try:
            return icbinn_stat(self.icbinn, str(path))
        except OSError as exc:
            raise IcbinnError("error statting icbinn file '%s': icbinn_stat "
                              "failed: %s" % (path, exc))

    def unlink(self, path):
        if icbinn_unlink(self.icbinn, str(path)) < 0:
            raise IcbinnError("error unlinking icbinn file '%s': "
                              "icbinn_unlink failed" % path)

    def rand(self, src, size):
        data = ""
        while True:
            if len(data) == size:
                break
            try:
                data += icbinn_rand(self.icbinn, src, size - len(data))
            except IOError as exc:
                raise IcbinnError("error reading random data from icbinn: "
                                  "icbinn_rand failed: %s" % exc)
        return data

    def write_file(self, name, content):
        file_obj = self.open(name, O_WRONLY | O_CREAT)
        file_obj.pwrite(content, 0)
        file_obj.close()

    def mounted_path(self, path):
        components = path.split('/')
        if '.' in components or '..' in components:
            raise TargetStateError('invalid components in %s' % (path))
        return join(self.mount_point, path)

class IcbinnFile(object):
    def __init__(self, icbinn, path, mode):
        self.icbinn = icbinn
        self.path = path
        self.write_offset = 0

        self.fd = icbinn_open(self.icbinn, str(self.path), mode)
        if self.fd < 0:
            raise IcbinnError("error opening icbinn file '%s': icbinn_open "
                              "failed" % self.path)

    def close(self):
        if icbinn_close(self.icbinn, self.fd) < 0:
            raise IcbinnError("error closing icbinn file '%s': icbinn_close "
                              "failed" % self.path)

    def get_read_lock(self):
        if icbinn_lock(self.icbinn, self.fd, ICBINN_LTYPE_RDLCK) < 0:
            raise IcbinnError("error getting read lock on icbinn file '%s': "
                              "icbinn_lock failed" % self.path)

    def get_write_lock(self):
        if icbinn_lock(self.icbinn, self.fd, ICBINN_LTYPE_WRLCK) < 0:
            raise IcbinnError("error getting write lock on icbinn file '%s': "
                              "icbinn_lock failed" % self.path)

    def seek(self, offset):
        self.write_offset = offset

    def write(self, data):
        try:
            self.pwrite(data, self.write_offset)
        except IcbinnError as e:
            raise e

        self.write_offset += len(data)

    def pwrite(self, data, offset):
        data_len = len(data)
        written = 0
        while written < data_len:
            n = icbinn_pwrite(self.icbinn, self.fd,
                              data[written:written + ICBINN_MAXDATA],
                              offset + written)
            if n < 0:
                raise IcbinnError("error writing to icbinn file '%s': "
                                  "icbinn_pwrite failed" % self.path)
            written += n

    def pread(self, size, offset):
        try:
            return icbinn_pread(self.icbinn, self.fd, size, offset)
        except IOError as exc:
            raise IcbinnError("error reading icbinn file '%s': icbinn_pwrite "
                              "failed: %s" % (self.path, exc))

    def unlock(self):
        if icbinn_lock(self.icbinn, self.fd, ICBINN_LTYPE_UNLCK) < 0:
            raise IcbinnError("error unlocking icbinn file '%s': icbinn_lock "
                              "failed" % self.path)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

