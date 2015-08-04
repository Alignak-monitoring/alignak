#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
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

import os
import re
import copy
import time
import subprocess
import shutil
import datetime # not used but "sub-"imported by livestatus test.. (to be corrected..)
import sys # not here used but "sub-"imported by livestatus test.. (to be corrected..)

#
from alignak.modulesctx import modulesctx
from alignak.objects.module import Module
from alignak.modulesmanager import ModulesManager
from alignak.misc.datamanager import datamgr
from alignak.log import logger

#
from alignak_test import (
    modules_dir,
    AlignakTest,
    time_hacker, # not used here but "sub"-imported by lvestatus test (to be corrected)
)

modulesctx.set_modulesdir(modules_dir)


# Special Livestatus module opening since the module rename
#from alignak.modules.livestatus import module as livestatus_broker
livestatus_broker = modulesctx.get_module('livestatus')
LiveStatus_broker = livestatus_broker.LiveStatus_broker
LiveStatus = livestatus_broker.LiveStatus
LiveStatusRegenerator = livestatus_broker.LiveStatusRegenerator
LiveStatusQueryCache = livestatus_broker.LiveStatusQueryCache
LiveStatusClientThread = livestatus_broker.LiveStatusClientThread

Logline = livestatus_broker.Logline
LiveStatusLogStoreMongoDB = modulesctx.get_module('logstore-mongodb').LiveStatusLogStoreMongoDB
LiveStatusLogStoreSqlite = modulesctx.get_module('logstore-sqlite').LiveStatusLogStoreSqlite

livestatus_modconf = Module()
livestatus_modconf.module_name = "livestatus"
livestatus_modconf.module_type = livestatus_broker.properties['type']
livestatus_modconf.properties = livestatus_broker.properties.copy()



class AlignakModulesTest(AlignakTest):

    def do_load_modules(self):
        self.modules_manager.load_and_init()
        self.log.log("I correctly loaded the modules: [%s]" % (','.join([inst.get_name() for inst in self.modules_manager.instances])))

    def update_broker(self, dodeepcopy=False):
        # The brok should be manage in the good order
        ids = self.sched.brokers['Default-Broker']['broks'].keys()
        ids.sort()
        for brok_id in ids:
            brok = self.sched.brokers['Default-Broker']['broks'][brok_id]
            #print "Managing a brok type", brok.type, "of id", brok_id
            #if brok.type == 'update_service_status':
            #    print "Problem?", brok.data['is_problem']
            if dodeepcopy:
                brok = copy.deepcopy(brok)
            brok.prepare()
            self.livestatus_broker.manage_brok(brok)
        self.sched.brokers['Default-Broker']['broks'] = {}

    def init_livestatus(self, modconf=None, dbmodconf=None, needcache=False):
        self.livelogs = 'tmp/livelogs.db' + self.testid

        if modconf is None:
            modconf = Module({'module_name': 'LiveStatus',
                'module_type': 'livestatus',
                'port': str(50000 + os.getpid()),
                'pnp_path': 'tmp/pnp4nagios_test' + self.testid,
                'host': '127.0.0.1',
                'socket': 'live',
                'name': 'test', #?
            })

        if dbmodconf is None:
            dbmodconf = Module({'module_name': 'LogStore',
                'module_type': 'logstore_sqlite',
                'use_aggressive_sql': "0",
                'database_file': self.livelogs,
                'archive_path': os.path.join(os.path.dirname(self.livelogs), 'archives'),
            })

        modconf.modules = [dbmodconf]
        self.livestatus_broker = LiveStatus_broker(modconf)
        self.livestatus_broker.create_queues()

        #--- livestatus_broker.main
        self.livestatus_broker.log = logger
        # this seems to damage the logger so that the scheduler can't use it
        #self.livestatus_broker.log.load_obj(self.livestatus_broker)
        self.livestatus_broker.debug_output = []
        self.livestatus_broker.modules_manager = ModulesManager('livestatus', modules_dir, [])
        self.livestatus_broker.modules_manager.set_modules(self.livestatus_broker.modules)
        # We can now output some previouly silented debug ouput
        self.livestatus_broker.do_load_modules()
        for inst in self.livestatus_broker.modules_manager.instances:
            if inst.properties["type"].startswith('logstore'):
                f = getattr(inst, 'load', None)
                if f and callable(f):
                    f(self.livestatus_broker)  # !!! NOT self here !!!!
                break
        for s in self.livestatus_broker.debug_output:
            print "errors during load", s
        del self.livestatus_broker.debug_output
        self.livestatus_broker.rg = LiveStatusRegenerator()
        self.livestatus_broker.datamgr = datamgr
        datamgr.load(self.livestatus_broker.rg)
        self.livestatus_broker.query_cache = LiveStatusQueryCache()
        if not needcache:
            self.livestatus_broker.query_cache.disable()
        self.livestatus_broker.rg.register_cache(self.livestatus_broker.query_cache)
        #--- livestatus_broker.main

        self.livestatus_broker.init()
        self.livestatus_broker.db = self.livestatus_broker.modules_manager.instances[0]
        self.livestatus_broker.livestatus = LiveStatus(self.livestatus_broker.datamgr, self.livestatus_broker.query_cache, self.livestatus_broker.db, self.livestatus_broker.pnp_path, self.livestatus_broker.from_q)

        #--- livestatus_broker.do_main
        self.livestatus_broker.db.open()
        if hasattr(self.livestatus_broker.db, 'prepare_log_db_table'):
            self.livestatus_broker.db.prepare_log_db_table()
        #--- livestatus_broker.do_main


