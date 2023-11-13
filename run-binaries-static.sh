#! /bin/sh

ansible-playbook -b -i hosts -f 20 binaries-static.yaml
