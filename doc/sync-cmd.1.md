% SYNC-CMD(1) Version 1.0 | Synchronizer Command Shell

NAME
====

**sync-cmd** — Command shell for administrating an OpenXT system.

SYNOPSIS
========

**sync-cmd** \[**command** [***arguments***]]

DESCRIPTION
===========

Provides a command shell with an acceptable level of remote administrative
capabilities.

BUILTIN COMMANDS
=================

xenmgr
------

Used to interact and manage xenmgr process.

release
: Print the OpenXT release information for the current running software.

config
: Provides two subcommands to interact with xenmgr config.

|        ***subcommands:***
|        
|        get _property_
|            Retrieves _property_ from xenmgr config.
|        
|        set _property_ _value_
|            Stores _value_ in _property_ of xenmgr config.

vms
: List all VMs on the system.

create_vm _template name_ [_json file_]
: Create a VM using the specified template and populate its config using the
optional JSON file.

delete_vm _identifier_
: Delete a VM identified by identifier, where identifier may be the UUID or
the name of the VM.

upgrade _URL_
: Initiate a platform upgrade using the OTA file located at _URL_.

reboot
: Reboot the system.

shutdown
: Shutdown the system.

upgrade
-------

Alias to **xenmgr upgrade**

vm [_identifier_]
--

Used to interact and manage VM instances.

select [_identifier_]
: In interactive mode, this selects the VM to act upon for subsequent commands.

domstore
: Provides two subcommands to configure a domains domstore.

|        ***subcommands:***
|        
|        get _key_
|            Retrieves _key_ from domstore.
|        
|        set _key_ _value_
|            Stores _value_ for _key_ in domstore.

argo_firewall
: Provides three subcommands to configure a domains argo firewall.

|        ***subcommands:***
|        
|        list
|            Retrieves all the firewall rules.
|        
|        add _rule_
|            Add _rule_ to the firewall.
|        
|        delete _rule_
|            If _rule_ matches an existing rule, delete it.

disks
: List all disks associated with the VM.

disk
: Provides subcommands to manage a disk associated with the VM.

|        ***subcommands:***
|        
|        replace _URL_
|            Replace the backing disk image with one downloaded from _URL_.

usb
---

Used to manage the USB policy.

list
: List all the rules in the USB policy.

show _num_ | _all_
: Display _num_ rule in the USB policy, _all_ will display all rules.

set _rule_
: Set a rule in the USB Policy as described by _rule_.

remove _num_
: Remove rule number _num_ from the USB policy.

net
---

Used to manage the configuration for network instances.

list
: List all network instances defined for the system.

create _id_ _uuid_ _mac_
: Create a new network instance configured as follows,

|        _id_: network identifier
|        _uuid_: UUID of the backing domain for the network
|        _mac_: MAC address for the network bridge

mac_addr _obj_
: Retrieve the MAC address for the network as identified by network object _obj_.

NOTES
=====

The sync-cmd functions by communicating with various system daemons using DBus over Argo. All DBus messages entering
the control domain come through the rpc-proxy firewall. The rpc-proxy firewall provides a means to filter messages
based on source, destination, interface and member being invoked. A portion of sync-cmd functionality requires additional
rpc-proxy firewall rules beyond those included in a vanilla build of OpenXT.

Net Command Rules
-----------------

To enable functionality of the **net** command, rules to allow the following are required:

```
allow dom-type syncvm destination com.citrix.xenclient.networkdaemon interface org.freedesktop.DBus.Introspectable member Introspect
allow dom-type syncvm destination com.citrix.xenclient.networkdaemon interface com.citrix.xenclient.networkdaemon member list
allow dom-type syncvm destination com.citrix.xenclient.networkdaemon interface com.citrix.xenclient.networkdaemon member create_network
```

USB Command Rules
-----------------

To enable functionality of the **usb** command, rules to allow the following are required:

```
allow dom-type syncvm destination com.citrix.xenclient.usbdaemon interface org.freedesktop.DBus.Introspectable member Introspect
allow dom-type syncvm destination com.citrix.xenclient.usbdaemon interface com.citrix.xenclient.usbdaemon member policy_list
allow dom-type syncvm destination com.citrix.xenclient.usbdaemon interface com.citrix.xenclient.usbdaemon member policy_get_rules
allow dom-type syncvm destination com.citrix.xenclient.usbdaemon interface com.citrix.xenclient.usbdaemon member policy_set_rule
allow dom-type syncvm destination com.citrix.xenclient.usbdaemon interface com.citrix.xenclient.usbdaemon member policy_set_rule_basic
allow dom-type syncvm destination com.citrix.xenclient.usbdaemon interface com.citrix.xenclient.usbdaemon member policy_set_rule_advanced
allow dom-type syncvm destination com.citrix.xenclient.usbdaemon interface com.citrix.xenclient.usbdaemon member policy_remove_rule
```

BUGS
====

See GitHub Issues: <https://github.com/OpenXT/sync-client/issues>

AUTHOR
======

OpenXT Developers <openxt@googlegroups.com>

SEE ALSO
========

**sync-cmd(1)**
