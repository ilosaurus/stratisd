# Copyright 2016 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Test adding blockdevs to a pool.
"""

from stratisd_client_dbus import Manager
from stratisd_client_dbus import ObjectManager
from stratisd_client_dbus import Pool
from stratisd_client_dbus import StratisdErrors
from stratisd_client_dbus import blockdevs
from stratisd_client_dbus import get_object
from stratisd_client_dbus import pools

from stratisd_client_dbus._constants import TOP_OBJECT

from .._misc import SimTestCase
from .._misc import device_name_list

_DEVICE_STRATEGY = device_name_list(1)


class AddDataDevsTestCase(SimTestCase):
    """
    Test adding devices to a pool which is initially empty.
    """

    _POOLNAME = "deadpool"

    def setUp(self):
        """
        Start the stratisd daemon with the simulator.
        """
        super().setUp()
        self._proxy = get_object(TOP_OBJECT)
        ((poolpath, _), _, _) = Manager.Methods.CreatePool(
            self._proxy,
            {"name": self._POOLNAME, "redundancy": (True, 0), "devices": []},
        )
        self._pool_object = get_object(poolpath)
        Manager.Methods.ConfigureSimulator(self._proxy, {"denominator": 8})

    def testEmptyDevs(self):
        """
        Adding an empty list of devs should leave the pool empty.
        """
        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})
        (pool, _) = next(pools(props={"Name": self._POOLNAME}).search(managed_objects))

        blockdevs1 = blockdevs(props={"Pool": pool}).search(managed_objects)
        self.assertEqual(list(blockdevs1), [])

        (result, rc, _) = Pool.Methods.AddDataDevs(self._pool_object, {"devices": []})

        self.assertEqual(result, [])
        self.assertEqual(rc, StratisdErrors.OK)

        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})
        blockdevs2 = blockdevs(props={"Pool": pool}).search(managed_objects)
        self.assertEqual(list(blockdevs2), [])

        blockdevs3 = blockdevs(props={}).search(managed_objects)
        self.assertEqual(list(blockdevs3), [])

    def testSomeDevs(self):
        """
        Adding a non-empty list of devs should increase the number of devs
        in the pool.
        """
        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})
        (pool, _) = next(pools(props={"Name": self._POOLNAME}).search(managed_objects))

        blockdevs1 = blockdevs(props={"Pool": pool}).search(managed_objects)
        self.assertEqual(list(blockdevs1), [])

        (result, rc, _) = Pool.Methods.AddDataDevs(
            self._pool_object, {"devices": _DEVICE_STRATEGY()}
        )

        num_devices_added = len(result)
        managed_objects = ObjectManager.Methods.GetManagedObjects(self._proxy, {})

        if rc == StratisdErrors.OK:
            self.assertGreater(num_devices_added, 0)
        else:
            self.assertEqual(num_devices_added, 0)

        blockdev_object_paths = frozenset(result)

        # blockdevs exported on the D-Bus are exactly those added
        blockdevs2 = list(blockdevs(props={"Pool": pool}).search(managed_objects))
        blockdevs2_object_paths = frozenset([op for (op, _) in blockdevs2])
        self.assertEqual(blockdevs2_object_paths, blockdev_object_paths)

        # no duplicates in the object paths
        self.assertEqual(len(blockdevs2), num_devices_added)

        # There are no blockdevs but for those in this pool
        blockdevs3 = blockdevs(props={}).search(managed_objects)
        self.assertEqual(len(list(blockdevs3)), num_devices_added)

        # There are no cachedevs belonging to this pool
        blockdevs4 = blockdevs(props={"Pool": pool, "Tier": 1}).search(managed_objects)
        self.assertEqual(list(blockdevs4), [])
