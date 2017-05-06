# -*- coding: utf-8 -*-

#
# Copyright (C) 2015-2016: Alignak team, see AUTHORS.txt file for contributors
#
# This file is part of Alignak.
#
# Alignak is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alignak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Alignak.  If not, see <http://www.gnu.org/licenses/>.
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     xkilian, fmikus@acktomic.com
#     Pradeep Jindal, praddyjindal@gmail.com
#     aviau, alexandre.viau@savoirfairelinux.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Andrus Viik, andrus@a7k.pri.ee
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com

#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.
"""This module provide a set of function for triggers
Basically used to handle perfdata, exit status and output

"""
import time
import re
import logging

from alignak.misc.perfdata import PerfDatas
from alignak.objects.host import Hosts
from alignak.objects.service import Services
from alignak.objects.timeperiod import Timeperiods
from alignak.objects.macromodulation import MacroModulations
from alignak.objects.checkmodulation import CheckModulations

logger = logging.getLogger(__name__)  # pylint: disable=C0103

OBJS = {'hosts': Hosts({}), 'services': Services({}), 'timeperiods': Timeperiods({}),
        'macromodulations': MacroModulations({}), 'checkmodulations': CheckModulations({}),
        'checks': {}}
TRIGGER_FUNCTIONS = {}


def declared(function):
    """ Decorator to add function in trigger environment

    :param function: function to add to trigger environment
    :type function: types.FunctionType
    :return : the function itself only update TRIGGER_FUNCTIONS variable
    """
    name = function.func_name
    TRIGGER_FUNCTIONS[name] = function
    logger.debug("Added %s to trigger functions list ", name)
    return function


@declared
def up(obj, output):  # pylint: disable=C0103
    """ Set a host in UP state

    :param obj: object
    :type obj: object
    :param output:
    :type output:
    :return: None
    """
    set_value(obj, output, None, 0)


@declared
def down(obj, output):
    """ Set a host in DOWN state

    :param obj: object
    :type obj: object
    :param output:
    :type output:
    :return: None
    """
    set_value(obj, output, None, 1)


@declared
def ok(obj, output):  # pylint: disable=C0103
    """ Set a service in OK state

    :param obj: object
    :type obj: object
    :param output:
    :type output:
    :return: None
    """
    set_value(obj, output, None, 0)


@declared
def warning(obj, output):
    """ Set a service in WARNING state

    :param obj: object
    :type obj: object
    :param output:
    :type output:
    :return: None
    """
    set_value(obj, output, None, 1)


@declared
def critical(obj, output):
    """ Set a service in CRITICAL state

    :param obj: object
    :type obj: object
    :param output:
    :type output:
    :return: None
    """
    set_value(obj, output, None, 2)


@declared
def unknown(obj, output):
    """ Set a service in UNKNOWN state

    :param obj: object
    :type obj: object
    :param output:
    :type output:
    :return: None
    """
    set_value(obj, output, None, 3)


@declared
def set_value(obj_ref, output=None, perfdata=None, return_code=None):
    """ Set output, state and perfdata to a service or host

    :param obj_ref:
    :type obj_ref: object
    :param output:
    :type output: None | str
    :param perfdata:
    :type perfdata: None | str
    :param return_code:
    :type return_code: None | int
    :return: None
    """
    obj = get_object(obj_ref)
    if not obj:
        return
    output = output or obj.output
    perfdata = perfdata or obj.perf_data
    if return_code is None:
        return_code = obj.state_id

    logger.debug("[trigger] Setting %s %s %s for object %s",
                 output,
                 perfdata,
                 return_code,
                 obj.get_full_name())

    if perfdata:
        output = output + ' | ' + perfdata

    now = time.time()

    chk = obj.launch_check(now, OBJS['hosts'], OBJS['services'], OBJS['timeperiods'],
                           OBJS['macromodulations'], OBJS['checkmodulations'],
                           OBJS['checks'], force=True)
    if chk is None:
        logger.debug("[trigger] %s > none check launched", obj.get_full_name())
    else:
        logger.debug("[trigger] %s > I found the check I want to change",
                     obj.get_full_name())
        # Now we 'transform the check into a result'
        # So exit_status, output and status is eaten by the host
        chk.exit_status = return_code
        chk.get_outputs(output, obj.max_plugins_output_length)
        chk.status = 'waitconsume'
        chk.check_time = now
        # IMPORTANT: tag this check as from a trigger, so we will not
        # loop in an infinite way for triggers checks!
        chk.from_trigger = True
        # Ok now this result will be read by scheduler the next loop


