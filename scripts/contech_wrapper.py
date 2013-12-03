#!/usr/bin/env python

# Wrapper compiler for contech front end

import os
import sys
import subprocess
import shutil
from util import pcall

def main(isCpp = False, markOnly = False, minimal = False, hammer = False):
    
    # Set locations of clang, opt, and the contech pass
    if os.environ.has_key("CONTECH_HOME"):
        CONTECH_HOME = os.environ["CONTECH_HOME"]
        #CLANG = CONTECH_HOME + "/llvm_fe_3.2/build/Release+Asserts/bin/clang"
        #CLANGPP = CONTECH_HOME + "/llvm_fe_3.2/build/Release+Asserts/bin/clang++"
        #OPT = CONTECH_HOME + "/llvm_fe_3.2/build/Release+Asserts/bin/opt"
        CT_FILE = CONTECH_HOME + "/common/taskLib/ct_file_C.o"
        LLVMCONTECH = CONTECH_HOME + "/llvm_fe_3.2/build/Release+Asserts/lib/LLVMContech.so"
        LLVMHAMMER = CONTECH_HOME + "/llvm_fe_3.2/build/Release+Asserts/lib/LLVMHammer.so"
        #RUNTIME = CONTECH_HOME + "/common/runtime/libct_runtime.a"
        if markOnly:
            RUNTIME = CONTECH_HOME + "/common/runtime/ct_runtime.o"
        else:
            RUNTIME = CONTECH_HOME + "/common/runtime/ct_runtime.bc"
        
        if os.environ.has_key("CONTECH_STATE_FILE"):
            stateFile = os.environ["CONTECH_STATE_FILE"]
        else:
            stateFile = CONTECH_HOME + "/scripts/output/contechStateFile.temp"
    else:        
        print ">Error: Could not find contech installation. Set CONTECH_HOME to the root of your contech directory."
        exit(1)
    
    #LOCAL = "/net/tinker/local"
    #LLVMCONTECH = LOCAL + "/lib/LLVMContech.so"
    #RUNTIME = LOCAL + "/lib/libct_runtime.a"
    
    CLANG = "clang"
    CLANGPP = "clang++"
    OPT = "opt"
    
    # Name of the .c file to be processed
    cfile="" 
    # Names of the .o files to be linked
    ofiles=""
    # Name of the output file
    out=""
    # All remaining flags to be passed on to clang
    CFLAGS="-flto --verbose"

    # Choose correct compiler
    if isCpp:
        CC = CLANGPP
    else:
        CC = CLANG
    
    outFileComingNext = False;
    compileOnly = False;
    depsOnly = False;
    
    for arg in sys.argv[1:]:

        # This compile step is just generating dependencies, don't compile or link unless instructed to
        if "-M" in arg:
            depsOnly = True
    
        # -o, look for filename next
        elif "-o" == arg:
            outFileComingNext = True
        
        # -o attached to other options
        elif "-o," in arg and out == "":
            
            # Option might have been passed to the linker with something like -Wl,-o,out
            if "," in arg:
                for token in arg.split(","):
                    if outFileComingNext == True:
                        out = token
                        outFileComingNext = False
                    elif token == "-o":
                        outFileComingNext = True
                # Make sure the whole option makes it to the CFlAGS, just in case
                CFLAGS = CFLAGS + " " + arg
                
            # -o attached to the front of the name
            else:
                out = arg
                out = out.replace("-o","",1)
            # TODO What other horrible ways are there to pass the name of the output file???
        
        # Saw -o at last arg
        elif outFileComingNext:
            out = arg
            outFileComingNext = False
            
        # C++ file
        elif ".cpp" == arg[-4:]:
            cfile = arg
            isCpp = True;
        elif ".cc" == arg[-3:]:
            cfile = arg
            isCpp = True
        # C file
        elif ".c" == arg[-2:]:
            cfile = arg
            isCpp = False
        
        # Object file
        elif ".o" == arg[-2:]:
            ofiles = ofiles + " " + arg
        
        # Compile only
        elif "-c" == arg:
            compileOnly = True
        
        # Combine other args into CFLAGS
        else:
            CFLAGS = CFLAGS + " " + arg


            
    # Debug
    #print ""
    #print "Contech wrapper: "
    #print "cfile=" + cfile
    #print "ofiles=" + ofiles
    #print "CFLAGS=" + CFLAGS
    #print "out=" + outdo

    # Found some flag that we don't handle, just pass through the compiler and exit
    if depsOnly and not compileOnly:
        passThrough(CC)
    
    # Compile requested but no input found, let the compiler throw an error
    if cfile == "" and compileOnly:
        passThrough(CC)
    
    # Input file found, assuming compile requested.
    # Compile with contech
    elif cfile != "":
        
        # Get the name of cfile without an extension
        if isCpp:
            name=cfile.replace(".cpp","",1);
            name=name.replace(".cc","",1);
        else:
        #linux.contech ... 
            name=cfile[0: len(cfile) - 2]
        
        # Define names of intermediate files
        A= name + ".bc"
        B= name + "_ct.bc"

        # Define name of compiled file
        newobj = ""
        if out != "" :
            newobj = out
        else:
            newobj = name + ".o"
        
        # Make sure the output ends in .o
        if newobj[-2:] != ".o":
            newobj = newobj + ".o"

        # Compile with clang to emit LLVM bitcode
        pcall([CC, CFLAGS, cfile, "-emit-llvm", "-c", "-o", A])
        # Run the Contech pass to add instrumentation
        
        if markOnly:
            pcall([OPT, "-load=" + LLVMCONTECH, "-Contech", A, "-o", B, "-ContechState", stateFile, "-ContechMarkFE"])
        elif minimal:
            pcall([OPT, "-load=" + LLVMCONTECH, "-Contech", A, "-o", B, "-ContechState", stateFile, "-ContechMinimal"])
        elif hammer:
            hammerNailFile = os.environ["HAMMER_NAIL_FILE"]
            hammerOptLevel = os.environ["HAMMER_OPT_LEVEL"]
            pcall([OPT, "-load=" + LLVMHAMMER, "-Hammer", A, "-o", B, "-HammerState", stateFile, "-HammerNailFile", hammerNailFile, "-HammerOptLevel", hammerOptLevel])
        else:
            pcall([OPT, "-load=" + LLVMCONTECH, "-Contech", A, "-o", B, "-ContechState", stateFile])
        # Compile bitcode back to a .o file
        pcall([CC, CFLAGS, "-c", "-o", newobj, B])
        # Add the generated object file to the list of things to link
        ofiles = ofiles + " " + newobj
        
    # Link 
    if not compileOnly:
        if ofiles != "":
            
            # Define name of final executable
            if out == "":
                out = "a.out"
                
            if hammer:
                # Compile final executable
                pcall([CC, ofiles, CFLAGS, "-o", out, "-flto", "-lpthread", "-lz"])
            else:
                # Link in basic block table
                shutil.copyfile(stateFile, "contech.bin")
                # Note that we may have to create two .o, one for 32bit and one for 64bit
                OBJCOPY = "objcopy"
                pcall([OBJCOPY, "--input binary", "--output elf64-x86-64", "--binary-architecture i386", "contech.bin", "contech_state.o"])
                
                # Compile final executable
                pcall([CC, RUNTIME, ofiles, CFLAGS, "-o", out, "-flto", "-lpthread", "-lz", "contech_state.o"])
                        
        else:
            passThrough(CC)

# Pass all args through to the compiler and don't do anything else
def passThrough(CC):
    command = [CC] + sys.argv[1:] 
    pcall(command, silent=True)
    exit(0)
    
if __name__ == "__main__":
    main(False)

    
