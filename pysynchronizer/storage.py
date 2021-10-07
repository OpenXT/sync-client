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


import uuid

from os import O_CREAT, O_WRONLY
from os.path import join, split
from .http_fetcher import HttpFetcher
from .icbinn import Icbinn

DOWNLOAD_BLOCK_SIZE = 512 * 1024
REPO_DOWNLOAD_DIR = 'repo-download'
REPO_HANDOVER_DIR = 'repo'
DISKS_DIR = 'disks'

class Storage:
    def __init__(self, block_size=DOWNLOAD_BLOCK_SIZE):
        self.storage = Icbinn().storage
        self.block_size = block_size

    def fetch_using_partial(self, url, file_path):
        partial = file_path + '.partial'
        offset = 0
        fetcher = HttpFetcher()

        if self.storage.exists(partial):
            offset = self.storage.stat(partial)[0]

        partial_handle = self.storage.open(partial, O_CREAT | O_WRONLY)
        if offset != 0:
            partial_handle.seek(offset)

        fetcher.stream(url, partial_handle, offset, self.block_size)

        partial_handle.close()

        if self.storage.exists(file_path):
            self.storage.unlink(file_path)

        self.storage.rename(partial, file_path)

    def download_disk(self, disk_name, url):
        disk_file = join(DISKS_DIR, disk_name)

        self.fetch_using_partial(url, disk_file)

        return disk_file

    def list_disks(self):
        return self.storage.listdir(DISKS_DIR)

    def stage_oxt_repo(self, url):
        repo_uuid = uuid.uuid5(uuid.NAMESPACE_URL, url)
        repo_name = str(repo_uuid) + '.tar'

        self.storage.makedirs(REPO_DOWNLOAD_DIR)

        download_file = join(REPO_DOWNLOAD_DIR, repo_name)

        self.fetch_using_partial(url, download_file)

        return repo_name

    def list_repo_stage(self):
        return self.storage.listdir(REPO_DOWNLOAD_DIR)

    def apply_oxt_repo(self, name):
        src = join(REPO_DOWNLOAD_DIR, name)
        dst = join(REPO_HANDOVER_DIR, name)

        if self.storage.exists(dst):
            return False

        self.storage.makedirs(REPO_HANDOVER_DIR)
        self.storage.rename(src, dst)
