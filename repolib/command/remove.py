
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

Command to remove sources from the system.
"""

from pathlib import Path

import dbus

from . import command
from .. import get_all_sources
from ..source import Source
from ..legacy_deb import LegacyDebSource
from ..util import get_sources_dir, RepoError, dbus_quit

class Remove(command.Command):
    # pylint: disable=no-self-use,too-few-public-methods
    # This is a base class for other things to inherit and give other programs
    # a standardized interface for interacting with commands.
    """ Remove subcommand.

    The remove command will remove the selected source. It has no options. Note
    that the system sources cannot be removed. This requires root.
    """

    @classmethod
    def init_options(cls, subparsers):
        """ Sets up this command's options parser.

        Returns:
            The subparser for this command.
        """
        parser_remove = subparsers.add_parser(
            'remove',
            help='Remove a configured repository.'
        )
        parser_remove.add_argument(
            'repository',
            help='The name of the repository to remove. See LIST'
        )

        parser_remove.add_argument(
            '-y',
            '--assume-yes',
            action='store_true',
            help='Remove sources without prompting for confirmation.'
        )

    def __init__(self, log, args, parser):
        super().__init__(log, args, parser)

        self.source_name = args.repository
        self.sources_dir = get_sources_dir()

    def finalize_options(self, args):
        """ Finish setting up our options/arguments. """
        super().finalize_options(args)
        self.source, self.source_file = None, None
        sources, errors = get_all_sources()
        for source in sources:
            if source.ident == args.repository:
                self.source = source
                self.source_file = source.file
        self.assume_yes = args.assume_yes

    def run(self):
        """ Run the command. """

        self.log.debug('Removing %s', self.source)

        if self.source.ident.lower() == 'system':
            self.log.error("You cannot remove the system sources!")
            return False

        if not self.source:
            self.log.error(
                'Could not load the source "%s"; not found',
                self.source
            )
            return False
        
        response = 'y'
        if not self.assume_yes:
            response = 'n'
            print(f'This will remove the source {self.source.name}.')
            response = input('Are you sure you want to do this? (y/N) ')

        if response.lower() == 'y':
            source_index = self.source_file.get_source_index(self.source)
            self.source_file.remove_source(source_index)
            self.source_file.save_to_disk()

        else:
            print('Canceled.')
            return False

        return True
