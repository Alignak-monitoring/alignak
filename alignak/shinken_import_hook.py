# -*- coding: utf-8 -*-

import importlib
import sys


class Finder(object):

    def find_module(self, fullname, path=None):
        if fullname == 'shinken' or fullname.startswith('shinken.'):
            return self

    def load_module(self, name):
        mod = sys.modules.get(name)
        if mod is None:
            alignak_name = 'alignak%s' % name[7:]
            mod = sys.modules.get(alignak_name)
            if mod is None:
                mod = importlib.import_module(alignak_name)
            sys.modules[name] = mod
        return mod


finder = Finder()
sys.meta_path.append(finder)
