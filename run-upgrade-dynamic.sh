#! /bin/sh

ansible-playbook -b -i hosts -f 20 upgrade-dynamic.yaml
