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

This is a library for handling files which contain sources.
"""

from typing import Dict, List, Tuple
from pathlib import Path

import dbus

from .source import Source
from .deb import DebLine
from . import util

class SourceFileError(Exception):
    """ Exception from a source file."""

    def __init__(self, *args, code:int = 1, **kwargs):
        """Exception with a source file

        Arguments:
            :code int, optional, default=1: Exception error code.
    """
        super().__init__(*args, **kwargs)
        self.code: int = code
        
class SourceFile:
    """ A class for handling source files on disk.
    
    Attributes:
        :ident str: The name of the file (without the extension)
        :form str: The format of the file (either `deb` or `legacy`)
    """
    def __init__(self, ident: str = ''):
        self.ident = ident
        self.comments: Dict[int, str] = {}
        self.format: str = self.detect_file_format()
        self.source_path: Path = util.get_sources_dir() / f'{self.ident}.{self.format}'
        self.items = ['## Added/managed by Repolib', '']
        self.sources: dict = {}
        self.key_file: Path = util.get_keys_dir() / f'{self.ident}.gpg'
    
    def detect_file_format(self) -> str:
        """ Detect the format of the file based on the file extension.

        Returns:
            str: `sources` if the file is a DEB822 file, `list` if it is a legacy
                .list file, or `none` if the file doesn't exist (or has an
                invalid extension).
        """
        sources_dir = util.get_sources_dir()
        self.path = sources_dir / f'{self.ident}.sources'
        
        # If this is a sources file, return here
        if self.path.exists():
            return 'sources'

        self.path = sources_dir / f'{self.ident}.list'

        # If this is a list file, return here
        if self.path.exists():
            return 'list'
        
        # If the file doesn't exsit, return none
        return 'none' 
    
    def save_to_disk(self, save: bool = True, skip_keys: bool = False):
        """ Saves the source to disk."""
        if not self.ident:
            raise SourceFileError('No Filename to save was specified.')

        if len(self.sources.values()) > 0:
            for source in self.sources.values():
                if save and not skip_keys:
                    source.make_key()
            
            if save:
                try:
                    with open(self.source_path, mode='w') as sources_file:
                        sources_file.write(self.generate_output())
                
                except PermissionError:
                    bus = dbus.SystemBus()
                    privileged_object = bus.get_object('org.pop_os.repolib', '/Repo')
                    privileged_object.output_file_to_disk(
                        f'{self.ident}.{self.format}',
                        self.generate_output()
                    )
            else:
                print(self.generate_output())
        else:
            try:
                save_path = util.get_sources_dir() / f'{self.source_path.stem}.save'
                save_path.unlink(missing_ok=True)
                self.source_path.unlink()
            except PermissionError:
                bus = dbus.SystemBus()
                privileged_object = bus.get_object('org.pop_os.repolib', '/Repo')
                privileged_object.delete_source_file(self.source_path.name)

    def convert_formats(self):
        """ Convert the source file from its current format to the opposite."""
        try:
            self.source_path.unlink()
        except PermissionError:
            bus = dbus.SystemBus()
            privileged_object = bus.get_object('org.pop_os.repolib', '/Repo')
            privileged_object.delete_source(
                f"{self.ident}.{self.format}",
                'None'
            )
        
        if self.format == 'list':
            self.format = 'sources'
        elif self.format == 'sources':
            self.format = 'list'
        
        self.source_path = util.get_sources_dir() / f'{self.ident}.{self.format}'
        self.save_to_disk()
    
    def generate_output(self) -> str:
        """ Generate a str with the output of the source (the file contents)"""
        output = ''

        for item in self.items:
            try:
                if self.format == 'list':
                    output += f'{item.make_debline()}\n'
                else:
                    output += f'{item.save_output()}\n'
            except AttributeError:
                output += f'{item}\n'
        
        return output
    
    def _line_to_source(self, line:str):
        """ Convert a deb line to a source object."""
        source = Source()
        source.parse_debline(line)
        source.file = self

        if not source.name:
            if source.types == ['deb']:
                source.name = f'{self.ident} Binary'
            elif source.types == ['deb-src']:
                source.name = f'{self.ident} Source Code'
        
        if not source.ident:
            if source.types == ['deb']:
                source.ident = f'binary'
            elif source.types == ['deb-src']:
                source.ident = f'source'
    
    def load_deb_sources(self, ident: str = ''):
        """ Parses the contents of the file.

        Optionally use ident if one hasn't been supplied yet.

        Arguments:
            :ident str: The ident of the file. Does not override the main ident
                unless one hasn't been provided.
        """
        self.items = []
        self.sources = {}

        if not self.ident:
            self.ident = ident

        filestem: str = self.ident
        if ident:
            filestem: str

        if not filestem:
            raise SourceFileError(f'No filename provided to load: {self.ident}')

        with open(self.source_path, 'r') as source_file:
            source_list = source_file.readlines()

        item:int = 0
        raw_822: List[str] = []
        parsing_deb822: bool = False
        name:str = ''

        for line in source_list:

            if not parsing_deb822:
                commented = line.startswith('#')
                # Find commented out lines
                if commented:
                    # Exclude disabled legacy deblines.
                    name_line = line.startswith('## X-Repolib-Name: ')
                    valid_legacy = util.validate_debline(line.strip())
                    if not valid_legacy and not name_line:
                        self.items.append(line.strip())

                    elif valid_legacy:
                        if self.format != 'list':
                            raise SourceFileError(
                                f'File {self.ident} is a Legacy file, but '
                                'contains DEB822-format sources. This is not '
                                'allowed. Please fix the file manually.'
                            )
                        source = Source()
                        source.parse_debline(line)
                        source.file = self
                        

                    elif name_line:
                        name = ':'.join(line.split(':')[1:])
                        name = name.strip()

                # Find Legacy lines
                elif not commented:
                    if util.validate_debline(line.strip()):
                        if self.format != 'list':
                            raise SourceFileError(
                                f'File {self.ident} is a Legacy file, but contains'
                                'DEB822-format sources. This is not allowed. Please '
                                'fix the file manually.'
                            )
                        source = Source()
                        source.parse_debline(line)
                        if name:
                            if not source.name:
                                source.name = name
                                if source.types == [util.AptSourceType.SOURCE]:
                                    source.name = f'{name} Source code'
                        source.enabled = True
                        source.file = self
                        source.ident = f'{self.ident}-{self.source_count}'
                        self.sources[self.source_count] = source
                        self.items.append(source)

                # Empty lines count as comments
                if line.strip() == '':
                    self.items.append('')

                # Find Deb822 sources
                valid_keys = [
                    'X-Repolib-Name:',
                    'X-Repolib-Ident:',
                    'X-Repolib-Default-Mirror:',
                    'Enabled:',
                    'Types:',
                    'URIs:',
                    'Suites:',
                    'Components:',
                    'Architectures:',
                    'Languages:',
                    'Targets:',
                    'PDiffs:',
                    'By-Hash:',
                    'Allow-Insecure:',
                    'Allow-Weak:',
                    'Allow-Downgrade-To-Insecure:',
                    'Trusted:',
                    'Signed-By:',
                    'Check-Valid-Until:',
                    'Valid-Until-Min:',
                    'Valid-Until-Max:',
                ]
                # Valid DEB822 sources may start with any key.
                for key in valid_keys:
                    if line.startswith(key):
                        if self.format == 'list':
                            raise SourceFileError(
                                f'File {self.ident} is a DEB822-format file, but '
                                'contains legacy sources. This is not allowed. '
                                'Please fix the file manually.'
                            )
                        parsing_deb822 = True
                        raw_822.append(item)
                        raw_822.append(line.strip())
                        continue

                item += 1

            elif parsing_deb822:
                # 822 Sources are ended with a blank line
                if line.strip() == '':
                    parsing_deb822 = False
                    source = Source()
                    source.load_from_data(raw_822[1:])
                    source.file = self
                    source.ident = f'{self.ident}-{self.source_count}'
                    self.sources[self.source_count] = source
                    self.items.append(source)
                    raw_822 = []
                    item += 1
                    self.items.append('')

                else:
                    raw_822.append(line.strip())

        if raw_822:
            parsing_deb822 = False
            source = Source()
            source.load_from_data(raw_822[1:])
            source.ident = f'{self.ident}-{self.source_count}'
            self.sources[self.source_count] = source
            self.items.append(source)
            raw_822 = []
            item += 1
            self.items.append('')

    def get_source_index(self, source: Source = None, ident:str = None) -> int:
        """ Get the index of a source, given the actual source or the ident.

        Arguments:
            :source Source: The source object (can be any Source subclass)
            :ident str: The ident of the source to remove.
        
        Returns:
            :int: The index of the source, or -1 if the source wasn't found.
        """
        if source:
            for i in self.sources:
                if self.sources[i] == source:
                    return i
        
        if ident:
            for i in self.sources:
                if self.sources[i].ident == ident:
                    return i
        
        return -1
                

    def add_source(self, source: Source): 
        """ Adds a source to this file.

        Arguments:
            :source Source: The source to add (Can be any source subclass)            
        """
        source.ident = f'{self.ident}-{self.source_count}'
        self.items.append(source)
        self.sources[self.source_count] = source
        source.file = self
    
    def remove_source(self, index: int, errors: bool = False):
        """ Remove a source from this file.

        Arguments:
            :index int: The index of the source to remove
        """
        remove_source = self.sources[index]
        self.items.remove(remove_source)
        self.sources.pop(index, None)
        remove_source.delete_key()
    
    @property
    def source_count(self) -> int:
        """int: return the number of sources."""
        return len(self.sources.values())

    @property
    def ident(self) -> str:
        """str: the name of the file on disk."""
        if not self._ident:
            try:
                self._ident = self.sources[0]
            except KeyError:
                raise SourceFileError('SourceFile has no ident assigned.')
        return self._ident
    
    @ident.setter
    def ident(self, ident):
        """ Also re-detect the file format."""
        self._ident = ident
        self.format = self.detect_file_format()
    
    @property
    def format(self) -> str:
        """str: the format of the file, either `list`, `sources`, or `none`"""
        if not self._format:
            self._format = self.detect_file_format()
        return self._format
    
    @format.setter
    def format(self, format):
        """ Need to update path when format changes"""
        self.source_path = util.get_sources_dir() / f'{self.ident}.{format}'
        self._format = format
