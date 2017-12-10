import pytest
from alignak_test import AlignakTest
from alignak.util import generate_key_value_sequences, KeyValueSyntaxError


class ServiceDescriptionDuplicateForEach(AlignakTest):

    def setUp(self):
        self.setup_with_file('cfg/cfg_service_description_duplicate_foreach.cfg')
        self._sched = self.schedulers['scheduler-master'].sched

    def test_simple_get_key_value_sequence(self):
        rsp = list(generate_key_value_sequences("1", "default42"))
        expected = [
            {'VALUE': 'default42', 'VALUE1': 'default42', 'KEY': '1'},
        ]
        assert expected == rsp

    def test_not_simple_get_key_value_sequence(self):
        rsp = list(generate_key_value_sequences("1  $(val1)$, 2 $(val2)$ ", "default42"))
        expected = [
            {'VALUE': 'val1', 'VALUE1': 'val1', 'KEY': '1'},
            {'VALUE': 'val2', 'VALUE1': 'val2', 'KEY': '2'},
        ]
        assert expected == rsp

    def test_all_duplicate_ok(self):
        host = self._sched.hosts.find_by_name("my_host")
        services_desc = set(self._sched.services[s].service_description for s in host.services)
        expected = set(map(lambda i: 'Generated Service %s' % i, range(1, 4)))
        assert expected == services_desc

    def test_complex(self):
        rsp = list(generate_key_value_sequences('Unit [1-6] Port [0-46]$(80%!90%)$,Unit [1-6] Port 47$(80%!90%)$', ''))
        assert 288 == len(rsp)

    def test_sytnax_error_bad_empty_value(self):
        generator = generate_key_value_sequences('', '')
        with pytest.raises(KeyValueSyntaxError) as ctx:
            list(generator)
        assert ctx.value.args[0] == "At least one key must be present"

    def test_sytnax_error_bad_empty_value_with_comma(self):
        generator = generate_key_value_sequences(',', '')
        with pytest.raises(KeyValueSyntaxError) as ctx:
            list(generator)
        assert ctx.value.args[0] == "At least one key must be present"

    def test_syntax_error_bad_value(self):
        generator = generate_key_value_sequences("key $(but bad value: no terminating dollar sign)", '')
        with pytest.raises(KeyValueSyntaxError) as ctx:
            list(generator)
        assert ctx.value.args[0] == "\'key $(but bad value: no terminating dollar sign)\' " \
                                    "is an invalid key(-values) pattern"