class TestConfig(AlignakModulesTest):

    def tearDown(self):
        self.livestatus_broker.db.close()
        if os.path.exists(self.livelogs):
            os.remove(self.livelogs)
        if os.path.exists(self.livelogs + "-journal"):
            os.remove(self.livelogs + "-journal")
        if os.path.exists(self.livestatus_broker.pnp_path):
            shutil.rmtree(self.livestatus_broker.pnp_path)
        if os.path.exists('var/alignak.log'):
            os.remove('var/alignak.log')
        if os.path.exists('var/retention.dat'):
            os.remove('var/retention.dat')
        if os.path.exists('var/status.dat'):
            os.remove('var/status.dat')
        self.livestatus_broker = None


    def contains_line(self, text, pattern):
        regex = re.compile(pattern)
        for line in text.splitlines():
            if re.search(regex, line):
                return True
        return False

    def update_broker(self, dodeepcopy=False):
        # The brok should be manage in the good order
        ids = self.sched.brokers['Default-Broker']['broks'].keys()
        ids.sort()
        for brok_id in ids:
            brok = self.sched.brokers['Default-Broker']['broks'][brok_id]
            #print "Managing a brok type", brok.type, "of id", brok_id
            #if brok.type == 'update_service_status':
            #    print "Problem?", brok.data['is_problem']
            if dodeepcopy:
                brok = copy.deepcopy(brok)
            brok.prepare()
            self.livestatus_broker.manage_brok(brok)
        self.sched.brokers['Default-Broker']['broks'] = {}

    def lines_equal(self, text1, text2):
        # gets two multiline strings and compares the contents
        # lifestatus output may not be in alphabetical order, so this
        # function is used to compare unordered output with unordered
        # expected output
        # sometimes mklivestatus returns 0 or 1 on an empty result
        text1 = text1.replace("200           1", "200           0")
        text2 = text2.replace("200           1", "200           0")
        text1 = text1.rstrip()
        text2 = text2.rstrip()
        #print "text1 //%s//" % text1
        #print "text2 //%s//" % text2
        sorted1 = "\n".join(sorted(text1.split("\n")))
        sorted2 = "\n".join(sorted(text2.split("\n")))
        len1 = len(text1.split("\n"))
        len2 = len(text2.split("\n"))
        #print "%s == %s text cmp %s" % (len1, len2, sorted1 == sorted2)
        #print "text1 //%s//" % sorted(text1.split("\n"))
        #print "text2 //%s//" % sorted(text2.split("\n"))
        if sorted1 == sorted2 and len1 == len2:
            return True
        else:
            # Maybe list members are different
            # allhosts;test_host_0;test_ok_0;servicegroup_02,servicegroup_01,ok
            # allhosts;test_host_0;test_ok_0;servicegroup_02,ok,servicegroup_01
            # break it up to
            # [['allhosts'], ['test_host_0'], ['test_ok_0'],
            #     ['ok', 'servicegroup_01', 'servicegroup_02']]
            [line for line in sorted(text1.split("\n"))]
            data1 = [[sorted(c.split(',')) for c in columns] for columns in [line.split(';') for line in sorted(text1.split("\n")) if line]]
            data2 = [[sorted(c.split(',')) for c in columns] for columns in [line.split(';') for line in sorted(text2.split("\n")) if line]]
            #print "text1 //%s//" % data1
            #print "text2 //%s//" % data2
            # cmp is clever enough to handle nested arrays
            return cmp(data1, data2) == 0

    def show_broks(self, title):
        print
        print "--- ", title
        for brok in sorted(self.sched.broks.values(), lambda x, y: x._id - y._id):
            if re.compile('^service_').match(brok.type):
                pass
                #print "BROK:", brok.type
                #print "BROK   ", brok.data['in_checking']
        self.update_broker()
        request = 'GET services\nColumns: service_description is_executing\n'
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response

ShinkenModulesTest = AlignakModulesTest
