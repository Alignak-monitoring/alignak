"""
This file is used to get all dynamic properties to add in pylint rc file to ignore these
fields
"""

import sys
import inspect
import fileinput
from alignak.objects import *
from alignak.objects.config import Config
from alignak.objects.arbiterlink import ArbiterLink, ArbiterLinks
from alignak.objects.checkmodulation import CheckModulation, CheckModulations
from alignak.objects.schedulerlink import SchedulerLink, SchedulerLinks
from alignak.action import ActionBase
from alignak.daemon import Daemon

clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)

properties = ['REQUEST' ,'acl_users', 'aq_parent']

# Properties defined in class_inherit
properties.extend(['global_low_flap_threshold', 'global_high_flap_threshold', 'log_retries',
                   'global_event_handler', 'max_check_spread',
                   'enable_predictive_dependency_checks', 'cached_check_horizon', 'check_timeout',
                   'obsess_over', 'perfdata_command', 'perfdata_file', 'perfdata_file_template',
                   'perfdata_file_mode', 'perfdata_file_processing_command', 'check_for_orphaned',
                   'global_check_freshness', 'execute_checks', 'timeperiods', 'services',
                   'servicegroups', 'commands', 'hosts', 'hostgroups', 'contacts', 'contactgroups',
                   'notificationways', 'checkmodulations', 'macromodulations',
                   'servicedependencies', 'hostdependencies', 'arbiters', 'schedulers',
                   'reactionners', 'brokers', 'receivers', 'pollers', 'realms', 'modules',
                   'resultmodulations', 'businessimpactmodulations', 'escalations',
                   'serviceescalations', 'hostescalations', 'hostsextinfo', 'servicesextinfo',
                   '_id', 'status', 'command', 't_to_go', 'timeout', 'env', 'module_type',
                   'execution_time', 'u_time', 's_time'])

for name, obj in clsmembers:
    if hasattr(obj, 'properties'):
        for p in obj.properties:
            properties.append(p)
    if hasattr(obj, 'running_properties'):
        for p in obj.running_properties:
            properties.append(p)

unique_prop = list(set(properties))

print unique_prop

for line in fileinput.input(['../.pylintrc'], inplace=True):
    if line.strip().startswith('generated-members='):
        line = 'generated-members=%s\n' % ','.join(unique_prop)
    sys.stdout.write(line)
