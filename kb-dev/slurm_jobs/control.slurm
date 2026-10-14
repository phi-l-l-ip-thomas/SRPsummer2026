#!/bin/bash

#SCRON --job-name=control
#SCRON -q cron
#SCRON -C cron
#SCRON -A m5128
#SCRON -t 1-00:00:00
#SCRON -o /global/cfs/cdirs/m5128/kbilal/interface/control.%j.out
#SCRON --open-mode=append

*/2 * * * * cd /global/cfs/cdirs/m5128/kbilal/interface && scripts/checkpoint.sh