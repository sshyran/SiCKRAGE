#!/usr/bin/env python2.7
# Author: echel0n <echel0n@sickrage.ca>
# URL: https://sickrage.ca
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, unicode_literals

import unittest

from sickrage.core.helpers import clean_url
from tests import SiCKRAGETestCase


class QualityTests(SiCKRAGETestCase):
    def test_clean_url(self):
        self.assertEqual(clean_url("https://subdomain.domain.tld/endpoint"),
                         "https://subdomain.domain.tld/endpoint")
        self.assertEqual(clean_url("google.com/xml.rpc"), "http://google.com/xml.rpc")
        self.assertEqual(clean_url("google.com"), "http://google.com/")
        self.assertEqual(clean_url("http://www.example.com/folder/"), "http://www.example.com/folder/")
        self.assertEqual(clean_url("scgi:///home/user/.config/path/socket"),
                         "scgi:///home/user/.config/path/socket")


if __name__ == '__main__':
    print("==================")
    print("STARTING - CONFIG TESTS")
    print("==================")
    print("######################################################################")
    unittest.main()
