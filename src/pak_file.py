"""
Created on February 2, 2012

@author: sbobovyc
"""
"""   
    Copyright (C) 2012 Stanislav Bobovych

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import struct 
import os
import zlib
import cStringIO
import base64
from Crypto.Cipher import AES

PAK_SIGNATURE = 0x504B4C4501000000
AES_KEY_CIPHERED = "eFd1cnozbFBFVEVSMjUzeg=="
                
class PAK_data:
    def __init_(self, dir):  
        self.file_name_length = None    # includes '\0' 
        self.file_size = None   # in bytes
        self.file_offset = None # in bytes
        self.file_crc = None    # unknown crc
        self.file_name = None   # includes '\0'                
        self.data = None
    
    def unpack(self, dir, file_pointer, dest_filepath, verbose=False):
        self.file_directory = dir
        self.file_name_length, self.file_size, self.file_offset, self.file_crc = struct.unpack('<IQQQ', file_pointer.read(28))
        
        self.file_name = file_pointer.read(self.file_name_length)
        # srip the null
        self.file_name = self.file_name.replace("\00", "").strip()
        
        saved_pointer = file_pointer.tell()
        file_pointer.seek(self.file_offset)
        self.data = file_pointer.read(self.file_size)
        
        if verbose:
            print "File name: %s" % os.path.join(self.file_directory,self.file_name)
            print "File offset: %s" % hex(self.file_offset)
            print "File Size: %s bytes" % hex(self.file_size)
            print "File unknown crc: %s" % hex(self.file_crc)
            #print "File Adler32 %s" % hex(zlib.adler32(self.data) & 0xffffffff )
            #print "File CRC32 %s" % hex(zlib.crc32(self.data) & 0xffffffff )
            print 
        
        path = os.path.join(dest_filepath, self.file_directory)
        if not os.path.exists(path):
            os.makedirs(path)
            
        with open(os.path.join(path, self.file_name), "wb") as f:
            f.write(self.data)
        file_pointer.seek(saved_pointer)
        
class PAK_dir:
    def __init_(self, dir):
        self.dir_index = None           # start index is 1  
        self.dir_name_length = None     
        self.dir_number_files = None  
        self.dir_name = None
                
            
    
    def unpack(self, file_pointer, dest_filepath, verbose=False):        
        self.dir_index, self.dir_name_length, self.dir_number_files = struct.unpack('<IIQ', file_pointer.read(16))
        self.dir_name = file_pointer.read(self.dir_name_length)
        
        # strip the null and remove leading slash
        self.dir_name = self.dir_name.replace("\00", "").strip()[1:]
        
        if self.dir_number_files != 0:
            for i in range(0, self.dir_number_files):
                pF = PAK_data()
                pF.unpack(self.dir_name, file_pointer, dest_filepath, verbose)
        else:            
            return 
        
class PAK_header:
    def __init__(self):
        self.magic = None
        self.descriptor_size = None # in bytes
        self.num_dirs = None
    
    def unpack(self, file_pointer, dest_filepath, verbose=False):    
        self.magic, = struct.unpack(">Q", file_pointer.read(8))
        
        if self.magic != PAK_SIGNATURE:            
            # something bad happened
            print "File is not BiA pak"
            return
        
        self.descriptor_size, self.num_dirs = struct.unpack("<QQ", file_pointer.read(16))        
        
        if verbose:
            print "Descriptor size: %i bytes" % self.descriptor_size
            print "Number of directories in archive: %i" % self.num_dirs
            
        for i in range(0, self.num_dirs):
            pD = PAK_dir()
            pD.unpack(file_pointer, dest_filepath, verbose)
            
class PAK_file:
    def __init__(self, filepath=None):
        self.filepath = filepath
        self.header = None
        if self.filepath != None:
            self.open(filepath)
    
    def open(self, filepath=None, peek=False):
        if filepath == None and self.filepath == None:
            print "File path is empty"
            return
        if self.filepath == None:
            self.filepath = filepath
        
        self.header = PAK_header()

    def dump(self, dest_filepath=os.getcwd(), verbose=False):
        with open(self.filepath, "rb") as f:            
            self.header.unpack(f, dest_filepath, verbose)

class PAK_CRYPT_file(PAK_file):
    def open(self, filepath=None, peek=False):        
        if filepath == None and self.filepath == None:
            print "File path is empty"
            return
        if self.filepath == None:
            self.filepath = filepath
        
        with open(self.filepath, "rb") as f:
            _, real_size, block_size = struct.unpack("<HII", f.read(0xa))
        
            buf = f.read(block_size)
        
            aes = AES.new(base64.b64decode(AES_KEY_CIPHERED), AES.MODE_ECB)
            self.io = cStringIO.StringIO(aes.decrypt(buf)[:real_size])
        self.header = PAK_header()

    def dump(self, dest_filepath=os.getcwd(), verbose=False):          
            self.header.unpack(self.io, dest_filepath, verbose)
                            
if __name__ == "__main__":
    pF = PAK_file("C:\Program Files (x86)\Jagged Alliance Back in Action Demo\\voices_win32.pak")
    #pF = PAK_CRYPT_file("C:\Program Files (x86)\Jagged Alliance Back in Action Demo\\configs_win32.pak.crypt")
    pF.open()        
    pF.dump()