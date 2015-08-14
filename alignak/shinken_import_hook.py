# -*- coding: utf-8 -*-
"""This module provides a Finder class for python modules.
It is used to keep compatibility with Shinken modules to be able to
import them.

It basically replace shinken package by alignak one

"""
import importlib
import sys


class Finder(object):
    """Finder class to import and load module

    see : https://docs.python.org/2/glossary.html#term-finder
          https://docs.python.org/2/library/sys.html#sys.meta_path
    """

    def find_module(self, fullname, path=None):
        """Find module based on the fullname and path given

        :param fullname: module full name
        :type fullname: str
        :param path: path to find (not used, only for signature)
        :type path: str
        :return: module | None
        :rtype: object
        """
        hookable_names = ['shinken', 'shinken_modules', 'shinken_test']
        if fullname in hookable_names or fullname.startswith('shinken.'):
            return self

    def load_module(self, name):
        """Load module

        :param name: module to load
        :type name: str
        :return: module
        :rtype: object
        """
        mod = sys.modules.get(name)
        if mod is None:
            alignak_name = 'alignak%s' % name[7:]
            mod = sys.modules.get(alignak_name)
            if mod is None:
                mod = importlib.import_module(alignak_name)
            sys.modules[name] = mod
        return mod

# pylint: disable=C0103
finder = Finder()
sys.meta_path.append(finder)
