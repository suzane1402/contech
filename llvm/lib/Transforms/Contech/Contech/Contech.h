#ifndef CONTECH_H
#define CONTECH_H

#include "llvm/Pass.h"
#include "llvm/Module.h"

namespace llvm {
    class Contech;
    ModulePass* createContechPass();
    
    typedef struct _llvm_mem_op {
        bool isWrite;
        char size;
        Value* addr;
        struct _llvm_mem_op* next;
    } llvm_mem_op, *pllvm_mem_op;

    typedef struct _llvm_basic_block {
        unsigned int id, len;
        int hasCheckBuffer;
        ct_event_id ev; // if ev == ct_event_basic_block, then no sync in this block
        pllvm_mem_op first_op;
        BasicBlock* tgts[2]; // basic blocks may branch into up to two other blocks
    } llvm_basic_block, *pllvm_basic_block;
    
    typedef enum _CONTECH_FUNCTION_TYPE {
        NONE,
        MAIN,
        MALLOC,
        FREE,
        THREAD_CREATE,
        THREAD_JOIN,
        SYNC_ACQUIRE,
        SYNC_RELEASE,
        BARRIER,
        BARRIER_WAIT,
        EXIT,
        COND_WAIT,
        COND_SIGNAL,
        NUM_CONTECH_FUNCTION_TYPES
    } CONTECH_FUNCTION_TYPE;
    
    typedef struct _llvm_function_map {
        const char* func_name;
        size_t str_len;
        CONTECH_FUNCTION_TYPE typeID;
    } llvm_function_map, *pllvm_function_map;
}

#endif