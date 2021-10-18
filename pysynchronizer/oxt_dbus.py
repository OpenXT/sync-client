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

from dbus import SystemBus, Interface
import collections

# DBus Services
XENMGR_SERVICE = 'com.citrix.xenclient.xenmgr'
DBD_SERVICE = 'com.citrix.xenclient.db'
USB_SERVICE = 'com.citrix.xenclient.usbdaemon'

# DBus Interfaces
XENMGR_INTF = 'com.citrix.xenclient.xenmgr'
XENMGR_UNRESTRICTED_INTF = 'com.citrix.xenclient.xenmgr.unrestricted'
XENMGR_HOST_INTF = 'com.citrix.xenclient.xenmgr.host'
XENMGR_VM_INTF = 'com.citrix.xenclient.xenmgr.vm'
DISK_INTF = 'com.citrix.xenclient.vmdisk'
INPUT_INTF = 'com.citrix.xenclient.input'
DB_INTF = 'com.citrix.xenclient.db'
USB_INTF = 'com.citrix.xenclient.usbdaemon'

class ServiceObject:
    def __init__(self, service, intf, obj_path):
        obj = SystemBus().get_object(service, obj_path)
        self.intf = Interface(obj, dbus_interface=intf)
        self.propi = Interface(obj, dbus_interface='org.freedesktop.DBus.Properties')

    def __getattr__(self, name):
        # if wrapped dbus intf has it, call it
        if isinstance(getattr(self.intf, name, None), collections.Callable):
            return getattr(self.intf, name)

    def get_property(self, key):
        """Lookup key on interface at path"""
        return self.propi.Get(self.intf.dbus_interface, key)

    def set_property(self, key, value):
        """Set key to value on interface at path"""
        return str(self.propi.Set(self.intf.dbus_interface, key, value))

class OXTDBusApi:
    @staticmethod
    def open_xenmgr():
        """Return a dbus proxy for the main xenmgr interface"""
        try:
            obj = ServiceObject(XENMGR_SERVICE, XENMGR_INTF, '/')
        except:
            obj = None
        return obj

    @staticmethod
    def open_xenmgr_unrestricted():
        """Return a dbus proxy for the main xenmgr unrestricted interface"""
        try:
            obj = ServiceObject(XENMGR_SERVICE, XENMGR_UNRESTRICTED_INTF, '/')
        except:
            obj = None
        return obj

    @staticmethod
    def open_host():
        """Return a dbus proxy for the main xenmgr host interface"""
        try:
            obj = ServiceObject(XENMGR_SERVICE, XENMGR_HOST_INTF, '/host')
        except:
            obj = None
        return obj

    @staticmethod
    def open_vm(vm_path):
        """Return a dbus proxy for the VM object"""
        try:
            obj = ServiceObject(XENMGR_SERVICE, XENMGR_VM_INTF, vm_path)
        except:
            obj = None
        return obj

    @staticmethod
    def open_disk(disk_path):
        """Return a proxy with the disk path interface for disk_path"""
        try:
            obj = ServiceObject(XENMGR_SERVICE, DISK_INTF, disk_path)
        except:
            obj = None
        return obj

    @staticmethod
    def open_input_daemon():
        """Return a dbus proxy for the input daemon interface"""
        try:
            obj = ServiceObject(XENMGR_SERVICE, INPUT_INTF, '/')
        except:
            obj = None
        return obj

    @staticmethod
    def open_db():
        """Return a dbus proxy for the database (i.e. domstore) interface"""
        try:
            obj = ServiceObject(DBD_SERVICE, DB_INTF, '/')
        except:
            obj = None
        return obj

    @staticmethod
    def open_usb():
        """Return a dbus proxy for the database (i.e. domstore) interface"""
        try:
            obj = ServiceObject(USB_SERVICE, USB_INTF, '/')
        except:
            obj = None
        return obj
