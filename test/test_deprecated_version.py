

import sys
import warnings

if sys.version_info[:2] >= (2, 7):
    import unittest
else:
    import unittest2 as unittest


class Test_Deprecated_alignak_bin_VERSION(unittest.TestCase):

    def test_deprecated_version(self):
        """ Test the deprecated Alignak version warning """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            import alignak.bin
            alignak.bin.VERSION
            self.assertEqual(1, len(w))
            self.assertIs(w[-1].category, DeprecationWarning)
            self.assertIn('`alignak.bin.VERSION` is deprecated version', str(w[-1].message))
