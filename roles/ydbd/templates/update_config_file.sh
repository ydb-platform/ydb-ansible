#! /bin/sh
# Update the YDB cluster configuration file.

set +e
set +u

YDB_DIR="{{ ydb_dir }}"
CONF_SRC=${YDB_DIR}/cfg/"$1"
CONF_DST=${YDB_DIR}/cfg/"$2"
CONF_MODE="$3"
CONF_CORES="$4"

set -e
set -u

cp -v ${CONF_SRC} ${CONF_DST}
COUNT=`grep -E '^[ ]*actor_system_config:[ ]*' ${CONF_DST} | wc -l | (read x && echo $x)`
if [ $COUNT -gt 0 ]; then
  echo "ERROR: actor system config already defined in $CONF_SRC" >&2
  exit 1
fi

cat >>${CONF_DST} <<EOF
actor_system_config:
  use_auto_config: true
  node_type: $CONF_MODE
  cpu_count: $CONF_CORES
EOF

chown root:ydb ${CONF_DST}
chmod 440 $CONF_DST

# End Of File