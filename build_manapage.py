# -*- coding: utf-8 -*-

"""build_manpage command -- Generate man page from argparse/dist metadata.
Lifted from: Andi Albrecht, http://andialbrecht.wordpress.com/2009/03/17/creating-a-man-page-with-distutils-and-optparse/
Minimal modifications to work with argparse.
"""

import argparse
from setuptools import Command, distutils


class ManPageFormatter(argparse.HelpFormatter):
    def _markup(self, txt):
        """Prepares txt to be used in man pages."""
        return txt.replace('-', '\\-')

    def format_usage(self, usage):
        """Formate the usage/synopsis line."""
        return self._markup(usage)

    def format_heading(self, heading):
        """Format a heading.
        If level is 0 return an empty string. This usually is the string "Options".
        """
        if self.level == 0:
            return ''
        return '.TP\n%s\n' % self._markup(heading.upper())

    def format_option(self, option):
        """Format a single option.
        The base class takes care to replace custom argparse values.
        """
        result = []
        opts = self.option_strings[option]
        result.append('.TP\n.B %s\n' % self._markup(opts))
        if option.help:
            help_text = '%s\n' % self._markup(self.expand_default(option))
            result.append(help_text)
        return ''.join(result)


class build_manpage(Command):
    description = 'Generate a man page.'
    user_options = [
        ('output=', 'O', 'output file'),
        ('parser=', None, 'module path to parser (e.g. mymod:func'),
        ]                                                                       

    def initialize_options(self):
        self.output = None
        self.parser = None                                                      

    def finalize_options(self):
        if self.output is None:
            raise distutils.errors.DistutilsOptionError('\'output\' option is required')
        if self.parser is None:
            raise distutils.errors.DistutilsOptionError('\'parser\' option is required')
        mod_name, func_name = self.parser.split(':')
        fromlist = mod_name.split('.')
        try:
            mod = __import__(mod_name, fromlist=fromlist)
            self._parser = getattr(mod, func_name)()
        except ImportError, err:
            raise
        self._parser.formatter = ManPageFormatter()
        self._parser.formatter.set_parser(self._parser)
        self.announce('Writing man page %s' % self.output)
        self._today = datetime.date.today()

    def run(self):
    # Do something useful!
        pass
