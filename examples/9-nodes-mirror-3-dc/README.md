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
4. Encrypt `inventory/99-inventory-vault.yaml` with `ansible-vault encrypt inventory/99-inventory-vault.yaml` command. To edit this file use command `ansible-vault edit inventory/99-inventory-vault.yaml`
5. Download ydb archive and put it in `files/` directory
