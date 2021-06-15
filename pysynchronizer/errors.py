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

class Error(Exception):
    """Base class for other exceptions"""

class ConfigError(Error):
    """sync-client configuration is not valid"""
    exit_code = 4

class ConnectionError(Error):
    """sync-client API connection error"""
    exit_code = 5

class HTTPError(Error):
    """An error occurred while contacting the server"""
    exit_code = 6

class ServerVersionError(Error):
    """The server version is not supported"""
    exit_code = 7

class TargetStateError(Error):
    """The target state is not valid"""
    exit_code = 8

class PlatformError(Error):
    """An error occurred while updating the platform to the target state"""
    exit_code = 9

class IcbinnConnectError(Error):
    """Unable to connect to icbinn server"""
    exit_code = 10

class IcbinnError(Error):
    """Other icbinn error"""
    exit_code = 11

class MissingDownload(Error):
    """stat failed on a file after download"""
    exit_code = 12

class InsufficientIcbinnPaths(Error):
    """We did not get the two icbinn paths we needed"""
    exit_code = 13

class DiskMissing(Error):
    """The file for a disk we are responsible for is missing"""
    exit_code = 14

class KeyMismatch(Error):
    """We downloaded a VHD with a key that did not match the key that came with it"""
    exit_code = 15

class EncryptionKeyLengthWrong(Error):
    """We got a key length that we did not expect"""
    exit_code = 16

class VhdUtilSnapshotFailed(Error):
    """Running vhd-util snapshot did not create a file"""
    exit_code = 17
