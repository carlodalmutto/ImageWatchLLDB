
import lldb
from PIL import Image
import struct
from subprocess import call
from time import strftime
from os.path import expanduser
import os
import pickle
import numpy as np


##################################################
# __lldb_init_module ()
##################################################
def __lldb_init_module(debugger, internal_dict):

    # Initialization code to add your commands
    debugger.HandleCommand('command script add -f iw.iw iw')
    print 'The "iw" python command has been installed and is ready for use.'


##################################################
# im_show ()
##################################################

def iw(debugger, command, result, internal_dict):

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
# showImage ()
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

    # Fit the opencv elemente data in the PIL element data
    if matInfo['data_symbol'] == 'b':
        image_data = [i+128 for i in image_data]
    elif matInfo['data_symbol'] == 'H':
        image_data = [i >> 8 for i in image_data]
    elif matInfo['data_symbol'] == 'h':
        image_data = [(i + 32768) >> 8 for i in image_data]
    elif matInfo['data_symbol'] == 'i':
        image_data = [(i + 2147483648) >> 24 for i in image_data]
    elif matInfo['data_symbol'] in ('f', 'd'):
        # A float image is discretized in 256 bins for display.
        max_image_data = max(image_data)
        min_image_data = min(image_data)
        img_range = max_image_data - min_image_data
        if img_range > 0:
            image_data = [int(255 * (i - min_image_data) / img_range)
                          for i in image_data]
        else:
            image_data = [0 for i in image_data]

    # Producing data for visualization
    if n_channel == 3:
        # OpenCV stores the channels in BGR mode. Convert to RGB while packing.
        image_data = zip(*[image_data[i::3] for i in [2, 1, 0]])

    # Show image.
    img = Image.new(mode, (width, height))
    img.putdata(image_data)

    # Save to file and open it.
    TEMP_FOLDER = expanduser("~") + "/Downloads/lldb_iw_temp/"
    imageFolder = str(TEMP_FOLDER) + \
        str(matInfo['name']) + "_" + strftime("%H_%M_%S") + ".png"
    pickleFolder = str(TEMP_FOLDER) + \
        str(matInfo['name']) + "_" + strftime("%H_%M_%S") + ".p"

    data = str(matInfo['name']) + " = double\\(imread\\("+"\\'" + imageFolder + "\\'" + "\\)\\) \\/ 255.0\\; figure\\(\\)\\; imshow\\(" + str(matInfo['name']) + "\\)\\; system\\(\\'find " + TEMP_FOLDER + " -mtime +1 -delete  \\'\\)\\;"
    os.system("echo " + data.strip() + " | pbcopy")

    if os.path.exists(TEMP_FOLDER):
        os.system("rm -r " +  TEMP_FOLDER)
    os.mkdir(TEMP_FOLDER)
    pickle.dump(np.asarray(img), open(pickleFolder, "wb"))

    # os.system("python " + expanduser("~") + "/lldb/iw_visualizer.py " + imageFolder)
    os.system("python " + expanduser("~") + "/Documents/APPS/ImageWatchLLDB/Useful_Files/iw_visualizer.py " + pickleFolder)
    if os.path.exists(TEMP_FOLDER):
        os.system("rm -r " +  TEMP_FOLDER)
