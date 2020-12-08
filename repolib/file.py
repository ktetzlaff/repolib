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
    """ A class for handling source files (files which contain sources).

    Attributes:
        :ident str: the name of the file (less the extension).
        :comments dict[int, str]: A dict of comments in the file, with line
            numbers as the keys.
        :sources list[Source]: A list of DEB822-format sources in the file.
        :legacy_sources dict[int, DebLine]: A list of legacy-format sources and
            their line numbers.
        :source_path Path: The Path object for the file.
        :legacy bool: Whether the source contains legacy deb sources.
    """

    def __init__(self, ident: str = ''):
        """
        Arguments:
            :str ident: The filename of the file (without the extension)
        """
        self.ident: str = ident
        self.comments: Dict[int, str] = {}
        self.deb_sources: Dict[int, Source] = {}
        self.legacy_sources: Dict[int, DebLine] = {}
        self.source_path: Path
        self.legacy: bool = False
    
    def save_to_disk(self, save:bool = True):
        """ Saves the source to disk."""
        if not self.filename:
            raise SourceFileError('No filename to save to specified')
        full_path = util.get_sources_dir() / self.filename

        if save:
            try:
                with open(full_path, mode='w') as sources_file:
                    sources_file.write(self.generate_output())
            except PermissionError:
                bus = dbus.SystemBus()
                privileged_object = bus.get_object('org.pop_os.repolib', '/Repo')
                privileged_object.output_file_to_disk(self.filename, self.generate_output())
                privileged_object.exit()

    def sources(self):
        """ A generator that yields all sources.

        This returns all sources regardless of whether this is a legacy or a 
        new-format file.
        """
        if self.legacy:
            for i in self.legacy_sources:
                yield self.legacy_sources[i]
        
        else:
            for i in self.deb_sources:
                yield self.deb_sources[i]
    
    def get_source_by_ident(self, ident: str) -> Source:
        """ Get a source with the specified index.

        Arguments:
            :ident str: The ident of the source to get.
        
        Returns: 
            The :Source: object.
        """
        
        for source in self.sources():
            if source.ident == ident:
                return source
        
        raise SourceFileError(
            f'Could not find a source with ident `{ident}` in this file.`'
        )
        
    def get_source_by_index(self, index: int) -> Source:
        """ Get a source from the list of sources.

        Works regardless of whether the file is a legacy file or a DEB822 file, 
        or where in the file the source occurs. 

        Arguments:
            :index int: The index to get, with 0 being the first one in the 
                file. This will always correspond to the file_ident-`index`.
        
        Returns:
            The :Source: object.
        """        
        suffix = f'-{index}'
        if index == 0:
            suffix = ''
        
        try:
            return self.get_source_by_ident(f'{self.ident}{suffix}')
        
        except SourceFileError:
            raise SourceFileError(
                f'Could not find the specified index: {index}. Most likely the '
                'index is higher than the number of sources.'
            )
    
    def generate_output(self) -> str:
        """ Generate output for writing to a file on disk.

        Returns:
            :str: The formatted string data, with newlines specified as \n
        """
        items = {}
        output:str = ''
        
        for comment in self.comments:
            items[comment] = self.comments[comment]
        
        if self.legacy:
            for source in self.legacy_sources:
                items[source] = self.legacy_sources[source].make_debline()
        
        else:
            for source in self.deb_sources:
                items[source] = self.deb_sources[source]
        
        keys = sorted(items.keys())
        for item in keys:
            output += f'{items[item]}\n'
        
        return output

    def parse_file(self, ident: str = ''):
        """ Parses the contents of the file.

        Optionally use ident if one hasn't been supplied yet.

        Arguments:
            :ident str: The ident of the file. Does not override the main ident
                unless one hasn't been provided.
        """
        if not self.ident:
            self.ident = ident

        filestem: str = self.ident
        if ident:
            filestem: str

        if not filestem:
            raise SourceFileError('No filename provided to load.')

        self.source_path = util.get_source_path(filestem)

        if self.source_path.suffix == '.list':
            self.legacy = True

        with open(self.source_path, 'r') as source_file:
            source_list = source_file.readlines()

        item:int = 0
        raw_822: List[str] = []
        parsing_deb822: bool = False
        name:str = ''
        source_count: int = 0

        for line in source_list:

            if not parsing_deb822:
                commented = line.startswith('#')
                # Find commented out lines
                if commented:
                    # Exclude disabled legacy deblines.
                    name_line = line.startswith('## X-Repolib-Name: ')
                    valid_legacy = util.validate_debline(line.strip())
                    if not valid_legacy and not name_line:
                        self.comments[item] = line.strip()

                    elif valid_legacy:
                        if not self.legacy:
                            raise SourceFileError(
                                f'File {self.ident} is a Legacy file, but '
                                'contains DEB822-format sources. This is not '
                                'allowed. Please fix the file manually.'
                            )
                        source = DebLine(line)
                        if name:
                            source.name = name
                            if source.types == [util.AptSourceType.SOURCE]:
                                source.name = f'{name} Source code'
                        source.enabled = False
                        source.file = self
                        source.ident = self.ident
                        if source_count > 0:
                            source.ident = f'{self.ident}-{source_count}'
                            source.name += f' {source_count}'
                        source_count += 1
                        self.legacy_sources[item] = source

                    elif name_line:
                        name = ':'.join(line.split(':')[1:])
                        name = name.strip()

                # Find Legacy lines
                elif not commented:
                    if util.validate_debline(line.strip()):
                        if not self.legacy:
                            raise SourceFileError(
                                f'File {self.ident} is a Legacy file, but contains'
                                'DEB822-format sources. This is not allowed. Please '
                                'fix the file manually.'
                            )
                        source = DebLine(line)
                        if name:
                            source.name = name
                            if source.types == [util.AptSourceType.SOURCE]:
                                source.name = f'{name} Source code'
                        source.enabled = True
                        source.file = self
                        source.ident = self.ident
                        if source_count > 0:
                            source.ident = f'{self.ident}-{source_count}'
                            source.name += f' {source_count}'
                        source_count += 1
                        self.legacy_sources[item] = source

                # Empty lines count as comments
                if line.strip() == '':
                    self.comments[item] = line.strip()

                # Find Deb822 sources
                valid_keys = [
                    'X-Repolib-Name:',
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
                        if self.legacy:
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
                    source.load_from_list(raw_822[1:])
                    source.file = self
                    source.ident = self.ident
                    if source_count > 0:
                        source.ident = f'{self.ident}-{source_count}'
                        source.name += f' {source_count}'
                    source_count += 1
                    self.deb_sources[raw_822[0]] = source
                    raw_822 = []
                    item += 1
                    self.comments[item] = ''

                else:
                    raw_822.append(line.strip())

        if raw_822:
            parsing_deb822 = False
            source = Source()
            source.load_from_list(raw_822[1:])
            self.deb_sources[raw_822[0]] = source
            raw_822 = []
            item += 1
            self.comments[item] = ''

    @property 
    def filename(self):
        ext = 'sources'
        if self.legacy:
            ext = 'list'
        
        return f'{self.ident}.{ext}'
