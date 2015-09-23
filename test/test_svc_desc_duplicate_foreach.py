from alignak_test import *
from alignak.util import generate_key_value_sequences, KeyValueSyntaxError


class ServiceDescriptionDuplicateForEach(AlignakTest):

    def setUp(self):
        self.setup_with_file(['etc/test_service_description_duplicate_foreach.cfg'])

    def test_simple_get_key_value_sequence(self):
        rsp = list(generate_key_value_sequences("1", "default42"))
        expected = [
            {'VALUE': 'default42', 'VALUE1': 'default42', 'KEY': '1'},
        ]
        self.assertEqual(expected, rsp)

    def test_not_simple_get_key_value_sequence(self):
        rsp = list(generate_key_value_sequences("1  $(val1)$, 2 $(val2)$ ", "default42"))
        expected = [
            {'VALUE': 'val1', 'VALUE1': 'val1', 'KEY': '1'},
            {'VALUE': 'val2', 'VALUE1': 'val2', 'KEY': '2'},
        ]
        self.assertEqual(expected, rsp)

    def test_all_duplicate_ok(self):
        host = self.sched.hosts.find_by_name("my_host")
        services_desc = set(s.service_description for s in host.services)
        expected = set(map(lambda i: 'Generated Service %s' % i, range(1, 4)))
        self.assertEqual(expected, services_desc)

    def test_complex(self):
        rsp = list(generate_key_value_sequences('Unit [1-6] Port [0-46]$(80%!90%)$,Unit [1-6] Port 47$(80%!90%)$', ''))
        self.assertEqual(288, len(rsp))

    def test_sytnax_error_bad_empty_value(self):
        generator = generate_key_value_sequences('', '')
        with self.assertRaises(KeyValueSyntaxError) as ctx:
            list(generator)
        self.assertEqual(ctx.exception.message, "At least one key must be present")

    def test_sytnax_error_bad_empty_value_with_comma(self):
        generator = generate_key_value_sequences(',', '')
        with self.assertRaises(KeyValueSyntaxError) as ctx:
            list(generator)
        self.assertEqual(ctx.exception.message, "At least one key must be present")

    def test_syntax_error_bad_value(self):
        generator = generate_key_value_sequences("key $(but bad value: no terminating dollar sign)", '')
        with self.assertRaises(KeyValueSyntaxError) as ctx:
            list(generator)
        self.assertEqual('\'key $(but bad value: no terminating dollar sign)\' is an invalid key(-values) pattern',
                         ctx.exception.message)






