#!/usr/bin/python3

"""
Copyright (c) 2020, Ian Santopietro
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

Module for adding repos to the system in CLI applications.
"""

from ..deb import DebLine
from ..legacy_deb import LegacyDebSource
from ..ppa import PPASource
from ..file import SourceFile
from ..util import DISTRO_CODENAME, CLEAN_CHARS, dbus_quit

from . import command

KEYSERVER = 'keyserver.ubuntu.com'
SHORTCUTS = [PPASource]

class Add(command.Command):
    """ Add subcommand.

    The add command is used for adding new software sources to the system. It
    requires root.

    Options:
        --disable, -d
        --source-code, -s
        --expand, -e
    """

    shortcut_prefixes = {
        'deb': DebLine,
        'deb-src': DebLine,
        PPASource.prefix: PPASource,
    }

    @classmethod
    def init_options(cls, subparsers):
        """ Sets up this command's options parser.

        Returns:
            The subparser for this command.
        """
        options = subparsers.add_parser(
            'add',
            help='Add a new repository to the system.'
        )
        options.add_argument(
            'deb_line',
            nargs='*',
            default=['822styledeb'],
            help='The deb line of the repository to add'
        )
        options.add_argument(
            '-d',
            '--disable',
            action='store_true',
            help='Add the repository and then set it to disabled.'
        )
        options.add_argument(
            '-s',
            '--source-code',
            action='store_true',
            help='Also enable source code packages for the repository.'
        )
        options.add_argument(
            '-e',
            '--expand',
            action='store_true',
            help='Display expanded details about the repository before adding it.'
        )
        options.add_argument(
            '-n',
            '--name',
            default=['x-repolib-default-name'],
            help='A name to set for the new repo'
        )
        options.add_argument(
            '-i',
            '--identifier',
            default=['x-repolib-default-id'],
            help='The filename to use for the new source'
        )
        options.add_argument(
            '-k',
            '--skip-keys',
            action='store_true',
            help='Skip adding signing keys (not recommended!)'
        )

    def finalize_options(self, args):
        """ Finish setting up options/arguments."""
        super().finalize_options(args)
        self.deb_line = ' '.join(self.args.deb_line)
        self.expand = args.expand
        self.source_code = args.source_code
        self.disable = args.disable
        try:
            name = args.name.split()
        except AttributeError:
            name = args.name
        try:
            ident = args.identifier.split()
        except AttributeError:
            ident = args.identifier
        self.name = ' '.join(name)
        self.ident = '-'.join(ident).translate(CLEAN_CHARS)

        self.skip_keys = args.skip_keys

    def set_names(self, source):
        """Set up names for the source.

        Arguments:
            source(repolib.Source): The source for which to set names
        """
        source.make_names()

        if self.name != 'x-repolib-default-name':
            self.log.debug('Got Name: %s', self.name)
            source.name = self.name

        if self.ident != 'x-repolib-default-id':
            self.log.debug('Got Ident: %s', self.ident)
            source.ident = self.ident.lower()

# pylint: disable=too-many-statements, attribute-defined-outside-init
# Not a lot of reusable code here. Unfortunately it just needs to do a lot.
    def run(self):
        """ Run the command."""
        # pylint: disable=too-many-branches
        # We just need all these different checks.
        if self.deb_line == '822styledeb':
            self.parser.print_usage()
            self.log.error('A repository is required.')
            return False

        if self.deb_line.startswith('http') and len(self.deb_line.split()) == 1:
            self.deb_line = f'deb {self.deb_line} {DISTRO_CODENAME} main'

        print('Fetching repository information...')

        new_file = SourceFile()

        self.log.debug('Adding line %s', self.deb_line)

        for prefix in self.shortcut_prefixes:
            self.log.debug('Trying prefix %s', prefix)
            if self.deb_line.startswith(prefix):
                self.log.debug('Line is prefix: %s', prefix)
                new_source = self.shortcut_prefixes[prefix](line=self.deb_line)
                break
    
        new_source.enabled = not self.disable
        new_file.ident = new_source.make_default_name()
        new_file.add_source(new_source)

        if not self.deb_line.startswith('deb-src'):
            # Only add source code repos if the line is not a source code repo
            new_source_code = new_source.copy(source_code=True)
            new_source_code.enabled = self.source_code
            new_file.add_source(new_source_code)
        
        new_file.format = 'list'
        if self.expand:
            print('Adding the following source:')
            try:
                print(new_source.ppa.description)
                print('\n')
                print(new_file.generate_output())
            except AttributeError:
                print(new_file.generate_output())
            self.log.debug('File format: %s', new_file.format)
            self.log.debug('Filename: %s.%s', new_file.ident, new_file.format)
            try:
                input(
                    'Press ENTER to continue adding this source, or Ctrl+C '
                    'to cancel: '
                )
            except KeyboardInterrupt:
                # Handle this nicely to avoid printing errors when a user cancels
                exit(0)

        if self.args.debug == 0:
            new_file.save_to_disk(skip_keys=self.skip_keys)
            dbus_quit()
            return True

        return False
