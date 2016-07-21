# -*- coding: utf-8 -*-

# Copyright (C) 2015:
# Thibault Cohen, titilambert@gmail.com
#
# This file is part of Alignak
#
# Alignak is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alignak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Alignak. If not, see <http://www.gnu.org/licenses/>.

"""
This module job is to get configuration data from Surveil
"""

import time

from alignak.basemodule import BaseModule
from alignak.log import logger

properties = {
    # Which daemon can load this module
    'daemons': ['scheduler'],
    # name of the module type ; to distinguish between them:
    'type': 'example',
     # is the module "external" (external means here a daemon module)
    'external': True,
    # Possible configuration phases where the module is involved:
    'phases': ['configuration', 'late_configuration', 'running', 'retention'],
}


def get_instance(mod_conf):
    logger.info("[schedulerexample] Example module %s",
                mod_conf.get_name())
    instance = Schedulerexample(mod_conf)
    return instance


class Schedulerexample(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)

    def init(self):
        logger.info("[Dummy Arbiter] Initialization of the dummy arbiter module")
        pass
