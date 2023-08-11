# 9 node example

Steps to reproduce

1. Create inventory directory.
2. Create `inventory/50-inventory.yaml` file. Add inventory content in that file.
3. Create `inventory/99-inventory-vault.yaml` file. Put secrets in that file, example:
    ```
    $ cat inventory/99-inventory-vault.yaml
    all:
      children:
        ydb:
          vars:
            ydb_password: password

    ```
4. Download YDB archive and put it in `files/` directory.
5. Create YDB configuraiton and put it in `files/` directory.
6. Create certificates using YDB-ca-update.sh script and put it in `files/` directory.
7. Put ssh keys in `files/` directory.
8. Build ansible docker container with `make build` command (make and docker must be installed).
9. Start ansible docker container with `make run` command.
10. Encrypt `inventory/99-inventory-vault.yaml` with `ansible-vault encrypt inventory/99-inventory-vault.yaml` command. To edit this file use command `ansible-vault edit inventory/99-inventory-vault.yaml`.
11. Run playbook with `ansible-playbook setup_playbook.yaml` command.
