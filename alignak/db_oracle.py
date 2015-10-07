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
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#
#  Copyright (C) 2009-2014:
#     xkilian, fmikus@acktomic.com
#     Hartmut Goebel, h.goebel@goebel-consult.de
#     Nicolas Dupeux, nicolas@dupeux.net
#     Grégory Starck, g.starck@gmail.com
#     Sebastien Coavoux, s.coavoux@free.fr
#     Thibault Cohen, titilambert@gmail.com
#     Jean Gabes, naparuba@gmail.com
#     Zoran Zaric, zz@zoranzaric.de

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
"""This module provide DBOracle class to access Oracle databases

"""
# Failed to import will be catch by __init__.py
from cx_Oracle import connect as connect_function
from cx_Oracle import IntegrityError as IntegrityError_exp
from cx_Oracle import ProgrammingError as ProgrammingError_exp
from cx_Oracle import DatabaseError as DatabaseError_exp
from cx_Oracle import InternalError as InternalError_exp
from cx_Oracle import DataError as DataError_exp
from cx_Oracle import OperationalError as OperationalError_exp

from alignak.db import DB
from alignak.log import logger


class DBOracle(DB):
    """Manage connection and query execution against Oracle databases."""

    def __init__(self, user, password, database, table_prefix=''):
        super(DBOracle, self).__init__(table_prefix)
        self.user = user
        self.password = password
        self.database = database

    def connect_database(self):
        """Create the database connection

        :return: None
        TODO: finish (begin :) ) error catch and conf parameters...
        """
        connstr = '%s/%s@%s' % (self.user, self.password, self.database)

        self.db = connect_function(connstr)  # pylint: disable=C0103
        self.db_cursor = self.db.cursor()
        self.db_cursor.arraysize = 50

    def execute_query(self, query):
        """ Execute a query against an Oracle database.

        :param query: the query
        :type query: str
        :return: None
        """
        logger.debug("[DBOracle] Execute Oracle query %s\n", query)
        try:
            self.db_cursor.execute(query)
            self.db.commit()
        except IntegrityError_exp, exp:
            logger.warning("[DBOracle] Warning: a query raise an integrity error: %s, %s",
                           query, exp)
        except ProgrammingError_exp, exp:
            logger.warning("[DBOracle] Warning: a query raise a programming error: %s, %s",
                           query, exp)
        except DatabaseError_exp, exp:
            logger.warning("[DBOracle] Warning: a query raise a database error: %s, %s",
                           query, exp)
        except InternalError_exp, exp:
            logger.warning("[DBOracle] Warning: a query raise an internal error: %s, %s",
                           query, exp)
        except DataError_exp, exp:
            logger.warning("[DBOracle] Warning: a query raise a data error: %s, %s",
                           query, exp)
        except OperationalError_exp, exp:
            logger.warning("[DBOracle] Warning: a query raise an operational error: %s, %s",
                           query, exp)
        except Exception, exp:
            logger.warning("[DBOracle] Warning: a query raise an unknown error: %s, %s",
                           query, exp)
            logger.warning(exp.__dict__)
