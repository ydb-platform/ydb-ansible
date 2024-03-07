#! /bin/sh

echo "always" > /sys/kernel/mm/transparent_hugepage/enabled
echo "defer+madvise" > /sys/kernel/mm/transparent_hugepage/defrag
echo "0" > /sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none
