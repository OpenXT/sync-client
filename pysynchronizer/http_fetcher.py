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

import os
import ssl
import urllib.request, urllib.error, urllib.parse

from .utils import disable_argo_inet, enable_argo_inet
from tempfile import NamedTemporaryFile, TemporaryFile
from .oxt_dbus import OXTDBusApi

class HttpFetcher:
    def __init__(self):
        db = OXTDBusApi.open_db()

        self.cacert = db.read("cacert")
        self.cert = db.read("device-cert")
        self.key = db.read("device-key")

    def __setup_cert__(self):
        if self.cert != "":
            with open("/tmp/id", "w+") as crt:
                crt.write("%s\n" % self.cert)
            with open("/tmp/key", "w+") as key:
                key.write("%s\n" % self.key)

    def __cleanup_cert__(self):
        try:
            os.remove("/tmp/id")
            os.remove("/tmp/key")
        except:
            pass

    def setup_ssl_context(self):
        sslcont = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        sslcont.minimum_version = ssl.TLSVersion.TLSv1_2
        if self.cacert != "":
            sslcont.load_verify_locations(cadata=self.cacert)

            self.__setup_cert__()

            sslcont.load_cert_chain(certfile="/tmp/id", keyfile="/tmp/key")

        return sslcont

    def fetch(self, url, offset=-1, size=-1):
        sslcont = self.setup_ssl_context()
        request = urllib.request.Request(url)

        # Add the header to specify the range to download.
        if offset != -1:
            if size != -1:
                request.add_header("range", "bytes=%d-%d" % (offset, offset + size - 1))
            else:
                request.add_header("range", "bytes=%d-" % offset)

        disable_argo_inet()
        response = urllib.request.urlopen(request, context=sslcont)

        # SSL Context has been used, clean up temporary cert files
        self.__cleanup_cert__()

        data = response.read()
        enable_argo_inet()

        # If a content-range header is present, partial retrieval worked.
        if "content-range" in response.headers:
            # The header contains the string 'bytes', followed by a space, then the
            # range in the format 'start-end', followed by a slash and then the total
            # size of the page (or an asterix if the total size is unknown). Lets get
            # the range and total size from this.
            bounds, total = response.headers['content-range'].split(' ')[-1].split('/')

            return bounds, total, data
        else:
            return "", "", data

    def stream(self, url, file_handle=None, offset=-1, chunk_size=1024):
        if file_handle == None:
            file_handle = TemporaryFile()

        sslcont = self.setup_ssl_context()
        request = urllib.request.Request(url)

        # Add the header to specify the range to download.
        if offset != -1:
            request.add_header("range", "bytes=%d-" % offset)

        disable_argo_inet()
        response = urllib.request.urlopen(request, context=sslcont)

        # SSL Context has been used, clean up temporary cert files
        self.__cleanup_cert__()

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            file_handle.write(chunk)

        enable_argo_inet()

        return file_handle
