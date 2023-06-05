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

import shlex

from cmd import Cmd
from os.path import split

from .errors import ConnectionError
from .objects import XenMgr, VM, Usb, UsbPolicyRule, Net
from .utils import column_print, dbus_path_to_uuid

class BaseCmd(Cmd):
    def __init__(self):
        super().__init__()

    def run(self, cmd_str=""):
        if cmd_str == "":
            self.cmdloop()
        else:
            self.onecmd(cmd_str)

    def do_exit(self, args):
        return -1

class SyncCmd(BaseCmd):
    def __init__(self, cmd_str=""):
        super().__init__()
        self.prompt = "sync> "

    def do_xenmgr(self, arg_str):
        try:
            XenMgrCmd().run(arg_str)
        except ConnectionError as err:
            print('Connection failed:\n\t%s\n' % err)
        except Exception as err:
            print('Unexpected exception:\n\t%s\n' % err)

    def do_upgrade(self, arg_str):
        self.do_xenmgr("upgrade " + arg_str)

    def do_vm(self, arg_str):
        args = arg_str.split()

        try:
            if args:
                vc = VmCmd(args[0])
                arg_str = " ".join(args[1:])
            else:
                vc = VmCmd("")
                arg_str = ""

            vc.run(arg_str)
        except ConnectionError  as err:
            print('Connection failed:\n\t%s\n' % err)
        except Exception as err:
            print('Unexpected exception:\n\t%s\n' % err)

    def do_usb(self, arg_str):
        try:
            UsbCmd().run(arg_str)
        except ConnectionError as err:
            print('Connection failed:\n\t%s\n' % err)
        except Exception as err:
            print('Unexpected exception:\n\t%s\n' % err)

    def do_net(self, arg_str):
        try:
            NetCmd().run(arg_str)
        except ConnectionError as err:
            print('Connection failed:\n\t%s\n' % err)
        except Exception as err:
            print('Unexpected exception:\n\t%s\n' % err)

class XenMgrCmd(BaseCmd):
    def __init__(self):
        super().__init__()

        self.prompt = "xemmgr> "
        self.xenmgr = XenMgr()

    def help_release(self):
        print('Usage: release\n')
        print('Prints Software build information')

    def do_release(self, arg_str):
        release = self.xenmgr.get_release_and_build()
        for key in release.keys():
            print("%s: %s" % (key, release[key]))

    def help_config(self):
        print('Usage: config {command}\n')
        print('Available commands:')
        print('  get {property}: get config property\n')
        print('  set {property}: get config property\n')

    def do_config(self, arg_str):
        args = arg_str.split()
        if len(args) < 2:
            self.help_config()
            return

        comm, args = args[0], args[1:]

        if comm == 'get':
            print('%s\n' % self.xenmgr.config_get(args[0]))

        if comm == 'set':
            self.xenmgr.config_set(args[0], args[1])

    def do_vms(self, arg_str):
        """Usage: vms\n\nList all VMs\n """
        rows = [ [
            "Name",
            "UUID",
        ] ]

        vm_list = self.xenmgr.vm_by_name()
        for name in vm_list:
            rows.append([name, vm_list[name]])

        column_print(rows)
        print('')

    def do_create_vm(self ,arg_str):
        """Usage: create_vm {template name} [path to json]"""

        tmplate, json_file = arg_str.split(None, 1)

        json = ""
        try:
            with open(json_file, 'r') as f:
                json = f.read()
        except OSError:
            print('  ERR: failure reading json file %s' % json_file)
            return

        path = self.xenmgr.create_vm(tmplate, json)

        print(dbus_path_to_uuid(path))

    def help_delete_vm(self):
        print('Usage: delete_vm [uuid|name]\n')
        print('Deletes VM matching either a uuid or a name\n')

    def do_delete_vm(self, arg_str):
        if not arg_str:
            self.help_delete_vm()
            return

        ref = arg_str.split()[0]

        vm_uuid = self.xenmgr.find_vm(ref)

        if vm_uuid:
            vm = VM(vm_uuid)
            vm.delete()
        else:
            print('unable to find vm: %s\n' % ref)

    def help_upgrade(self):
        print('Usage: upgrade "URL"\n')
        print('Upgrade OpenXT using repo file located at "URL"\n')

    def do_upgrade(self, arg_str):
        if not arg_str:
            self.help_upgrade()
            return

        if not self.xenmgr.upgrade(arg_str.split()[0]):
            print('upgrade failed\n')

