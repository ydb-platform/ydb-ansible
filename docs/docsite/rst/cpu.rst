==================================
CPU usage
==================================

Overview
--------

By default YDB is using all available cores. There're several way to split available cores between YDB instances:
- define number of cores for different types of instances
- pin exactly core to instances

V2 Config::

    These settings don't work with YDB V2 Configuration.

1. Setting cores for instances
------------------------------

It's possible to define how many cores can be used by YDB instances by using Ansible variables:

+---------------------+------------------------------------------------------------------+
| Variable            | Description                                                      |
+=====================+==================================================================+
| `ydb_cores_static`  | Number of cores to be used by thread pools of the storage nodes  |
+---------------------+------------------------------------------------------------------+
| `ydb_cores_dynamic` | Number of cores to be used by thread pools of the database nodes |
+---------------------+------------------------------------------------------------------+

If your server has more than 16 CPU cores, increase these so they sum up to the actual available number. If you have over 64 cores per server, consider running multiple database nodes per server.

`available_cores >= ydb_cores_static + ydb_cores_dynamic * number_of_dynnodes_per_server`

Example inventory::

    ydb_cores_static: 8
    ydb_cores_dynamic: 8

2. Pin cores to instances
------------------------------

CPU affinity settings help you restrict the access of a particular process to some CPUs. Effectively, the CPU scheduler never schedules the process to run on the CPU that is not in the affinity mask of the process.
The default CPU affinity mask applies to all services managed by systemd. Ansible collection helps to configure CPUAffinity option.

+-------------------------+------------------------------------------------------------------+
| Variable                | Description                                                      |
+=========================+==================================================================+
| ydb_affinity_static     | affinity mask for YDB storage instance                           |
+-------------------------+------------------------------------------------------------------+
| ydb_dynnodes[.affinity] | affinity mask for YDB dynamic instance for specific DB.          |
+-------------------------+------------------------------------------------------------------+

You can find out which processor cores belong to which numa nodes using lscpu or `numactl --hardware` or `lscpu --extended=CPU,NODE`.

Example inventory::

    ydb_affinity_static: "1,2"
    ydb_dynnodes:
        - {"instance": "a", offset: 1, dbname: "db", affinity: "3,4"}
        - {"instance": "b", offset: 2, dbname: "db", affinity: "5,6"}
        - {"instance": "c", offset: 3, dbname: "db2", affinity: "7,8"}
