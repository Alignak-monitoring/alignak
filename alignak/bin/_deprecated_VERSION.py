# -*- coding: utf-8 -*-
# pylint: disable=C0103
"""This module provide VERSION if we try to import alignak.bin.VERSION
It will raise a warning to notify user/dev

"""
import warnings

from .. import __version__
from alignak.misc.custom_module import CustomModule


class DeprecatedAlignakBin(CustomModule):
    """DeprecatedAlignakBin subclasses Custommodule and implement VERSION property

    """

    @property
    def VERSION(self):
        """Any code importing, or using, `VERSION` from alignak.bin will have
        this deprecation warning emitted, *if* deprecation warnings are enabled.

        :return: version number
        :rtype: str
        """
        warnings.warn(
            '`alignak.bin.VERSION` is deprecated version attribute'
            ' and will be removed in a future release.\n'
            'You must use `alignak.__version__` attribute by now.\n'
            'Please update your code accordingly.', DeprecationWarning, stacklevel=2)
        return __version__
