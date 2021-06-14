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
#pylint: disable=too-many-ancestors
# If we want to use the subclass, we don't have a lot of options.

import re

import dbus
from debian import deb822

from . import util
from .parsedeb import ParseDeb

class SourceError(Exception):
    """ Exception from a source object."""

    def __init__(self, *args, code=1, **kwargs):
        """Exception with a source object

        Arguments:
            code (:obj:`int`, optional, default=1): Exception error code.
    """
        super().__init__(*args, **kwargs)
        self.code = code

class Source(deb822.Deb822):
    """ A Deb822 object representing a software source.

    Provides a dict-like interface for accessing and modifying DEB822-format
    sources, as well as options for loading and saving them from disk.
    """
    # pylint: disable=too-many-instance-attributes
    # We want to provide easy access to these data

    options_d = {
        'arch': 'Architectures',
        'lang': 'Languages',
        'target': 'Targets',
        'pdiffs': 'PDiffs',
        'by-hash': 'By-Hash',
        'allow-insecure': 'Allow-Insecure',
        'allow-weak': 'Allow-Weak',
        'allow-downgrade-to-insecure': 'Allow-Downgrade-To-Insecure',
        'trusted': 'Trusted',
        'signed-by': 'Signed-By',
        'check-valid-until': 'Check-Valid-Until',
        'valid-until-min': 'Valid-Until-Min',
        'valid-until-max': 'Valid-Until-Max'
    }

    outoptions_d = {
        'Architectures': 'arch',
        'Languages': 'lang',
        'Targets': 'target',
        'PDiffs': 'pdiffs',
        'By-Hash': 'by-hash',
        'Allow-Insecure': 'allow-insecure',
        'Allow-Weak': 'allow-weak',
        'Allow-Downgrade-To-Insecure': 'allow-downgrade-to-insecure',
        'Trusted': 'trusted',
        'Signed-By': 'signed-by',
        'Check-Valid-Until': 'check-valid-until',
        'Valid-Until-Min': 'valid-until-min',
        'Valid-Until-Max': 'valid-until-max'
    }
    options_re = re.compile(r'[^@.+]\[([^[]+.+)\]\ ')
    uri_re = re.compile(r'\w+:(\/?\/?)[^\s]+')
    debline_parser = ParseDeb()

    def __init__(self, *args, line:str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_values()
        self.file = None
        if line:
            self.parse_debline(line)

    def init_values(self) -> None:
        """ Reset Values to blank defaults, and adds all of them to self.

        We need to do this to ensure they are in the correct order.
        """
        self.ident:str = ''
        self.name:str = ''
        self.enabled:bool = True
        self.types:list(str) = ['deb']
        self.uris:list(str) = []
        self.suites:list(str) = []
        self.components:list(str) = []
        self.options:dict(str, str) = {}
        self.comment:str = ''
    
    def load_from_data(self, data:list) -> None:
        """ Loads the given data into self.

        Arguments:
            data (list[str]): The data to load from.
        """
        self.init_values()
        if data[0].strip().startswith('#'):
            comment = util.strip_hashes(data.pop(0))
            self.comment = comment
            
        super().__init__(sequence=data)
    
    # pylint: disable=arguments-differ
    # We're doing something different than the parent class
    def copy(self, source_code=False):
        """ Copies the source and returns an identical source object.

        Arguments:
            source_code (bool): If True, output object will have source enabled.
        
        Returns:
            Source(): The copied source object.
        """
        new_source = Source()
        new_source.file = self.file
        new_source.name = self.name
        new_source.enabled = self.enabled
        new_source.types = self.types.copy()

        if source_code:
            new_source.types = ['deb-src']

        new_source.uris = self.uris.copy()
        new_source.suites = self.suites.copy()
        new_source.components = self.components.copy()

        try:
            new_source.options = self.options.copy()
        except AttributeError:
            pass
        return new_source
    
    def make_source_string(self, indent:int = 0) -> str:
        """ Make a printable string of the source.

        This method produces output suitable for output to a user e.g. in a 
        command. For getting the actual data, use self.dump() instead.

        Arguments:
            :indent int: The indent to add to the output.

        Returns:
            str: The output string.
        """
        self.enabled = self.enabled
        print_output:str = self.dump()
        print_output = print_output.replace('X-Repolib-Name', 'Name')
        print_output = print_output.replace('X-Repolib-Ident: ', '')
        print_output = print_output.replace(self.ident, f'{self.ident}:')
        print_output += f'Comments: {self.comment}'

        return print_output
    
    def save_string(self):
        """ Create a string for saving the source to a file. 

        Returns:
            str: The generated string.
        """
        save_output:str = ''
        if self.comment:
            save_output = f'# {self.comment}\n'
        save_output += self.dump()
        return save_output
    
    def make_debline(self) -> str:
        """ Output this source as a one-line format source line.

        Note: this is expected to fail if there is more than one type, URI, or
        Suite; the one-line format does not support having multiple of these
        properties.
        """
        line = ''

        for attr in ['types', 'uris', 'suites']:
            if len(getattr(self, attr)) > 1:
                msg = f'The source has too many {attr}.'
                msg += f'One-line format sources support one {attr[:-1]} only.'
                raise SourceError(msg)
        
        if not self.enabled:
            line += '# '
        
        line += self.types[0].strip()
        line += ' '
        
        if self.options:
            line += '['
            line += self._get_options()
            line = line.strip()
            line += '] '
        
        line += f'{self.uris[0]} '
        line += f'{self.suites[0]} '

        for component in self.components:
            line += f'{component} '
        
        line += f' ## X-Repolib-Name: {self.name}'
        line += f' # X-Repolib-Ident: {self.ident}'
        line += f' # {self.comment}'

        return line

    
    def make_default_name(self, prefix='') -> str:
        """ Create a default name for this source.

        Arguments:
            prefix (str): An optional prefix to append to the beginning of the
                name.
        
        Returns:
            str: The generated name.
        """
        if len(self.uris) > 0:
            uri = self.uris[0].replace('/', ' ')
            uri_list = uri.split()
            name = '{}{}'.format(
                prefix,
                '-'.join(uri_list[1:]).translate(util.CLEAN_CHARS)
            )
        else:
            # Use the ident as a fallback as it should be good enough
            name = self.ident
        
        return name
    
    def make_default_ident(self) -> str:
        """ Make a default ident if one is not provided.

        The ident is used to uniquely identify the source within a file. 
        
        Returns:
            str: The generated ident
        """
    
    def make_key(self):
        """ Create a signing key for this source.

        Note: This is intended to be used by subclasses.
        """
        self.key_file = util.get_keys_dir() / f'{self.ident}.gpg'
        return
    
    def delete_key(self):
        """ Delete the signing key file for this source."""
        try:
            self.key_file.unlink(missing_ok=True)
        except PermissionError:
            bus = dbus.SystemBus()
            privileged_object = bus.get_object('org.pop_os.repolib', '/Repo')
            privileged_object.delete_key(self.key_file.name)
    
    def parse_debline(self, line:str) -> None:
        """ Parse a one-line format source.
        
        Arguments:
            line (str): The one-line source line to parse
        """
        self.init_values()

        if not util.validate_debline(line):
            raise SourceError(f'The line {line} is malformed.')
        
        parsed_debline = self.debline_parser.parse_line(line)
        self.enabled = parsed_debline['enabled']
        self.ident = parsed_debline['ident']
        self.name = parsed_debline['name']
        self.comment = parsed_debline['comment']
        self.types = [parsed_debline['repo_type']]
        self.uris = [parsed_debline['uri']]
        self.suites = [parsed_debline['suite']]
        self.components = parsed_debline['components']
        self.options = parsed_debline['options'].copy()
    
    def dump(self) -> str:
        """ Override to add options to output."""
        output:str = super().dump()
        for key in self.options:
            output += f'{key}: {self.options[key]}\n'
        
        return output
    
    def _compare_ident(self, source):
        """ Compare the ident of source and self

        Return True if they are equal"""
        if self.ident == source.ident:
            return True
        return False
    
    def compare_source(self, source, compare_types: bool = True):
        """ Compare self with source. Return True if identical

        This method ignores certain immaterial parameters (like name and ident)
        because they don't affect the technical equivalence. This prevents us 
        using self == source.
        """
        types_equal = True
        if compare_types:
            types_equal = self.types == source.types
        uris_equal = self.uris == source.uris
        suites_equal = self.suites == source.suites
        components_equal = self.components == source.components

        for cond in (types_equal, uris_equal, suites_equal, components_equal):
            if not cond:
                # If any of these aren't the same, then the sources are 
                # technically different and we should return False.
                return False
        return True

    @property
    def key_data(self) -> bytes:
        """ bytes: The data containing the signing key for this source. 
        
        Since base sources don't have keys, we skip this in this class.

        In subclasses which add key files, be sure to return the encoded bytes.
        Otherwise things may not work.
        """
        return None
        
    
    @property
    def ident(self) -> str:
        """ str: The unique identifier for this source within its file"""
        try:
            return self['X-Repolib-Ident']
        except KeyError:
            return ''
    
    @ident.setter
    def ident (self, ident: str) -> None:
        # self._ident = ident
        # self.key_file =  util.get_keys_dir() / f'{self.ident}.gpg' 

        ident = ident.translate(util.CLEAN_CHARS)
        self['X-Repolib-Ident'] = ident


    @property
    def source_code(self) -> bool:
        """ bool: Whether or not this source provides source code."""
        if 'src' in self.types:
            return True
        return False
    
    @source_code.setter
    def source_code (self, source_code: bool):
        if source_code:
            if 'src' not in self.types:
                self.types += ' deb-src'
        else:
            self.types = 'deb'


    @property
    def name(self) -> str:
        """ str: A human-friendly name for this source"""
        if not self['X-Repolib-Name']:
            self['X-Repolib-Name'] = self.make_default_name()
        return self['X-Repolib-Name']
    
    @name.setter
    def name (self, name: str):
        self['X-Repolib-Name'] = name


    @property
    def enabled(self) -> bool:
        """ bool: whether or not this source is enabled"""
        enabled = self['Enabled'] == 'yes'
        if enabled and self.has_required_parts:
            return True
        return False
            
    
    @enabled.setter
    def enabled (self, enabled):
        e_values = [
            True,
            'True',
            'true',
            'Yes',
            'yes',
            'YES',
            'y',
            'Y',
            util.AptSourceEnabled.TRUE,
            1
        ]

        if enabled in e_values:
            self['Enabled'] = 'yes'
        else:
            self['Enabled'] = 'no'


    @property
    def types(self) -> list:
        """ list: The types of the source"""
        return self['Types'].split()
    
    @types.setter
    def types (self, types: list):
        self['Types'] = ' '.join(types).strip()


    @property
    def uris(self) -> list:
        """ list: The URIs for this source"""
        return self['URIs'].split()
    
    @uris.setter
    def uris (self, uris: list):
        self['URIs'] = ' '.join(uris).strip()


    @property
    def suites(self) -> list:
        """ list: The suites for this source"""
        return self['Suites'].split()
    
    @suites.setter
    def suites (self, suites: list):
        self['Suites'] = ' '.join(suites).strip()


    @property
    def components(self) -> list:
        """ list: The components for this source"""
        return self['Components'].split()
    
    @components.setter
    def components (self, components: list):
        self['Components'] = ' '.join(components).strip()


    @property
    def options(self) -> dict:
        """ dict: The options for this source"""
        return self._options
    
    @options.setter
    def options (self, options: dict):
        self._options = options


    @property
    def has_required_parts(self) -> bool:
        """ bool: True if all required attributes are set, otherwise false."""
        required_parts = ['uris', 'suites', 'ident']

        for attr in required_parts:
            if len(getattr(self, attr)) < 1:
                return False
        
        return True

    def _get_options(self):
        """ Turn the options dict into a single string for one-lining."""
        opt_str = ''
        for key in self.options:
            opt_str += f'{self.outoptions_d[key]}={self.options[key].replace(" ", ",")} '
        return opt_str
    
    def _copy(self, new_source, source_code=False):
        """ Copy the data from self into new_source)"""
        new_source.name = self.name
        new_source.enabled = self.enabled
        new_source.types = self.types.copy()

        if source_code:
            new_source.types = [util.AptSourceType.SOURCE]

        new_source.uris = self.uris.copy()
        new_source.suites = self.suites.copy()
        new_source.components = self.components.copy()

        try:
            new_source.options = self.options.copy()
        except AttributeError:
            pass
        return new_source
