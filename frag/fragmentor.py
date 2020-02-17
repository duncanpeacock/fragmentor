#!/usr/bin/env python
# Purpose
#
# Based on build_db_from_smiles.py, this module builds the graph network nodes
# and edges from # the Informatics Matters 'standard' (uncompressed) file
# representation with fragmentation done over parallel processes.
#
# The output is these files:
# nodes.csv containing the molecules. The fields are: SMILES, HAC, RAC, NUM_CHILDREN, NUM_EDGES, TIME_MS
# edges.csv containing the edges. The fields are: PARENT_SMILES, CHILD_SMILES, LABEL
# rejects.smi containing the SMILES that were rejected because of the fragment count filter.
#
# Duncan Peacock
# February 2020


import argparse
import os
import sys
import threading
import collections
import time
import multiprocessing
from multiprocessing import Pool
# Local classes.
from fragclass import FragProcess
from fragclass import FragController
from fragclass import FileWriter


#from frag.network.models import NodeHolder, Attr
#from frag.utils.network_utils import build_network

cache = set()
node_count = 0
edge_count = 0
rejects_count = 0

base_dir = None
nodes_f = None
edges_f = None
rejects_f = None

def get_arguments():

    parser = argparse.ArgumentParser(
        description="Convert un-compressed standard SMILES"
                    " for Astex Fragment network."
    )
    parser.add_argument("--input")
    parser.add_argument("--base_dir")
    parser.add_argument('-l', '--limit',
                        type=int, default=0,
                        help='Limit processing to the first N molecules,'
                             ' process all otherwise')
    parser.add_argument('-s', '--skip',
                        type=int, default=0,
                        help='Number of molecules to skip molecules'
                             ' in the input file')
    parser.add_argument('--max-frag',
                        type=int, default=0,
                        help='Limit processing to molecules with no more than'
                             ' this number of initial fragment (no limit if 0)')
    parser.add_argument('-r', '--report-interval', type=int, default=1000, help='Reporting interval')
    parser.add_argument('-p', '--processes', type=int, default=4,
                        help='Number of parallel processes')
    parser.add_argument('-c', '--chunk_size', type=int, default=10,
                        help='size of chunk the SMILES will be grouped in to')

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", dest="verbosity", action="store_const", const=1)
    group.add_argument("-vv", dest="verbosity", action="store_const", const=2)

    parser.set_defaults(verbosity=0)
    return parser.parse_args()

def main():
    """ Main Function.
    1. Accept input
    2. Sets up parallel fragment worker processes using the FragWorker class
    3. Sets up fragmentation queue control thread using the FragControl class

    Parameters:
        Standardized filename
        File paths for base directory and output.
        Process parameters (max_frag_layers, max_queue_size, max_chunk_size)
        Reporting parameters

    Returns:
        processing details.

    """
    args = get_arguments()

    # Do we have an input and base directory?
    if not args.input:
        print('ERROR: Must specify an input')
        sys.exit(1)
    if not os.path.isfile(args.input):
        print('ERROR: input (%s) does not exist' % args.input)
        sys.exit(2)
    if not args.base_dir:
        print('ERROR: Must specify a base directory')
        sys.exit(3)

    # Create Directories for output files

    global base_dir
    global nodes_f
    global edges_f
    global rejects_f
    base_dir = args.base_dir

    if not os.path.isdir(base_dir):
        os.mkdir(base_dir)
    nodes_f = open(os.path.join(base_dir, "nodes.csv"), "w")
    edges_f = open(os.path.join(base_dir, "edges.csv"), "w")

    f_writer = FileWriter(args, nodes_f, edges_f)


    num_processed = 0


    # Create Queues
    manager = multiprocessing.Manager()
    process_queue = manager.Queue()
    results_queue = manager.Queue()

    # Start Fragmentation Worker Processes
    pool = Pool(processes=args.processes)
    frag_processes = []
    for _ in range(args.processes):
        proc = FragProcess(
                process_queue,
                results_queue)
        frag_processes.append(proc)
        proc.start()

    t1 = time.time()
    # Start Fragmentation Control Thread

    thrd = FragController(
                args,
                process_queue,
                results_queue,
                f_writer)
    thrd.start()

    # Close and Shutdown
    nodes_f.close()
    edges_f.close()
    if rejects_f:
        rejects_f.close()

    print("Processed {0} molecules, wrote {1} nodes and {2} edges, {3} rejects".format(num_processed, node_count, edge_count, rejects_count))
    print ("Fragementation took:", time.time() - t1)


if __name__ == "__main__":
    main()

