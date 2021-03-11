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

# class SourceFile:
#     """ A class for handling source files (files which contain sources).

#     Attributes:
#         :ident str: the name of the file (less the extension).
#         :comments dict[int, str]: A dict of comments in the file, with line
#             numbers as the keys.
#         :sources list[Source]: A list of DEB822-format sources in the file.
#         :legacy_sources dict[int, DebLine]: A list of legacy-format sources and
#             their line numbers.
#         :source_path Path: The Path object for the file.
#         :legacy bool: Whether the source contains legacy deb sources.
#     """

#     def __init__(self, ident: str = '', filename=''):
#         """
#         Arguments:
#             :str ident: The filename of the file (without the extension)
#             :str filename: The filename of the file (with the extension)
        
#             Note: If both an ident and a filename are provided, the ident takes 
#             precedence.
#         """
#         if filename:
#             filename = filename.replace('.list', '')
#             filename = filename.replace('.sources', '')
#             self.ident = filename
#         if ident:
#             self.ident: str = ident
#         self.comments: Dict[int, str] = {}
#         self.deb_sources: Dict[int, Source] = {}
#         self.legacy_sources: Dict[int, DebLine] = {}
#         self.source_path: Path
#         self.legacy: bool = False
    
#     def save_to_disk(self, save:bool = True):
#         """ Saves the source to disk."""
#         if not self.filename:
#             raise SourceFileError('No filename to save to specified')
#         full_path = util.get_sources_dir() / self.filename

#         if save:
#             try:
#                 with open(full_path, mode='w') as sources_file:
#                     sources_file.write(self.generate_output())
#             except PermissionError:
#                 privileged_object = bus.get_object('org.pop_os.repolib', '/Repo')
#                 privileged_object.output_file_to_disk(self.filename, self.generate_output())
#                 privileged_object.exit()

#     def all_sources(self):
#         """ A generator that yields all sources.

#         This returns all sources regardless of whether this is a legacy or a 
#         new-format file. If this is a single-source (one repo, possibly with 
#         source code), then only returns self.
#         """
#         if self.single_source:
#             yield self

#         if self.legacy:
#             for i in self.legacy_sources:
#                 yield self.legacy_sources[i]
        
#         else:
#             for i in self.deb_sources:
#                 yield self.deb_sources[i]
    
#     def get_source_by_ident(self, ident: str) -> Source:
#         """ Get a source with the specified index.

#         Arguments:
#             :ident str: The ident of the source to get.
        
#         Returns: 
#             The :Source: object.
#         """
        
#         for source in self.all_sources():
#             if source.ident == ident:
#                 return source
        
#         raise SourceFileError(
#             f'Could not find a source with ident `{ident}` in this file.`'
#         )
        
#     def get_source_by_index(self, index: int) -> Source:
#         """ Get a source from the list of sources.

#         Works regardless of whether the file is a legacy file or a DEB822 file, 
#         or where in the file the source occurs. 

#         Arguments:
#             :index int: The index to get, with 0 being the first one in the 
#                 file. This will always correspond to the file_ident-`index`.
        
#         Returns:
#             The :Source: object.
#         """        
#         suffix = f'-{index}'
#         if index == 0:
#             suffix = ''
        
#         try:
#             return self.get_source_by_ident(f'{self.ident}{suffix}')
        
#         except SourceFileError:
#             raise SourceFileError(
#                 f'Could not find the specified index: {index}. Most likely the '
#                 'index is higher than the number of sources.'
#             )
    
#     def generate_output(self) -> str:
#         """ Generate output for writing to a file on disk.

#         Returns:
#             :str: The formatted string data, with newlines specified as \n
#         """
#         items = {}
#         output:str = ''
        
#         for comment in self.comments:
#             items[comment] = self.comments[comment]
        
#         if self.legacy:
#             for source in self.legacy_sources:
#                 items[source] = self.legacy_sources[source].make_debline()
        
#         else:
#             for source in self.deb_sources:
#                 items[source] = self.deb_sources[source]
        
#         keys = sorted(items.keys())
#         for item in keys:
#             output += f'{items[item]}\n'
        
#         return output

#     def parse_file(self, ident: str = ''):
#         """ Parses the contents of the file.

#         Optionally use ident if one hasn't been supplied yet.

