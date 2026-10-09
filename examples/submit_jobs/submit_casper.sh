#!/bin/bash -l

#PBS -N mm_eval
#PBS -q casper
#PBS -l select=1:ncpus=1:mem=64GB
#PBS -l walltime=05:00:00
#PBS -j oe
# -- Update to your project code
#PBS -A PXXXXXXXX

# PBS example for NCAR Casper. See submit_hera.sh for the Slurm equivalent.

# -- Update to your conda environment
module load conda
conda activate melodies-monet

# -- Update to the location of your run script
cd /glade/work/$USER/MELODIES-MONET/examples/submit_jobs/

python run_melodies_monet.py

# ---------------------------------------------------------------------------
# Running one day per job with a PBS job array
# ---------------------------------------------------------------------------
# Satellite pairing is often too large for a single job. A job array runs one
# day per element, with a concurrency cap so a month does not swamp the queue:
#
#   #PBS -J 1-30%6            # 30 elements, at most 6 running at once
#
# and derive the date from the array index:
#
#   export YMD=$(printf "202406%02d" ${PBS_ARRAY_INDEX})   # 20240601..20240630
#
# Your run script then reads YMD (via os.environ) to select that day's input
# files and name its output.
#
# Two things to watch:
#
#   * A degenerate range is rejected. `-J 5-5` is an error, not a one-element
#     array. To rerun a single day, submit it directly and pass the date in:
#         qsub -v YMD=20240605 submit_casper.sh
#
#   * `-v` lists must not contain spaces. `-v RUN=ref, YMD=20240605` silently
#     drops YMD -- the job runs with it unset. Write `-v RUN=ref,YMD=20240605`.
#
# Fanning out over several model runs, one job each:
#
#   for RUN in ref alt; do
#     qsub -N mm_${RUN} -o mm_${RUN}.log -v RUN=$RUN submit_casper.sh
#   done
#
# Memory scales with the target grid rather than the observation volume, so
# unstructured meshes need considerably more than a lat/lon grid of the same
# nominal resolution. Check a single day before committing a month.