class VmCmd(BaseCmd):
    def __init__(self, arg_str):
        super().__init__()

        self.prompt = "vm> "

        if arg_str:
            self.select_vm(arg_str.split()[0])

    def select_vm(self, vm_ref):
        vm_uuid = XenMgr().find_vm(vm_ref)
        if vm_uuid:
            self.vm = VM(vm_uuid)
            self.prompt = "vm[%s]> " % self.vm.get_property("name")
        else:
            self.vm = None
            self.prompt = "vm> "

    def help_select(self):
        print('Usage: select [uuid|name]\n')
        print('Changes the selected VM by matching uuid or name\n' )

    def do_select(self, arg_str):
        if not arg_str:
            self.help_select()
            return

        self.vm = None
        self.prompt = "vm> "

        vm_ref = arg_str.split()[0]

        self.select_vm(vm_ref)
        if self.vm is None:
            print('Failed to select VM %s\n' % vm_ref)

    def help_domstore(self):
        print('Usage: domstore get|set key [value]\n')
        print('Get or Set domstore "key"\n')

    def do_domstore(self, arg_str):
        args = arg_str.split()
        if not args:
            self.help_domstore()
            return

        cmd, args = args[0], args[1:]

        if cmd == "get":
            if not args:
                print('Usage: domstore get key\n')
                return
            key = args[0]
            print(self.vm.domstore_get(key))
            return

        if cmd == "set":
            if len(args) != 2:
                print('Usage: domstore set key value\n')
                return
            key, value = args[0], args[1]
            print(self.vm.domstore_set(key, value))
            return

        print('Unknown domstore command: %s\n' % cmd)

    def help_argo_firewall(self):
        print('Usage: argo_firewall list|[add|delete rule]\n')
        print('\tlist: List Argo firewall rules\n')
        print('\tadd|delete rule: Add/delete rule to Argo firewall\n')

    def do_argo_firewall(self, arg_str):
        args = arg_str.split()
        if not args:
            self.help_argo_firewall()
            return

        cmd, args = args[0], args[1:]

        if cmd == "list":
            col = [["Argo Rules"]]
            for rule in self.vm.list_argo_firewall_rules():
                col.append([rule])
            column_print(col)
            return

        if cmd == "add":
            if len(args) == 0:
                print('Usage: argo_firewall add rule\n')
                return
            rule = " ".join(args).replace('"', '').replace("'", "")
            print(self.vm.add_argo_firewall_rule(rule))
            return

        if cmd == "delete":
            if len(args) == 0:
                print('Usage: argo_firewall delete rule\n')
                return
            rule = " ".join(args).replace('"', '').replace("'", "")
            print(self.vm.delete_argo_firewall_rule(rule))
            return

        print('Unknown argo_firewall command: %s\n' % cmd)

    def do_disks(self, arg_str):
        """Usage: disks\n\nList all disks associated with selected VM\n """
        if self.vm is None:
            print('Please select a VM first\n')
            return

        rows = [ [
            "disk id",
            "phys-path",
            "virt-path",
            "enabled",
            "mode",
            "utilization-mb",
            "virtual-size-mb",
        ] ]
        for disk in self.vm.disks():
            row = [ disk.id ]
            row.append(disk.get_property('phys-path'))
            row.append(disk.get_property('virt-path'))
            row.append(str(disk.get_property('enabled')))
            row.append(disk.get_property('mode'))

            util_mb = int(disk.get_property('utilization-bytes')) // (1024 * 1024)
            row.append(str(util_mb))

            row.append(str(disk.get_property('virtual-size-mb')))

            rows.append(row)

        column_print(rows)
        print('')

    def help_disk(self):
        print('Usage: disk {command}\n')
        print('Available commands:')
        print('  replace "URL": replace backing disk image with that from "URL"\n')

    def do_disk(self, arg_str):
        args = arg_str.split()
        if len(args) < 2:
            self.help_disk()
            return

        disk_id, cmd, args = args[0], args[1], args[2:]

        disk = self.vm.find_disk(disk_id)

        if disk is None:
            print('Unknown disk: %s\n' % disk_id)
            return

        if cmd == "replace":
            url = args[0]
            if not url:
                print('Usage: disk replace "URL"\n')
                print('Download from "URL" and replace disk with image\n')
                return

            phy_path = self.disk.replace(url)
            if phy_path:
                print('Replaced %s\n' % phy_path)
            else:
                print('Failed to replace disk\n')