#         Arguments:
#             :ident str: The ident of the file. Does not override the main ident
#                 unless one hasn't been provided.
#         """
#         if not self.ident:
#             self.ident = ident

#         filestem: str = self.ident
#         if ident:
#             filestem: str

#         if not filestem:
#             raise SourceFileError(f'No filename provided to load: {self.ident}')

#         self.source_path = util.get_source_path(filestem)

#         if self.source_path.suffix == '.list':
#             self.legacy = True

#         with open(self.source_path, 'r') as source_file:
#             source_list = source_file.readlines()

#         item:int = 0
#         raw_822: List[str] = []
#         parsing_deb822: bool = False
#         name:str = ''
#         source_count: int = 0

#         for line in source_list:

#             if not parsing_deb822:
#                 commented = line.startswith('#')
#                 # Find commented out lines
#                 if commented:
#                     # Exclude disabled legacy deblines.
#                     name_line = line.startswith('## X-Repolib-Name: ')
#                     valid_legacy = util.validate_debline(line.strip())
#                     if not valid_legacy and not name_line:
#                         self.comments[item] = line.strip()

#                     elif valid_legacy:
#                         if not self.legacy:
#                             raise SourceFileError(
#                                 f'File {self.ident} is a Legacy file, but '
#                                 'contains DEB822-format sources. This is not '
#                                 'allowed. Please fix the file manually.'
#                             )
#                         source = Source()
#                         source.parse_debline(line)
#                         if name:
#                             source.name = name
#                             if source.types == [util.AptSourceType.SOURCE]:
#                                 source.name = f'{name} Source code'
#                         source.enabled = False
#                         source.file = self
#                         source.ident = self.ident
#                         if source_count > 0:
#                             source.ident = f'{self.ident}-{source_count}'
#                             source.name += f' {source_count}'
#                         source_count += 1
#                         self.legacy_sources[item] = source

#                     elif name_line:
#                         name = ':'.join(line.split(':')[1:])
#                         name = name.strip()

#                 # Find Legacy lines
#                 elif not commented:
#                     if util.validate_debline(line.strip()):
#                         if not self.legacy:
#                             raise SourceFileError(
#                                 f'File {self.ident} is a Legacy file, but contains'
#                                 'DEB822-format sources. This is not allowed. Please '
#                                 'fix the file manually.'
#                             )
#                         source = Source()
#                         source.parse_debline(line)
#                         if name:
#                             source.name = name
#                             if source.types == [util.AptSourceType.SOURCE]:
#                                 source.name = f'{name} Source code'
#                         source.enabled = True
#                         source.file = self
#                         source.ident = self.ident
#                         if source_count > 0:
#                             source.ident = f'{self.ident}-{source_count}'
#                             source.name += f' {source_count}'
#                         source_count += 1
#                         self.legacy_sources[item] = source

#                 # Empty lines count as comments
#                 if line.strip() == '':
#                     self.comments[item] = line.strip()

#                 # Find Deb822 sources
#                 valid_keys = [
#                     'X-Repolib-Name:',
#                     'X-Repolib-Default-Mirror:',
#                     'Enabled:',
#                     'Types:',
#                     'URIs:',
#                     'Suites:',
#                     'Components:',
#                     'Architectures:',
#                     'Languages:',
#                     'Targets:',
#                     'PDiffs:',
#                     'By-Hash:',
#                     'Allow-Insecure:',
#                     'Allow-Weak:',
#                     'Allow-Downgrade-To-Insecure:',
#                     'Trusted:',
#                     'Signed-By:',
#                     'Check-Valid-Until:',
#                     'Valid-Until-Min:',
#                     'Valid-Until-Max:',
#                 ]
#                 # Valid DEB822 sources may start with any key.
#                 for key in valid_keys:
#                     if line.startswith(key):
#                         if self.legacy:
#                             raise SourceFileError(
#                                 f'File {self.ident} is a DEB822-format file, but '
#                                 'contains legacy sources. This is not allowed. '
#                                 'Please fix the file manually.'
#                             )
#                         parsing_deb822 = True
#                         raw_822.append(item)
#                         raw_822.append(line.strip())
#                         continue

#                 item += 1

