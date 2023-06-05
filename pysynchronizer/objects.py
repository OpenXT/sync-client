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

import dbus
import os.path

from .utils import is_valid_uuid, dbus_path_to_uuid, uuid_to_dbus_path
from .errors import Error, ConnectionError, ConfigError
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

    def get_release_and_build(self):
        """Get current XC release and build number from xenmgr"""
        return self.host.get_property('build-info')

    def config_get(self, key):
        value = self.xenmgr.propi.Get('com.citrix.xenclient.xenmgr.config', key)

        if isinstance(value, dbus.Boolean):
            return bool(value)

        if isinstance(value, dbus.Int32):
            return int(value)

        if isinstance(value, dbus.String):
            return str(value)

        return value

    def config_set(self, key, value):
        v = self.config_get(key)

        if isinstance(v, bool):
            if value.lower() == "true":
                value = True
            else:
                value = False
        elif isinstance(v, int):
            value = int(value)

        return str(self.xenmgr.propi.Set('com.citrix.xenclient.xenmgr.config', key, value))

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

    def list_argo_firewall_rules(self):
        """List Argo firewall rules"""
        return self.proxy_object.list_argo_firewall_rules()

    def add_argo_firewall_rule(self, rule):
        """Add firewall rule to Argo firewall"""
        try:
            self.proxy_object.add_argo_firewall_rule(rule)
            return rule
        except:
            return ""

    def delete_argo_firewall_rule(self, rule):
        """Delete firewall rule to Argo firewall"""
        try:
            self.proxy_object.delete_argo_firewall_rule(rule)
            return rule
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

class Usb:
    def __init__(self):
        try:
            self.usb = OXTDBusApi.open_usb()
        except Exception as err:
           raise ConnectionError('Failed to connect to USB service') from err

    # policy_set_rule: Set or create a specific USB rule
    #
    # rule_id(int): ID of the rule. If a rule exists with the ID, it will be replaced.
    # command(string): Command string of {allow, always, default, deny}
    # description(string): Description of the policy rule
    # vendor_id(string): USB vendor ID as headecimal, parsed by strtol (e.g. 8086)
    # device_id(string): USB product ID as hexadecimal, parsed by strtol (e.g. 1a2c)
    # serial_number(string): Serial number of the device, or an empty string to match any
    # sysattrs(dictionary): Dict of String:String sysattributes
    # udev_properties(dictionary): Dict of String:String udev properties
    # vm_uuid(string): VM UUID, or an empty string to match any VM
    def policy_set_rule(self, rule):
        return self.usb.policy_set_rule(rule.idx, rule.cmd, rule.desc, rule.vid, rule.pid, rule.serial, rule.sysattrs, rule.udev, rule.vm)

    # policy_set_rule_advanced: Set or create a specific USB rule, an advanced interface wrapper around policy_set_rule
    #
    # rule_id(int): ID of the rule. If a rule exists with the ID, it will be replaced.
    # command(string): Command string of {allow, always, default, deny}
    # description(string): Description of the policy rule
    # sysattrs(dictionary): Dict of String:String sysattributes
    # udev_properties(dictionary): Dict of String:String udev properties
    # vm_uuid(string): VM UUID, or an empty string to match any VM
    def policy_set_rule_advanced(self, rule):
        return self.usb.policy_set_rule_advanced(rule.idx, rule.cmd, rule.desc, rule.sysattrs, rule.udev, rule.vm)

    # policy_set_rule: Set or create a specific USB rule, interface wrapper around policy_set_rule
    #
    # rule_id(int): ID of the rule. If a rule exists with the ID, it will be replaced.
    # command(string): Command string of {allow, always, default, deny}
    # description(string): Description of the policy rule
    # vendor_id(string): USB vendor ID as headecimal, parsed by strtol (e.g. 8086)
    # device_id(string): USB product ID as hexadecimal, parsed by strtol (e.g. 1a2c)
    # serial_number(string): Serial number of the device, or an empty string to match any
    def policy_set_rule_basic(self, rule):
        return self.usb.policy_set_rule_basic(rule.idx, rule.cmd, rule.desc, rule.vid, rule.pid, rule.serial)

    # policy_get_rules: Get a set of all USB rules
    #   The set of rules in the format as an array of structs of:
    #    * int: Rule ID
    #    * string: Command
    #    * string: Description
    #    * string: Vendor ID as a String interpretable by strtol (e.g. 8086). An empty string or 0 indicates to match any device.
    #    * string: Product ID as a String interpretable by strtol (e.g. 8086). An empty string or 0 indicates to match any device.
    #    * string: Serial number of device. An empty string indicates to ignore serial number (match any).
    #    * [string]string: Dict of String:String sysattibutes
    #    * [string]string: Dict of String:String udev properties
    #    * string: VM UUID, or an empty string to match any VM
    def policy_get_rules(self):
        rules = []
        for rule in self.usb.policy_get_rules():
            rules.append(UsbPolicyRule(rule))

        return rules

    # policy_get_rule: Get a specific USB rule
    #
    # rule_id(int): Index position of the rule to get
    #
    # returns:
    #   string: Command string of {allow, always, default, deny}
    #   string: Description of the policy rule
    #   string: USB vendor ID as hexadecimal, parsed by strtol (e.g. 8086)
    #   string: USB product ID as hexadecimal, parsed by strtol (e.g. 1a2c)
    #   string: Serial number of the device, or an empty string to match any
    #   dictionary: Dict of String:String sysattributes
    #   dictionary: Dict of String:String udev properties
    #   string: VM UUID, or an empty string to match any VM
    def policy_get_rule(self, rule_id):
        values = [rule_id]

        values.extend(self.usb.policy_get_rule(rule_id))

        return UsbPolicyRule(values)

