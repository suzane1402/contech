#!/usr/bin/env python

import os
import argparse
import subprocess
import shutil
from util import *

def main(parsec=False):
    
    # Find contech installation
    if os.environ.has_key("CONTECH_HOME"):
        CONTECH_HOME = os.environ["CONTECH_HOME"]
        MIDDLE = os.path.join(CONTECH_HOME, "middle/middle")
        TRACEVALIDATOR = os.path.join(CONTECH_HOME, "backend/TraceValidator/traceValidator")
        
        #PIN frontend
        PINPATH = os.path.join(CONTECH_HOME,"pin_fe/pin-2.12-58423-gcc.4.4.7-linux/")
        PINBIN = os.path.join(PINPATH,"pin")
        PINTOOL = os.path.join(PINPATH,"source/tools/Frontend/obj-intel64/Frontend.so")
        
        # List of backend tools.
        # TODO: generalize this list so that the script can recognize these by name
        TASKVIZ = os.path.join(CONTECH_HOME, "backend/TaskGraphVisualizer/taskViz")
        STATS = os.path.join(CONTECH_HOME, "backend/Statistics/stats")
        DYNAMICCFG = os.path.join(CONTECH_HOME, "backend/DynamicCFG/dynamicCFG")
        COMM = os.path.join(CONTECH_HOME, "backend/Comm/comm")
        COMM2 = os.path.join(CONTECH_HOME, "backend/Comm2/comm")
        CACHESIM = os.path.join(CONTECH_HOME, "backend/MultiCacheSim/CacheTestDriver")
        HELTECH = os.path.join(CONTECH_HOME, "backend/Heltech/heltech")
        HAMMER = os.path.join(CONTECH_HOME, "backend/Hammer/hammer")
    else:
        print_error("Error: Could not find contech installation. Set CONTECH_HOME to the root of your contech directory.")
        exit(1)

    # Find parsec installation
    if parsec:
        if os.environ.has_key("PARSEC_HOME"):
            PARSEC_HOME = os.environ["PARSEC_HOME"]
            PARSECMGMT = os.path.join(PARSEC_HOME, "bin/parsecmgmt")
        else:
            print_error("Error: Could not find parsec installation. Set PARSEC_HOME to the root of your parsec directory.")
            exit(1)
    
    # Find output directory
    if os.environ.has_key("CONTECH_OUTDIR"): 
        if os.environ["HOSTNAME"] == "ristorante":
            CONTECH_OUTDIR = os.environ["CONTECH_OUTDIR"]
        else:
            CONTECH_OUTDIR = "/tmp"
    else:
        CONTECH_OUTDIR = "/tmp"
        print_warning("Warning: CONTECH_OUTDIR is not set. Defaulting to " + CONTECH_OUTDIR + ".")
    
    # Parse commandline arguments
    if parsec:
        parser = argparse.ArgumentParser(description="Runs a parsec benchmark that has been compiled with contech, generating a task graph and optionally running backend tools.")
        parser.add_argument("benchmark", help="The parsec bencmark to run.")
        parser.add_argument("-i", "--input", help="The input size to use.", default="test")
        parser.add_argument("-n", "--numthreads", help="The number of threads to run.", default="4")
    else:
        parser = argparse.ArgumentParser(description="Runs benchmark that has been compiled with contech, generating a task graph and optionally running backend tools.")
        parser.add_argument("benchmark", help="The executable to run.")
        parser.add_argument("--args", help="Input arguments, enclosed in quotes.", default="")
        
                
    parser.add_argument("--backends", help="List of backends to run on the generated task graph. Separate backends with a space, and surround the list in quotes.")
    parser.add_argument("--cached", help="Don't re-run the benchmark, use existing task graph", default=False, action='store_true')
    parser.add_argument("--traceOnly", help="Save the event trace and do not run any other steps", default=False, action='store_true')
    parser.add_argument("--pinFrontend",help="Whether to use the PIN frontend.",default=False, action='store_true')
    parser.add_argument("--discardTrace",help="Write trace to /dev/null",default=False, action='store_true')
    args = parser.parse_args()
    
    name = os.path.basename(args.benchmark)
    if parsec:
        taskgraphBasename = "{}_{}_{}.taskgraph".format(name, args.numthreads, args.input)
    else:
        taskgraphBasename = "{}.taskgraph".format(name)
    
    if args.cached == False:
        # Run the benchmark
        print_header("Running " + name)
        tracefile = os.path.join(CONTECH_OUTDIR, name + ".contech.trace")
        taskgraph = os.path.join(CONTECH_OUTDIR, taskgraphBasename)
        if args.discardTrace: tracefile = "/dev/null"
        os.environ["CONTECH_FE_FILE"] = tracefile
        
        with Timer(name):
            if args.pinFrontend and parsec:
                pcall([
                       PARSECMGMT, 
                       "-a", "run",
                       "-p", name,
                       "-c", "llvm",
                       "-d", CONTECH_OUTDIR,
                       "-n", args.numthreads,
                       "-i", args.input,
                       "-s", '"/usr/bin/time %(PINBIN)s -t %(PINTOOL)s --"' % locals() 
                       ])  
            elif parsec:
                pcall([
                       PARSECMGMT, 
                       "-a", "run", 
                       "-p", name, 
                       "-c", "contech", 
                       "-d", CONTECH_OUTDIR,
                       "-n", args.numthreads, 
                       "-i", args.input, 
                       "-s", '"/usr/bin/time"'])
            else:
                pcall([args.benchmark, args.args])
        
        # Stop here if we only care about the trace
        if args.discardTrace:
            exit(0)
        elif args.traceOnly:
            permTrace = os.path.join(CONTECH_HOME, "traces/", name + ".contech.trace")
            if pcall([TRACEVALIDATOR, tracefile], returnCode = True):
                print_error("Trace was corrupt, did not save")
            else:
                shutil.copy(tracefile, permTrace)
                print_header("Trace saved to " + permTrace)
            os.remove(tracefile)
            exit(0)
             
        # Run the generated trace through the middle layer
        print_header("Passing through middle layer")
        
        if not os.path.exists(tracefile):
            print_error("Error: Trace file does not exist. Benchmark either didn't run or crashed.")
            exit(1)
            
        with Timer("Middle layer"):
            pcall([MIDDLE, tracefile, taskgraph])
            
        # Copy results back
        shutil.copy(taskgraph, os.path.join(CONTECH_HOME, "middle/output"))
            
    else:
        # Use existing task graph
        taskgraph = os.path.join("/net/tinker/ehein6/contech", "middle/output", taskgraphBasename)
    
    # Run backends
    if args.backends != None:
        
        for backend in args.backends.split(" "):
            print_header("Running " + backend)
            with Timer(backend):
                if backend == "stats":
                    pcall([STATS, taskgraph])
                    
                elif backend == "taskViz": 
                    print_header("Generating graph")
                    pcall([TASKVIZ, taskgraph])
                    shutil.copy("taskGraph.png", os.path.join(CONTECH_HOME, "backend/TaskGraphVisualizer/output", name + ".taskgraph.png"))
                    
                elif backend == "taskViz:enableDataArrows":
                    print_header("Generating graph with data arrows")
                    pcall([TASKVIZ, taskgraph, "--enableDataArrows"])
                    shutil.copy("taskGraph.png", os.path.join(CONTECH_HOME, "backend/TaskGraphVisualizer/output", name + "-arrows.taskgraph.png"))
                    
                elif backend == "dynamicCFG":
                    print_header("Generating CFG graph")
                    #cfgFile = os.path.join(CONTECH_HOME, "scripts/output/", name + ".controlflowgraph")
                    cfgOutput = os.path.join(CONTECH_HOME, "backend/DynamicCFG/output/", name + ".png")
                    pcall([DYNAMICCFG, taskgraph, cfgOutput])
                    
                elif backend == "comm":
                    pcall([COMM, taskgraph])
                    
                elif backend == "comm2":
                    output = os.path.join(CONTECH_HOME, "backend/Comm2/output/", name)
                    pcall([COMM2, taskgraph, output])
                
                elif "cacheSim" in backend:
                    mode = backend.split(":")[1]
                    
                    cacheModel = os.path.join(CONTECH_HOME, "backend/MultiCacheSim/MOSI_dir_SMPCache.so")
                    profile = os.path.join(CONTECH_HOME, "backend/Comm2/output/", name)
                    output = os.path.join(CONTECH_HOME, "backend/MultiCacheSim/output/", name + "-" + mode + ".csv")
                    print_header("Running MultiCacheSim with " + os.path.basename(cacheModel) + " in " + mode + " mode.") 
                    pcall([CACHESIM, taskgraph, cacheModel, profile, mode , ">", output])
                elif "heltech" in backend:
                    pcall([HELTECH, taskgraph])
                elif "hammer" in backend:
                    output = os.path.join(CONTECH_HOME, "backend/Hammer/output/", name + ".csv")
                    pcall([HAMMER, taskgraph, ">", output])
                else:
                    print_warning("Unrecognized backend: " + backend)
                    
    
    if args.cached == False:
        # Clean up
        os.remove(taskgraph)
        os.remove(tracefile)
        # Parsec temp files, we're not really sure where they are so just try to remove all of them
        if parsec:
            try: shutil.rmtree(os.path.join(CONTECH_OUTDIR, "pkgs")) 
            except: pass
            try: shutil.rmtree(os.path.join(CONTECH_OUTDIR, "ext")) 
            except: pass
    
if __name__ == "__main__":
    main()