#             elif parsing_deb822:
#                 # 822 Sources are ended with a blank line
#                 if line.strip() == '':
#                     parsing_deb822 = False
#                     source = Source()
#                     source.load_from_data(raw_822[1:])
#                     source.file = self
#                     source.ident = self.ident
#                     if source_count > 0:
#                         source.ident = f'{self.ident}-{source_count}'
#                         source.name += f' {source_count}'
#                     source_count += 1
#                     self.deb_sources[raw_822[0]] = source
#                     raw_822 = []
#                     item += 1
#                     self.comments[item] = ''

#                 else:
#                     raw_822.append(line.strip())

#         if raw_822:
#             parsing_deb822 = False
#             source = Source()
#             source.load_from_data(raw_822[1:])
#             self.deb_sources[raw_822[0]] = source
#             raw_822 = []
#             item += 1
#             self.comments[item] = ''
        
#         if self.single_source:
#             self.file = self

#     # @property
#     # def oneline_format(self) -> bool:
#     #     """bool: Whether this is a one-line format file or not."""
#     #     return self._oneline_format
    
#     # @oneline_format.setter
#     # def oneline_format(self, form):
#     #     e_values = [
#     #         True,
#     #         'True',
#     #         'true',
#     #         'Yes',
#     #         'yes',
#     #         'YES',
#     #         'y',
#     #         'Y',
#     #         1
#     #     ]
        
#     #     if form in e_values:
#     #         self._oneline_format = True
#     #     else:
#     #         self._oneline_format = False

#     # @property 
#     # def filename(self):
#     #     ext = 'sources'
#     #     if self.legacy:
#     #         ext = 'list'
        
#     #     return f'{self.ident}.{ext}'
    
#     # @property
#     # def sources(self):
#     #     """ List(Source): A list of all of the sources, regardless of format."""
#     #     sources: List(Source) = []
        
#     #     if self.legacy:
#     #         for source in self.legacy_sources:
#     #             sources.append(self.legacy_sources[source])
        
#     #     else:
#     #         for source in self.deb_sources:
#     #             sources.append(self.deb_sources[source])
        
#     #     return sources

#     # @property
#     # def single_source(self):
#     #     """ bool: the file contains a single repo (with or without source code)"""
#     #     if len(self.sources) == 1:
#     #         return True
        
#     #     if len(self.sources) == 2:
#     #         source0 = (
#     #             self.sources[0].uris,
#     #             self.sources[0].suites,
#     #             self.sources[0].components
#     #         )
#     #         source1 = (
#     #             self.sources[1].uris,
#     #             self.sources[1].suites,
#     #             self.sources[1].components
#     #         )
#     #         if source0 == source1:
#     #             return True
        
#     #     return False
    
#     # @property
#     # def source_code(self):
#     #     """ bool: whether source code is enabled for a single source.

#     #     Returns False if single_source is false.
#     #     """
#     #     try:
#     #         if self.single_source and self.sources[1].enabled:
#     #             return True
#     #     except IndexError:
#     #         pass
        
#     #     return False
    
#     # @source_code.setter
#     # def source_code(self, enabled):
#     #     """ Enable the source_code repo. 
        
#     #     Do nothing if this isn't a single_source or if there isn't already a
#     #     source code repo present."""
#     #     if self.has_source_code:
#     #         try:
#     #             self.sources[1].enabled = enabled
#     #         except IndexError:
#     #             pass
    
#     # @property
#     # def has_source_code(self):
#     #     """ bool: True if this is a single source and there is a source code
#     #     repo present."""
#     #     if self.single_source and len(self.sources) == 2:
#     #         return True
        
#     #     return False


#     # # These properties are here for convenince to make changing sources easier.
#     # # They will only make changes if this is a single-source. Otherwise, they 
#     # # do nothing. 

#     # @property
#     # def name(self):
#     #     """ name"""
#     #     if self.single_source:
#     #         return self.sources[0].name
    
#     # @name.setter
#     # def name(self, name):
#     #     """Set the property in the sources."""
#     #     if self.single_source:
#     #         for source in self.sources:
#     #             source.name = name


#     # @property
#     # def enabled(self):
#     #     """ enabled"""
#     #     if self.single_source:
#     #         return self.sources[0].enabled
    
#     # @enabled.setter
#     # def enabled(self, enabled):
#     #     """Set the property in the sources."""
#     #     if self.single_source:
#     #         for source in self.sources:
#     #             source.enabled = enabled