@declared
def perf(obj_ref, metric_name):
    """ Get perf data from a service

    :param obj_ref:
    :type obj_ref: object
    :param metric_name:
    :type metric_name: str
    :return: None
    """
    obj = get_object(obj_ref)
    perfdata = PerfDatas(obj.perf_data)
    if metric_name in perfdata:
        logger.debug("[trigger] I found the perfdata")
        return perfdata[metric_name].value
    logger.debug("[trigger] I am in perf command")
    return None


@declared
def get_custom(obj_ref, cname, default=None):
    """ Get custom variable from a service or a host

    :param obj_ref:
    :type obj_ref: object
    :param cname:
    :type cname: str
    :param default:
    :type default:
    :return:
    :rtype:
    """
    print obj_ref
    objs = get_objects(obj_ref)
    print objs
    if len(objs) != 1:
        return default
    obj = objs[0]
    if not obj:
        return default
    cname = cname.upper().strip()
    if not cname.startswith('_'):
        cname = '_' + cname
    return obj.customs.get(cname, default)


@declared
def perfs(objs_ref, metric_name):
    """ Get the same performance data metric from multiple services/hosts

    :param objs_ref:
    :type objs_ref: object
    :param metric_name:
    :type metric_name: str
    :return: list of metrics
    :rtype: list
    """
    objs = get_objects(objs_ref)
    res = []
    for obj in objs:
        val = perf(obj, metric_name)
        res.append(val)
    return res


@declared
def allperfs(obj_ref):
    """ Get all perfdatas from a service or a host

    :param obj_ref:
    :type obj_ref: object
    :return: dictionary with perfdatas
    :rtype: dict
    """
    obj = get_object(obj_ref)
    perfdata = PerfDatas(obj.perf_data)
    logger.debug("[trigger] I get all perfdatas")
    return dict([(metric.name, perfdata[metric.name]) for metric in perfdata])


@declared
def get_object(ref):
    """ Retrieve object (service/host) from name

    :param ref:
    :type ref:
    :return:
    :rtype:
    """
    # Maybe it's already a real object, if so, return it :)
    if not isinstance(ref, basestring):
        return ref

    # If it is an object uuid, get the real object and return it :)
    if ref in OBJS['hosts']:
        return OBJS['hosts'][ref]
    if ref in OBJS['services']:
        return OBJS['services'][ref]

    # Ok it's a string
    name = ref
    if '/' not in name:
        return OBJS['hosts'].find_by_name(name)
    else:
        elts = name.split('/', 1)
        return OBJS['services'].find_srv_by_name_and_hostname(elts[0], elts[1])


@declared
def get_objects(ref):
    """ TODO: check this description
        Retrieve objects (service/host) from names

    :param ref:
    :type ref:
    :return: list of object (service/host)
    :rtype: list
    """
    # Maybe it's already a real object, if so, return it :)
    if not isinstance(ref, basestring):
        return [ref]

    # If it is an object uuid, get the real object and return it :)
    if ref in OBJS['hosts']:
        return [OBJS['hosts'][ref]]
    if ref in OBJS['services']:
        return [OBJS['services'][ref]]

    name = ref
    # Maybe there is no '*'? if so, it's one element
    if '*' not in name:
        return [get_object(name)]

    # Ok we look for splitting the host or service thing
    hname = ''
    sdesc = ''
    if '/' not in name:
        hname = name
    else:
        elts = name.split('/', 1)
        hname = elts[0]
        sdesc = elts[1]
    logger.debug("[trigger get_objects] Look for %s %s", hname, sdesc)
    hosts = []
    services = []

    # Look for host, and if need, look for service
    if '*' not in hname:
        host = OBJS['hosts'].find_by_name(hname)
        if host:
            hosts.append(host)
    else:
        hname = hname.replace('*', '.*')
        regex = re.compile(hname)
        for host in OBJS['hosts']:
            logger.debug("[trigger] Compare %s with %s", hname, host.get_name())
            if regex.search(host.get_name()):
                hosts.append(host)

    # Maybe the user ask for only hosts :)
    if not sdesc:
        return hosts

    for host in hosts:
        if '*' not in sdesc:
            serv = OBJS['services'].find_by_name(sdesc)
            if serv:
                services.append(serv)
        else:
            sdesc = sdesc.replace('*', '.*')
            regex = re.compile(sdesc)
            for serv_id in host.services:
                serv = OBJS['services'][serv_id]
                logger.debug("[trigger] Compare %s with %s", serv.service_description, sdesc)
                if regex.search(serv.service_description):
                    services.append(serv)

    logger.debug("Found the following services: %s", services)
    return services
