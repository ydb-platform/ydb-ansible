
CREATE USER fluentbit PASSWORD "....";
GRANT CONNECT ON `/cluster1/admin` TO fluentbit;

CREATE TABLE `ydblogs` (
  `ts` Timestamp NOT NULL,
  `datahash` Uint64 NOT NULL,
  `dbname` Text NOT NULL,
  `hostname` Text NOT NULL,
  `input` Text NOT NULL,
  `ts_orig` Text,   
  `level` Text,
  `unit` Text,
  `service` Text,
  `msg` Text,
  PRIMARY KEY (
    `ts`, `datahash`, `dbname`, `hostname`, `input`
  )
) PARTITION BY HASH(`ts`, `dbname`, `hostname`, `input`)
WITH (
  STORE = COLUMN
);

GRANT USE ON `/cluster1/admin/ydblogs` TO fluentbit;