#     # @property
#     # def types(self):
#     #     """ types"""
#     #     if self.single_source:
#     #         return self.sources[0].types
    
#     # @types.setter
#     # def types(self, types):
#     #     """Set the property in the sources."""
#     #     if self.single_source:
#     #         for source in self.sources:
#     #             source.types = types


#     # @property
#     # def uris(self):
#     #     """ uris"""
#     #     if self.single_source:
#     #         return self.sources[0].uris
    
#     # @uris.setter
#     # def uris(self, uris):
#     #     """Set the property in the sources."""
#     #     if self.single_source:
#     #         for source in self.sources:
#     #             source.uris = uris


#     # @property
#     # def suites(self):
#     #     """ suites"""
#     #     if self.single_source:
#     #         return self.sources[0].suites
    
#     # @suites.setter
#     # def suites(self, suites):
#     #     """Set the property in the sources."""
#     #     if self.single_source:
#     #         for source in self.sources:
#     #             source.suites = suites


#     # @property
#     # def components(self):
#     #     """ components"""
#     #     if self.single_source:
#     #         return self.sources[0].components
    
#     # @components.setter
#     # def components(self, components):
#     #     """Set the property in the sources."""
#     #     if self.single_source:
#     #         for source in self.all_sources():
#     #             source.components = components


#     # @property
#     # def options(self):
#     #     """ options"""
#     #     if self.single_source:
#     #         return self.sources[0].options
    
#     # @options.setter
#     # def options(self, options):
#     #     """Set the property in the sources."""
#     #     if self.single_source:
#     #         for source in self.sources:
#     #             source.options = options
        
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
        self.sources: Dict = {}
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
    
    def save_to_disk(self, save: bool = True):
        """ Saves the source to disk."""
        if not self.ident:
            raise SourceFileError('No Filename to save was specified.')

        for source in self.sources.values():
            source.make_key()
        
        if save:
            try:
                with open(self.source_path, mode='w') as sources_file:
                    sources_file.write(self.generate_output())
            
            except PermissionError:
                privileged_object = util.get_dbus_object()
                privileged_object.output_file_to_disk(
                    f'{self.ident}.{self.format}',
                    self.generate_output()
                )
        else:
            print(self.generate_output())
        
    def convert_formats(self):
        """ Convert the source file from its current format to the opposite."""
        try:
            self.source_path.unlink()
        except PermissionError:
            privileged_object = util.get_dbus_object()
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
                        if name:
                            if not source.name:
                                source.name = name
                            if source.types == [util.AptSourceType.SOURCE]:
                                source.name = f'{name} Source code'
                        source.enabled = False
                        source.file = self
                        source.ident = self.ident
                        if source_count > 0:
                            source.ident = f'{self.ident}-{source_count}'
                        self.sources[source_count] = source
                        source_count += 1
                        self.items.append(source)

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
                        source.ident = self.ident
                        if source_count > 0:
                            source.ident = f'{self.ident}-{source_count}'
                        self.sources[source_count] = source
                        source_count += 1
                        self.items.append(source)

                # Empty lines count as comments
                if line.strip() == '':
                    self.items.append('')

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
                    source.ident = self.ident
                    if source_count > 0:
                        source.ident = f'{self.ident}-{source_count}'
                    self.sources[source_count] = source
                    self.items.append(source)
                    source_count += 1
                    raw_822 = []
                    item += 1
                    self.items.append('')

                else:
                    raw_822.append(line.strip())

        if raw_822:
            parsing_deb822 = False
            source = Source()
            source.load_from_data(raw_822[1:])
            self.sources[source_count] = source
            self.items.append(source)
            source_count += 1
            raw_822 = []
            item += 1
            self.items.append('')

    def add_source(self, source: Source): 
        """ Adds a source to this file.

        Arguments:
            :source Source: The source to add (Can be any source subclass)            
        """
        self.items.append(source)
        source_count = len(self.sources.items) - 1 
        self.sources[source_count] = source
    
    def remove_source(self, source: int, errors: bool = False):
        """ Remove a source from this file.

        Arguments:
            :source int: The index of the source to remove
        """
        remove_source = self.sources[index]
        self.items.remove(remove_source)
        self.sources.pop(source, None)
