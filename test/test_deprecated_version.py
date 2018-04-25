

import sys
import warnings

from .alignak_test import AlignakTest

class Test_Deprecated_alignak_bin_VERSION(AlignakTest):
    def setUp(self):
        super(Test_Deprecated_alignak_bin_VERSION, self).setUp()

    def test_deprecated_version(self):
        """ Test the deprecated Alignak version warning """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            import alignak.bin
            alignak.bin.VERSION
            assert 1 == len(w)
            assert w[-1].category is DeprecationWarning
            assert '`alignak.bin.VERSION` is deprecated version' in str(w[-1].message)
