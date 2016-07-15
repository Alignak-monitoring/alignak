
import sys

if sys.version_info[:2] < (2,7):
    import unittest2 as unittest
else:
    import unittest


def clean_sys_modules():
    for k in list(sys.modules):
        if k in ('alignak', 'shinken') or k.startswith('alignak') or k.startswith('shinken'):
            sys.modules.pop(k)


class TestImport(unittest.TestCase):

    def setUp(self):
        # if for some reason alignak would have been already imported when this
        # test is run then we have to clean some things:
        for mp in list(sys.meta_path):
            if mp.__module__ == 'alignak.shinken_import_hook':
                sys.meta_path.remove(mp)
        self.orig_meta_path = sys.meta_path[:]
        clean_sys_modules()

    def tearDown(self):
        clean_sys_modules()
        sys.meta_path = self.orig_meta_path

    def test_import(self):
        """This just makes sure that we get alignak when we import shinken"""

        # first try, without anything done, must fail:
        with self.assertRaises(ImportError):
            import shinken

        # now load alignak:
        import alignak
        # and now:
        import shinken
        self.assertIs(alignak, shinken)
        # I know, this hurts, hopefully this is temporary.

        # make sure importing a sub-module is also ok:
        import shinken.objects
        import alignak.objects
        self.assertIs(alignak.objects, shinken.objects)

        # and make sure that from .. import is also ok:
        from shinken.objects import arbiterlink as shinken_arblink
        from alignak.objects import arbiterlink as alignak_arblink
        self.assertIs(alignak_arblink, shinken_arblink)

    def test_import_unknown_raise_importerrror(self):
        with self.assertRaises(ImportError):
            import shinken
        import alignak
        with self.assertRaises(ImportError):
            import shinken.must_be_unknown
        with self.assertRaises(ImportError):
            import alignak.must_be_unknown


if __name__ == '__main__':
    unittest.main()