class UsbCmd(BaseCmd):
    def __init__(self):
        super().__init__()

        self.prompt = "usb> "
        self.usb = Usb()

    def do_list(self, arg_str):
        rows = [ [
            "rule id",
            "description",
            "vm uuid",
        ] ]

        for rule in self.usb.policy_get_rules():
            rows.append(rule.summary_array())

        column_print(rows)
        print('')

    def help_show(self):
        print('Usage: show [rule # | all]\n')
        print('Show the definition for the rule or for all rules')

    def do_show(self, arg_str):
        args = arg_str.split()
        if len(args) < 1:
            self.help_show()
            return

        if args[0].isdigit():
            rule_id = int(args[0])
            rule = self.usb.policy_get_rule(rule_id)
            rule.show('', 0)
            return

        if args[0] != "all":
            self.help_show()
            return

        for rule in self.usb.policy_get_rules():
            rule.show('', 0)
            print('')

    def do_set(self, arg_str):
        arg_sep = '='
        rule = UsbPolicyRule(None) # get an empty rule

        args = shlex.split(arg_str)
        for arg in args:
            key, value = arg.split(arg_sep)

            try:
                rule.set(key, value)
            except Exception as err:
                print("Error: %s" % err)
                return

        self.usb.policy_set_rule(rule)

class NetCmd(BaseCmd):
    def __init__(self):
        super().__init__()

        self.prompt = "net> "
        self.net = Net()

    def do_list(self, arg_str):
        rows = [ [
            "object",
            "label",
            "mac",
            "driver",
            "backend",
        ] ]

        for network in self.net.list():
            row = [network['object']]
            row.append(network['label'])
            row.append(network['mac'])
            row.append(network['driver'])
            row.append(network['backend_vm'])

            rows.append(row)

        column_print(rows)
        print('')

    def help_create(self):
        print('Usage: create network_id backing_uuid mac_address\n')
        print('Create network with a backing domain and mac address')

    def do_create(self, arg_str):
        args = arg_str.split()
        if len(args) != 1:
            self.help_create()
            return

        net_num, uuid, mac_addr = args[0], args[1], args[2]
        config = "uuid=%s,%s,,,," % (uuid, mac_addr)

        print("Created:")
        for net_type in ['wired', 'internal', 'any']:
            print("\t%s" % self.net.create_network(net_type, net_num, config))

    def help_mac_addr(self):
        print('Usage: mac_addr network_object\n')
        print('Retrieve the mac address for the given network')

    def do_mac_addr(self, arg_str):
        args = arg_str.split()
        if len(args) != 1:
            self.help_mac_addr()
            return

        print('%s\n' % self.net.get_mac(args[0]))

if __name__ == '__main__':
    import sys

    args = " ".join(sys.argv[1:])

    SyncCmd().run(args)