class UsbPolicyRule:

    def __init__(self, values):
        if values == None:
            self.idx = -1
            self.cmd = ""
            self.desc = ""
            self.vid = ""
            self.pid = ""
            self.serial = ""
            self.sysattrs = {}
            self.udev = {}
            self.vm = ""
            return

        if len(values) != 9:
            raise Error("Incorrect number of fields passed to create UsbPolicyRule")

        self.idx, self.cmd, self.desc, self.vid, self.pid, self.serial, self.sysattrs, self.udev, self.vm = values

    def __repr__(self):
        return "idx:%d cmd:%s desc:%s vid:%s pid:%s serial:%s sysattrs:%s udev:%s self.vm: %s" % \
            (self.idx, self.cmd, self.desc, self.vid, self.pid, self.serial, self.sysattrs, self.udev, self.vm)

    def summary_array(self):
        return [ self.idx, self.desc, self.vm ]

    # indent: indent char string
    # count: number of indent instances to prepend
    def show(self, indent, count):
        if indent == None or indent == '':
            indent = "    "

        if type(count) != int:
            count = 0

        prepend = indent * count

        print("%sRule Index:  %s" % (prepend, self.idx))
        print("%sCommand:     %s" % (prepend, self.cmd))
        print("%sDescription: %s" % (prepend, self.desc))
        print("%sVendor Id:   %s" % (prepend, self.vid))
        print("%sProduct Id:  %s" % (prepend, self.pid))
        print("%sSerial Num:  %s" % (prepend, self.serial))
        print("%sSystem Attrs:" % prepend)
        for k,v in self.sysattrs.items():
            print("%s%s: %s" % (prepend + indent, k, v))
        print("%sUdev Props:" % prepend)
        for k,v in self.udev.items():
            print("%s%s: %s" % (prepend + indent, k, v))
        print("%sVM UUID:     %s" % (prepend, self.vm))

    def set(self, key, value):
        dict_sep = ':'

        # Idx is an integer
        if key in ('idx'):
            self.__dict__[key] = int(value)
            return

        # Handle all the keys that have string values
        if key in ('cmd', 'desc', 'vid', 'pid', 'serial', 'vm'):
            self.__dict__[key] = value
            return

        # Handle keys that are dictionaries
        if key in ('sysattrs', 'udev'):
            if not key in self.__dict__:
                self.__dict__[key] = {}

            k, v = value.split(dict_sep)
            self.__dict__[key][k] = v
            return

        raise Error("Unknown USB Policy Rule attribute: %s", key)

class Net:
    def __init__(self):
        try:
            self.net = OXTDBusApi.open_net()
        except Exception as err:
           raise ConnectionError('Failed to connect to Network service') from err

    # create_network: Creates network using configuration.
    #     kind(string)
    #     id(int)
    #     config(string)
    #
    # returns:
    #     network(string)
    def create_network(self, kind, id, config):
        return self.net.create_network(kind, id, config)

    # list: Lists networks.
    #
    # returns:
    #     networks(array of dictionaries)
    def list(self):
        return self.net.list()

    def list_by_type(self, kind):
        networks = []

        for network in self.list():
            if str(network['type']) == kind:
                networks.append(network)

        return networks

    def get_mac(self, obj):
        for net in self.list():
            if str(net['object']) == obj:
                return str(net['mac'])

        return None
