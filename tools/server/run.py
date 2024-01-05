from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import hashlib

def calculate_md5(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def dump_headers_to_file(self):
        headers = '\n'.join(f'{k}: {v}' for k, v in self.headers.items())
        with open('headers_dump.txt', 'w') as file:
            file.write(headers)

    '''
            freeSpace = self.headers.get('x-ESP8266-free-space')
            chipSize = self.headers.get('x-ESP8266-chip-size')
            sdkVersion = self.headers.get('x-ESP8266-sdk-version')
            sketchSize = self.headers.get('x-ESP8266-sketch-size')
            sketchMD5 = self.headers.get('x-ESP8266-sketch-md5')
            staMac = self.headers.get('x-ESP8266-STA-MAC')
    '''
    def chipSizeToPartitionName(self, chipSize):
        chipSizeMB = chipSize/1024/1024
        if chipSizeMB < 1:
            print('Chip size is less than 1MB, not supported')
            return None
        elif chipSizeMB == 1:
            partitionName = '1M128'
        elif chipSizeMB == 2:
            partitionName = '2M256'
        else:
            print('Chip size is more than 2MB, not supported now')
            return None
        return partitionName

    def getAppropriateFirmware(self, binFilePath, binGzFilePath, chipSize, freeSpace, GzipSupport):
        partitionName = self.chipSizeToPartitionName(chipSize)
        if partitionName is None:
                print('Chip size not supported')
                return None
        
        print('Chip size: ' + str(chipSize) + ' free space: ' + str(freeSpace) + ' gzip support: ' + str(GzipSupport) + ' partition name: ' + partitionName)

        step0bin = 'minota-builds/Minota_esp82xx_1M_auto_c230n.bin'
        step0binGz = step0bin + '.gz'
        step1bin = 'minota-builds/Minota_esp82xx_' + partitionName + '_auto_c274.bin'
        step1binGz = step1bin + '.gz'

        # if gzip is not supported, we are probably on SDK 1.x.x and step0 or some strange old firmware, we will force step1
        if not GzipSupport:
            return step1bin
        
        #from here down we expect gzip support
        if not os.path.isfile(binFilePath):
            print('Bin file not found: ' + binFilePath)
            return None
        if not os.path.isfile(binGzFilePath):
            print('Bin.gz file not found: ' + binGzFilePath)
            #we can create it
            return None
        fileSizeBin = os.path.getsize(binFilePath)
        fileSizeBinGz = os.path.getsize(binGzFilePath)
        # 1) go directly with bin if it fits
        if fileSizeBin <= freeSpace:
            return binFilePath
        # 1b) go directly with bin.gz if it fits and Gzip is supported
        if GzipSupport and fileSizeBinGz <= freeSpace:
            return binGzFilePath
        
        # 2) if we are here, we need to make space with smaller firmware
        # generally this souhld be need only for 1MB chips, for 2MB+ gzip mode should be enough for all cases (hope so :)
        # so from now we want gziped firmware of first step

        fileSizeStep1BinGz = os.path.getsize(step1binGz)
        if fileSizeStep1BinGz <= freeSpace:
            return step1binGz
        
        # 3) if we are here, only option is to try the smallest firmware, which will not support gzip and can override spiffs
        fileSizeStep0BinGz = os.path.getsize(step0binGz)
        if fileSizeStep0BinGz > freeSpace:
            print('No solution/firmware found for chip size: ' + str(chipSize) + ' and free space: ' + str(freeSpace) + ', but lets try to smallest')
        
        return step0binGz
        #print('No solution/firmware found for chip size: ' + chipSize + ' and free space: ' + freeSpace)
        return None

    def do_GET_provisioning_espeasy(self, hwID, sourceName):
        print('Request from hw id: ' + hwID + ' for ' + sourceName)
        if sourceName == '' or sourceName.startswith('firmware'):
            fwFilePath = 'data/' + hwID + '/current/firmware.bin'
            fwGzipFilePath = 'data/' + hwID + '/current/firmware.bin.gz'
            sdk = self.headers.get('x-ESP8266-sdk-version')
            gzipSupported = (int(sdk.split('.')[0]) > 1 ) if sdk is not None else False
            #string to int:
            freeSpace = self.headers.get('x-ESP8266-free-space')
            if freeSpace is not None: freeSpace = int(freeSpace)
            chipSize = self.headers.get('x-ESP8266-chip-size')
            if chipSize is not None: chipSize = int(chipSize)

            #check if fw is already on ESP:
            md5Current = self.headers.get('x-ESP8266-sketch-md5')
            if chipSize is None:
                self.send_error(500, 'Missing required header')
                return
            md5OfTargetFw = calculate_md5(fwFilePath)
            if md5Current == md5OfTargetFw:
                print('Firmware is already on ESP (' + md5Current + ') ' + fwFilePath)
                self.send_response(304)
                self.end_headers()
                return
            
            sourceFilePath = self.getAppropriateFirmware(fwFilePath, fwGzipFilePath, chipSize, freeSpace, gzipSupported)
            if sourceFilePath is None:
                self.send_error(404, 'No firmware found for chip size: %s and free space: %s' % (chipSize, freeSpace))
                return
            
            print('Replying with firmware: ' + sourceFilePath + ' (' + md5OfTargetFw + ')')
            

            #self.send_error(500, 'Not implemented yet')
            #return
        else:
            sourceFilePath = 'data/' + hwID + '/current/' + sourceName
        print('Source file path: ' + sourceFilePath)
        if not os.path.isfile(sourceFilePath):
            self.send_error(404, 'Source not defined: %s' % sourceName)
            return
        with open(sourceFilePath, 'rb') as file:
            file_content = file.read()
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(file_content)))
            self.send_header('x-MD5', calculate_md5(sourceFilePath))
            self.end_headers()
            self.wfile.write(file_content)

    def do_GET(self):
        print(f'GET request, path: {self.path}')
        self.dump_headers_to_file()
        if self.path.startswith('/p/ee/'):
            staMac = self.headers.get('x-ESP8266-STA-MAC')
            hwID = staMac.replace(':', '') if staMac is not None else 'unknown'
            self.do_GET_provisioning_espeasy(hwID, self.path.split('/')[3])

def run(server_class=HTTPServer, handler_class=CustomHTTPRequestHandler, port=10359):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'HTTP server running on port {port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run()

