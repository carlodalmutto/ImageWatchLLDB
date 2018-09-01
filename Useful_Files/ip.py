import lldb
from PIL import Image
import struct
from subprocess import call
from time import strftime
from os.path import expanduser
import os


##################################################
# __lldb_init_module ()
##################################################
def __lldb_init_module(debugger, internal_dict):

    # Initialization code to add your commands
    debugger.HandleCommand('command script add -f ip.ip ip')
    print 'The "ip" python command has been installed and is ready for use.'


##################################################
# ip_show ()
##################################################

def ip(debugger, command, result, internal_dict):

    # Get the frame.
    target = debugger.GetSelectedTarget()
    process = target.GetProcess()
    thread = process.GetSelectedThread()
    frame = thread.GetFrameAtIndex(0)

    # command holds the argument passed to im_show(),
    # e.g., the name of the Mat to be displayed.
    imageName = command

    # Get access to the required memory member.
    # It is wrapped in a SBValue object.
    root = frame.FindVariable(imageName)

    ## Get cvMat attributes.
    matInfo = getMatInfo(root, command)

    # Print cvMat attributes.
    printMatInfo(matInfo)

    # Show the image.
    showImage(debugger, matInfo)


##################################################
# getMatInfo ()
##################################################

def getMatInfo(root, command):

    # Flags.
    flags = int(root.GetChildMemberWithName("flags").GetValue())

    # Channels.
    channels = 1 + (flags >> 3) & 63

    # Type of cvMat.
    depth = flags & 7
    if depth == 0:
        cv_type_name = 'CV_8U'
        data_symbol = 'B'
    elif depth == 1:
        cv_type_name = 'CV_8S'
        data_symbol = 'b'
    elif depth == 2:
        cv_type_name = 'CV_16U'
        data_symbol = 'H'
    elif depth == 3:
        cv_type_name = 'CV_16S'
        data_symbol = 'h'
    elif depth == 4:
        cv_type_name = 'CV_32S'
        data_symbol = 'i'
    elif depth == 5:
        cv_type_name = 'CV_32F'
        data_symbol = 'f'
    elif depth == 6:
        cv_type_name = 'CV_64F'
        data_symbol = 'd'
    else:
        print("cvMat Type not sypported")

    # Rows and columns.
    rows = int(root.GetChildMemberWithName("rows").GetValue())
    cols = int(root.GetChildMemberWithName("cols").GetValue())

    # Get the step (access to value of a buffer with GetUnsignedInt16()).
    error = lldb.SBError()
    line_step = root.GetChildMemberWithName("step").GetChildMemberWithName('buf').GetData().GetUnsignedInt16(error, 0)

    # Get data address.
    data_address = int(root.GetChildMemberWithName("data").GetValue(), 16)

    # Create a dictionary for the output.
    matInfo = {'cols' : cols, 'rows' : rows, 'channels' : channels, 'line_step' : line_step,
               'data_address' : data_address, 'data_symbol' : data_symbol, 'flags' : flags, 'cv_type_name' : cv_type_name, 'name' : command}

    # Return.
    return matInfo


##################################################
# printMatInfo ()
##################################################

def printMatInfo(matInfo):

    # Print the info of the mat
    print ("flags: " + str(matInfo['flags']))
    print ("type: " + matInfo['cv_type_name'])
    print ("channels: " + str(matInfo['channels']))
    print ("rows: " + str(matInfo['rows']) + ", cols: " + str(matInfo['cols']))
    print ("line step: " + str(matInfo['line_step']))
    print ("data address: " + str(hex(matInfo['data_address'])))


##################################################
# chunker ()
##################################################

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))


##################################################
# prettyFloat to get only 4 decimals
##################################################

# maxIntDigitCnt = 1
# class prettyfloat(float):
#     def __repr__(self):
#         return ("%0.4f" % self).rjust(maxIntDigitCnt + 6, ' ') 


##################################################
# printImage ()
##################################################

def showImage(debugger, matInfo):

    # Get the process info.
    target = debugger.GetSelectedTarget()
    process = target.GetProcess()

    # Get the info of the Mat to be displayed.
    width = matInfo['cols']
    height = matInfo['rows']
    n_channel = matInfo['channels']
    line_step = matInfo['line_step']
    data_address = matInfo['data_address']

    if width == 0 | height == 0:
        return

    # Read the memory location of the data of the Mat.
    error = lldb.SBError()
    memory_data = process.ReadMemory(data_address, line_step * height, error)

    # Calculate the memory padding to change to the next image line.
    # Either due to memory alignment or a ROI.
    if matInfo['data_symbol'] in ('b', 'B'):
        elem_size = 1
    elif matInfo['data_symbol'] in ('h', 'H'):
        elem_size = 2
    elif matInfo['data_symbol'] in ('i', 'f'):
        elem_size = 4
    elif matInfo['data_symbol'] == 'd':
        elem_size = 8
    padding = line_step - width * n_channel * elem_size

    # Format memory data to load into the image.
    image_data = []
    if n_channel == 1:
        mode = 'L'
        fmt = '%d%s%dx' % (width, matInfo['data_symbol'], padding)
        for line in chunker(memory_data, line_step):
            image_data.extend(struct.unpack(fmt, line))
    elif n_channel == 3:
        mode = 'RGB'
        fmt = '%d%s%dx' % (width * 3, matInfo['data_symbol'], padding)
        for line in chunker(memory_data, line_step):
            image_data.extend(struct.unpack(fmt, line))
    else:
        print ('Only 1 or 3 channels supported\n')
        return
    
    # Make prining nicely formatted.
    if matInfo['data_symbol'] in ('f', 'd'):
        maxIntDigitCnt = len(str(int(max(image_data))))
        for i in range(0, len(image_data)):
            image_data[i] = ("%0.4f" % image_data[i]).rjust(maxIntDigitCnt + 6, ' ') 
    
    # Print mat.
    for i in range(0, height):
        lineToPrint = str(image_data[i * width: (i + 1) * width])
        lineToPrint = lineToPrint.replace("'", "")
        print lineToPrint



