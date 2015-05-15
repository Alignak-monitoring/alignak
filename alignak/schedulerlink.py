'''alignak.schedulerlink is deprecated. Please use alignak.objects.schedulerlink now.'''

from alignak.old_daemon_link import make_deprecated_daemon_link

from alignak.objects import schedulerlink


make_deprecated_daemon_link(schedulerlink)
