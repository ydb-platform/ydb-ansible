#! /bin/sh

ydb auth get-token -f >token.tmp
ydbd -s grpcs://ydbd-1.front.private:2135 --ca-file ydb-ca.crt --token-file token.tmp admin console execute tableprofiles.txt
