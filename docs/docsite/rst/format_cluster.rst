==================================
Format cluster
==================================

This manual is intended for testing purposes only. Be careful when using it.
This will destroy ALL DATA on all drives defined in inventory
This will delete all `bin` and `cfg` folders for YDB on hosts

When to use it
---------------------

It's useful when you try to reinstall previous installation of the YDB cluster.
Notes::

    It doesn't remove /opt/ydb/release folder with binaries for different YDB releases.
    You have to delete them manually if you what to use new binaries for previously used YDB version (for example, new version of any tool).
    Possible solution:
    ```
    ansible-console ydb
    $> sudo rm -rf /opt/ydb/release
    ```

How to use it
---------------------

Process all hosts:

    ansible-playbook ydb-platform.ydb.format_cluster

Process only one host

    ansible-playbook ydb-platform.ydb.format_cluster -l static-node-1.ydb-cluster.com

Process only one host group

    ansible-playbook ydb-platform.ydb.format_cluster -l current-hosts

How it works
---------------------

Steps:
- Stop all services with 'ydbd' in name
- Remove folder for configs (default: /opt/ydb/cfg)
- Remove folder for binary files (default: /opt/ydb/bin)
- Remove all ydbd-* named files in /etc/systemd/system/ and reload systemd daemon
- Run `dd` for every drive mentioned in inventory
