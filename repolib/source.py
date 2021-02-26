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

from debian import deb822

from . import util


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

    def __init__(self, *args, ident=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_values()
        self.file = None

    def init_values(self):
        """ Reset Values to blank defaults, and adds all of them to self.

        We need to do this to ensure they are in the correct order.
        """
        self.name = ''
        self.enabled = True
        self.types = 'deb'
        self.uris = []
        self.suites = []
        self.components = []
        self.options = {}
    
    def load_from_data(self, data):
        """ Loads the given data into self.

        Arguments:
            data (list[str]): The data to load from.
        """
        self.init_values()
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
    
    def make_source_string(self):
        """ Make a printable string of the source.

        This method produces output suitable for output to a user e.g. in a 
        command. For getting the actual data, use self.dump() instead.

        Returns:
            str: The output string.
        """
        self.enabled = self.enabled
        print_output = self.dump()
        print_output.replace('X-Repolib-Name', 'Name')

        return print_output
    
    def save_string(self):
        """ Create a string for saving the source to a file. 

        Returns:
            str: The generated string.
        """
        save_output = ''
        save_output += f'## {self.ident}\n'
        save_output += self.dump()
        return save_output
    
    def make_debline(self):
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

        return line

    
    def make_default_name(self, prefix=''):
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
    
    def make_key(self):
        """ Create a signing key for this source.

        Note: This is intended to be used by subclasses.
        """
        return
    
    def set_options(self, options):
        """Turn a one-line format options substring into a supported dict.

        Arguments:
            options (str): the one-line format options string to parse.
        
        Returns:
            dict: The parsed options and values.
        """
        # Split the option string into a list of chars, so that we can replace
        # the first and last characters ([ and ]) with spaces.
        ops = list(options)
        ops[0] = " "
        ops[-1] = " "
        options = "".join(ops).strip()

        for replacement in self.options_d:
            options = options.replace(replacement, self.options_d[replacement])

        options = options.replace('=', ',')
        options_list = options.split()

        options_output = {}

        for i in options_list:
            option = i.split(',')
            values_list = []
            for value in option[1:]:
                values_list.append(value)
            options_output[option[0]] = ' '.join(values_list)
        return options_output
    
    def parse_debline(self, line):
        """ Parse a one-line format source.
        
        Arguments:
            line (str): The one-line source line to parse
        """
        self.init_values()

        if not util.validate_debline(line):
            raise SourceError(f'The line {line} is malformed.')

        if '# X-Repolib-Name: ' in line:
            name_line = line.replace('# X-Repolib-Name: ', '\x05')
            name_list = name_line.split('\x05')
            self.name = name_list[-1]

        # Enabled vs. Disabled
        self.enabled = True
        if line.startswith('#'):
            self.enabled = False
            line = line.replace('#', '', 1)
            line = line.strip()

        # URI parsing
        for word in line.split():
            if util.url_validator(word):
                self.uris = [word]
                line_uri = line.replace(word, '')

        # Options parsing
        try:
            options = self.options_re.search(line_uri).group()
            opts = self.set_options(options.strip())
            self.options = opts.copy()
            line_uri = line_uri.replace(options, '')
        except AttributeError:
            pass

        deb_list = line_uri.split()

        # Type Parsing
        self.types = ['deb']
        if deb_list[0] == 'deb-src':
            self.types = ['deb-src']

        # Suite Parsing
        self.suites = [deb_list[1]]

        # Components parsing
        comps = []
        for item in deb_list[2:]:
            if not item.startswith('#'):
                comps.append(item)
            else:
                break
        self.components = comps

    
    @property
    def ident(self) -> str:
        """ str: The unique identifier for this source within its file"""
        return self._ident
    
    @ident.setter
    def ident (self, ident: str):
        self._ident = ident


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
