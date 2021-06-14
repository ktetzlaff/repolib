#!/usr/bin/python3

"""
Copyright (c) 2019-2020, Ian Santopietro
All rights reserved.

This file is part of RepoLib.

RepoLib is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

RepoLib is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with RepoLib.  If not, see <https://www.gnu.org/licenses/>.
"""

import subprocess
import tempfile
from . import util

import dbus

GPG_KEYBOX_CMD = [
    'gpg',
    '-q',
    '--no-options',
    '--no-default-keyring',
    '--batch'
]

GPG_KEYRING_CMD = [
    'gpg',
    '-q',
    '--no-options',
    '--no-default-keyring'
]

class KeyError(Exception):
    """ Exception from a Key object."""

    def __init__(self, *args, code=1, **kwargs):
        """Exception with a Key object

        Arguments:
            code (:obj:`int`, optional, default=1): Exception error code.
    """
        super().__init__(*args, **kwargs)
        self.code = code

class Key:
    """ Represents a key file on the disk 

    Attributes:
        idnet (str): The ident of the file (should match the file's ident)
    """

    def __init__(self, ident:str) -> None:
        self.ident = ident
        self.keys: dict(str, bytes) = {}
    
    def save_to_disk(self) -> None:
        """ Saves the key files to disk. """
        keys_dir = util.get_keys_dir()
        written: list = []

        for old_file in keys_dir.glob(f'{self.ident}_*.gpg'):
            # Remove old files before starting
            old_file.unlink(missing_ok=True)

        for source in self.keys:
            key_filename = f'{self.ident}_{source}.gpg'
            key_path = keys_dir / key_filename
            key_data = self.keys[source]
            if not key_data:
                continue
            try:
                key_data.decode('UTF-8')
            except AttributeError:
                # Input was not bytes
                raise KeyError(
                    'Invalid input: did not recieve bytes.'
                )

            self._convert_key_file(key_path, key_data)
        
    def _convert_key_file(self, key_path:Path, key_data:bytes):
        """ Convert key files to the olf format, which APT uses."""
        
        # Import to the old format in a temporary file first.
        import_dest = Path('/tmp', key_path.name)

        # Convert to the correct format
        with tempfile.TemporaryDirectory() as temp_dir:
            import_cmd = GPG_KEYBOX_CMD.copy()
            import_cmd += [
                f'--keyring={import_dest}',
                '--homdir',
                temp_dir,
                '--import'
            ]
            export_cmd = GPG_KEYRING_CMD.copy()
            export_cmd += [
                f'--keyring={import_dest}',
                '--export'
            ]

            try:
                with open(key_path, mode='wb') as key_file:
                    subprocess.run(import_cmd, check=True, input=key_data)
                    subprocess.run(export_cmd, check=True, stdout=key_file)
            
            except PermissionError: # Fallback on PolicyKit
                subprocess.run(import_cmd, check=True, input=key_data)
                # Needs to be a string since python-dbus doesn't cast it
                export_cmd += [str(key_path)]
                
                bus = dbus.SystemBus()
                privileged_object = bus.get_object('org.pop_os.repolib', '/Repo')
                privileged_object.add_apt_signing_key(export_cmd)

    
    def add_key(self, source:str, key_data:bytes):
        """ Adds a key to this set.

        Arguments:
            source (str): The source ident for the key
            key_data (bytes): The binary data for the keyring for the source
        """

        if key_data: # Skip empty keys
            self.keys[source] = key_data
            