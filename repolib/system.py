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
#pylint: disable=too-many-ancestors, too-many-instance-attributes
# If we want to use the subclass, we don't have a lot of options.

from . import file
from . import util

class SystemSourceException(Exception):
    """ System Source Exceptions. """

    def __init__(self, *args, code=1, **kwargs):
        """Exception with the system sources

        Arguments:
            msg (str): Human-readable message describing the error that threw the
                exception.
            code (:obj:`int`, optional, default=1): Exception error code.
    """
        super().__init__(*args, **kwargs)
        self.code = code

class SystemSource(file.SourceFile):
    """ System Sources. """

    def __init__(self, ident='system'):
        """ Constructor for System Sources

        Loads a source object for the System Sources. These are located (by
        default) in /etc/apt/sources.list.d/system.sources. If your distro uses
        a different location, please patch this in your packaging.
        """
        super().__init__()
        self.ident = ident
        self.parse_file()
    
    def set_source_enabled(self, enabled:bool = True):
        """Enable or disable source code for the system sources.
        
        Arguments:
            :bool enabled: The desired state of the system source code.
        """

        system_source = self.get_main_os_source()
        system_source.set_source_enabled(enabled)
    
    def get_main_os_source(self):
        """ Finds the main OS source and returns it."""
        possible_sources = []
        for source in self.sources:
            # If a source has a default mirror, then it's probably the OS source.
            try:
                if source.default_mirror:
                    if source not in possible_sources:
                        possible_sources.append(source)
            except AttributeError:
                # If the system doesn't have a default mirror, skip it. 
                pass

            # If a source name contains "System Sources", it's probably the OS source.
            singular = "system source" in source.name.lower()
            plural = "system sources" in source.name.lower()

            if singular or plural:
                if source not in possible_sources:
                    possible_sources.append(source)
        
        if len(possible_sources) > 1:
            raise SystemSourceException(
                'There are multiple sources which may be the system source. '
                'This is probably due to a malformed system source file. Path '
                'to system source file: {}'.format(self.filename)
            )
        
        if len(possible_sources) == 0:
            raise SystemSourceException(
                'There was not a candidate for default system source.'
            )

        return possible_sources[0]

    def set_component_enabled(self, component='main', enabled=True):
        """ Enables or disabled a repo component (e.g. 'main')

        Keyword Arguments:
            component -- The component to (en|dis)able (default: "main")
            ennabled -- Whether COMPONENT is enabled (default: True)
        """
        source = self.get_main_os_source()
        components = source.components.copy()

        if not enabled:
            if component in components:
                components.remove(component)
                source.components = components.copy()
                self.save_to_disk()
                return component
        else:
            if component not in components:
                self.enabled = True
                components.append(component)
                source.components = components.copy()
                self.save_to_disk()
                return component

        raise SystemSourceException(
            msg=f"Couldn't toggle component: {component} to {enabled}"
        )

    def set_suite_enabled(self, suite=util.DISTRO_CODENAME, enabled=True):

        """ Enables or disabled a repo suite (e.g. 'main')

        Keyword Arguments:
            suite -- The suite to (en|dis)able (default: main)
            ennabled -- Whether COMPONENT is enabled (default: True)
        """
        source = self.get_main_os_source()
        suites = source.suites.copy()
        if not enabled:
            if suite in suites:
                suites.remove(suite)
                source.suites = suites.copy()
                self.save_to_disk()
                return suite
        else:
            if suite not in suites:
                self.enabled = True
                suites.append(suite)
                source.suites = suites.copy()
                self.save_to_disk()
                return suite


        raise SystemSourceException(
            msg=f"Couldn't toggle suite: {suite} to {enabled}"
        )

    def set_default_mirror(self):
        """ Resets the System Sources to use the default mirrors.

        Requires that the `default_mirror` attribute be set.
        """
        source = self.get_main_os_source()

        if source.default_mirror:
            source.uris = [source.default_mirror]
            return
        raise SystemSourceException('No default mirror set.')

    @property
    def default_mirror(self):
        """str: The default system mirror."""
        source = self.get_main_os_source()
        try:
            return source['X-Repolib-Default-Mirror']
        except KeyError:
            return ''

    @default_mirror.setter
    def default_mirror(self, uri):
        source = self.get_main_os_source()
        if util.url_validator(uri):
            source['X-Repolib-Default-Mirror'] = uri
