#
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

import os.path

from .utils import is_valid_uuid, dbus_path_to_uuid, uuid_to_dbus_path
from .errors import ConnectionError, ConfigError
from .storage import Storage
from .oxt_dbus import OXTDBusApi

class XenMgr:
    def __init__(self):
        try:
            self.xenmgr = OXTDBusApi.open_xenmgr()
            self.host = OXTDBusApi.open_host()
        except Exception as err:
           raise ConnectionError('Failed to connect to XenMgr service') from err

    def get_current_release_and_build(self):
        """Get current XC release and build number from xenmgr"""
        build_info = self.host.get_property('build-info')
        return build_info['release'], build_info['build']

    # NB: RPC Proxy rules must be adjusted to allow
    def templates(self):
        """Returns a list of templates"""

        return self.xenmgr.list_templates()

    def vm_by_name(self):
        """Returns a dictionary of name:uuid pairs"""
        d = {}

        for path in self.xenmgr.list_vms():
            vm_uuid = dbus_path_to_uuid(path)
            name = OXTDBusApi.open_vm(path).get_property("name")
            d[name] = vm_uuid

        return d

    def vm_by_uuid(self):
        """Returns a dictionary of uuid:name pairs"""
        d = {}

        for path in self.xenmgr.list_vms():
            vm_uuid = dbus_path_to_uuid(path)
            name = OXTDBusApi.open_vm(path).get_property("name")
            d[vm_uuid] = name

        return d

    def find_vm(self, ref):
        """Takes a name or uuid and return a uuid if VM is found"""
        if is_valid_uuid(ref):
            vms = self.vm_by_uuid()
            if ref in vms:
                return ref
        else:
            vms = self.vm_by_name()
            if ref in vms:
                return vms[ref]

        return None

    def create_vm(self, template, json):
        """Creates a VM from template using JSON data returning object path"""
        try:
            unrestricted = OXTDBusApi.open_xenmgr_unrestricted()
        except Exception as err:
           raise ConnectionError('Failed to connect to XenMgr unrestricted service') from err

        return str(unrestricted.unrestricted_create_vm_with_template_and_json(template, json))

    def upgrade(self, url):
        """Takes a url, downloads it, and moves it for the upgrade manager to find"""
        storage = Storage()
        try:
            src = storage.stage_oxt_repo(url)
            storage.apply_oxt_repo(src)
            return True
        except:
            return False

class VM:
    def __init__(self, uuid=None):
        if is_valid_uuid(uuid):
            try:
                self.uuid = uuid
                self.path = uuid_to_dbus_path("/vm/", uuid)
                self.proxy_object = OXTDBusApi.open_vm(self.path)
                self.connected = True
            except Exception as err:
               raise ConnectionError('Failed to connect to XenMgr service') from err
        else:
            self.uuid=""
            self.connected = False

    def delete(self):
        """Attempts to delete the VM ref, returns True if successful"""
        if self.connected:
            self.proxy_object.delete()
            self.uuid = None
            self.proxy_object = None
            self.connected = False
            return True

        return False

    def get_property(self, name):
        """Retrieve a DBus object property, returning "" for when it does not exist"""
        try:
            value = self.proxy_object.get_property(name)
            return str(value)
        except:
            return ""

    def set_property(self, name, value):
        """Set the value of a DBus object property, returning value if successful"""
        try:
            self.proxy_object.set_property(name, value)
            return value
        except:
            return ""

    def domstore_get(self, key):
        """Retrieve a Domstore key, returning "" for when it does not exist"""
        try:
            value = self.proxy_object.get_domstore_key(key)
            return str(value)
        except:
            return ""

    def domstore_set(self, key, value):
        """Set the value of a Domstore key, returning value if successful"""
        try:
            self.proxy_object.set_domstore_key(key, value)
            return value
        except:
            return ""

    def disks(self):
        """Retrieve a list of VMDisk objects of the disk associate with the VM"""
        disks = []
        for disk_path in self.proxy_object.list_disks():
            disks.append(VMDisk(disk_path))

        return disks

    def find_disk(self, dsk_id):
        """Search if VM has an associated disk matching the disk identifier"""
        for disk in self.disks():
            values = [
                disk.id,
                str(disk.get_property("phys-path")),
                str(disk.get_property("virt-path")),
            ]
            if dsk_id in values:
                return disk

        return None

class VMDisk:
    def __init__(self, path):
            self.id = path.rsplit('/',1)[1]
            self.proxy_object = OXTDBusApi.open_disk(path)

    def get_property(self, name):
        """Retrieve a DBus object property, returning "" for when it does not exist"""
        return self.proxy_object.get_property(name)

    def set_property(self, name, value):
        """Set the value of a DBus object property, returning value if successful"""
        return self.proxy_object.set_property(name, value)

    def name(self):
        """Returns the phys-path as the "name" of the disk"""
        path = self.get_property('phys-path')

        # All disk paths should be absolute paths starting in /storage
        if not os.path.isabs(path):
            raise ConfigError("VMDisk(%s) has an invalid path (%s)" % (self.id, path))

        return os.path.basename(path)

    def replace(self, url):
        """Downloads a file located at "url" and overwrites the backing disk"""
        storage = Storage()
        try:
            return storage.download_disk(self.name(), url)
        except:
            return None
