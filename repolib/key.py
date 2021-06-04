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

from . import util

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

            with open(key_path, mode='wb') as key_file:
                key_file.write(key_data)
                written.append(source)
            