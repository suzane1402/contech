#include "ct_file.h"


ct_file* create_ct_file_blank(){
    ct_file* newHandle = (ct_file*) calloc(1,sizeof(ct_file));
    return newHandle;
}

ct_file* create_ct_file_w(const char* fileName,bool compressed){
    ct_file* newHandle = create_ct_file_blank();
    FILE* tempFileHandle = fopen (fileName,"wb");

    if(compressed){
        newHandle->compressedHandle = gzdopen (fileno(tempFileHandle), "wb");
    } else {
        newHandle->uncompressedHandle = tempFileHandle;
    }
    return newHandle;
}

ct_file* create_ct_file_r(const char* fileName){
    ct_file* newHandle = create_ct_file_blank();
    FILE* tempFileHandle = fopen (fileName,"rb");
    
    //read whether file is compressed or uncompressed.
    bool compressed;
    unsigned char zipTest[2];
    if(tempFileHandle == NULL){
        return NULL;
    }
    
    // read the first two bytes and check if they are equal to 0x1f8b.
    // false positive ARE possible (though unlikely) with this method but not false negatives
    fread(zipTest,sizeof(char),2,tempFileHandle);
    if(zipTest[0] == 0x1f && zipTest[1] == 0x8b){ // these are "magic" numbers stored in the bytes of gzip'ed files
        compressed = true;
    } else {
        compressed = false;
    }
    rewind(tempFileHandle); //rewind handle to to the beginning, gzip errors otherwise
    if(compressed){
        newHandle->compressedHandle = gzdopen(fileno(tempFileHandle), "rb");
    } else {
        newHandle->uncompressedHandle = tempFileHandle;
    }
    return newHandle;
}


ct_file* create_ct_file_from_handle(FILE* existingHandle){
    ct_file* newHandle = create_ct_file_blank();
    newHandle->uncompressedHandle = existingHandle;
    return newHandle;
}

gzFile getCompressedHandle(ct_file* handle){
    return handle->compressedHandle;    
}

FILE* getUncompressedHandle(ct_file* handle){
    return handle->uncompressedHandle;
}

bool isClosed(ct_file* handle){
    return getCompressedHandle(handle) == NULL && getUncompressedHandle(handle) == NULL;
}

bool isCompressed(ct_file* handle){
    if(getCompressedHandle(handle) == NULL){
        return false;
    }
    return true;
}

void close_ct_file(ct_file* handle){
    if(isClosed(handle) == false){ 
        if(isCompressed(handle)){
            gzclose(getCompressedHandle(handle));
            handle->compressedHandle = NULL;
        } else {
            fclose(getUncompressedHandle(handle));
            handle->uncompressedHandle = NULL;
        }
    }
}

size_t ct_read(void * ptr, size_t size, ct_file* handle){
    size_t read = 0;
    if(isCompressed(handle)){
        read = gzread (getCompressedHandle(handle), ptr, size);
    } else {
        read = fread(ptr,1,size,getUncompressedHandle(handle));
    }
    return read;
}


size_t ct_write(void * ptr, size_t size, ct_file* handle){
    size_t written = 0;
    if(isCompressed(handle)){
        written = gzwrite (getCompressedHandle(handle), ptr, size);
    } else {
        written = fwrite(ptr,1,size,getUncompressedHandle(handle));
    }
    return written;
}

int ct_eof(ct_file* handle){
    int result;
    if(isCompressed(handle)){
        result = gzeof (getCompressedHandle(handle));
    } else {
        result = feof (getUncompressedHandle(handle));
    }
    return result;
}

int ct_seek( unsigned long long offset,ct_file* handle){
    int result;
    if(isCompressed(handle)){
        result = gzseek (getCompressedHandle(handle), offset, SEEK_SET);
    } else {
        result = fseek (getUncompressedHandle(handle), offset, SEEK_SET );
    }
    return result;
}

void ct_rewind(ct_file* handle){
    ct_seek(0,handle);
}

int ct_flush(ct_file* handle){
    int result;
    if(isCompressed(handle)){
        result = gzflush (getCompressedHandle(handle), Z_FULL_FLUSH);
    } else {
        result = fflush (getUncompressedHandle(handle));
    }
    return result;
}








