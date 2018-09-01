# Function to visualize image quantities.
#
# 8/12/15, 8/31/18


################################
# Imports.
################################

import sys
import math
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches

################################
# Check inputs.
################################

if len(sys.argv) < 2:
    print "Not enough arguments"
    sys.exit()
else:
    IMG_NAME = str(sys.argv[1])



################################
# Callbacks
################################

def onclick(event):
    global img
    x = math.floor(event.xdata)
    y = math.floor(event.ydata)

    ax[0].clear()
    ax[1].clear()
    ax[2].clear()
    ax[0].axis("off")
    ax[1].axis("off")
    ax[2].axis("off")
    im1 = ax[0].imshow(img, interpolation='nearest', cmap='jet')
    clim = im1.properties()['clim']
    centerX = min(max(x, 21), img.shape[1] - 21)
    centerY = min(max(y, 21), img.shape[0] - 21)

    rect = patches.Rectangle((centerX-20, centerY-20), 41, 41, linewidth=1, edgecolor='r', facecolor='none')
    ax[0].add_patch(rect)
    rect = patches.Rectangle((centerX-3, centerY-3), 7, 7, linewidth=1, edgecolor='r', facecolor='none')
    ax[0].add_patch(rect)
    
    if len(img.shape) == 3:
        img2 = img[int(centerY)-20:int(centerY)+20, int(centerX)-20:int(centerX)+20, :]
        img3 = img[int(centerY)-3:int(centerY)+3, int(centerX)-3:int(centerX)+3, :]
    else:
        img2 = img[int(centerY)-20:int(centerY)+20, int(centerX)-20:int(centerX)+20]
        img3 = img[int(centerY)-3:int(centerY)+3, int(centerX)-3:int(centerX)+3]

    ax[1].imshow(img2, interpolation='nearest', clim=clim, cmap='jet')  
    ax[2].imshow(img3, interpolation='nearest', clim=clim, cmap='jet')  

    if len(img.shape) == 3:
        for r in range(0,img3.shape[0]):
            for c in range(0,img3.shape[1]):
                ax[2].text(c-0.2, r-0.15, math.floor(img3[r, c, 0] * 255), fontsize=6, color='red')
                ax[2].text(c-0.2, r+0.15, math.floor(img3[r, c, 1] * 255), fontsize=6, color='green')
                ax[2].text(c-0.2, r+0.45, math.floor(img3[r, c, 2] * 255), fontsize=6, color='blue')
    else:
        for r in range(0,img3.shape[0]):
            for c in range(0,img3.shape[1]):
                ax[2].text(c-0.2, r-0.15, math.floor(img3[r, c] * 255), fontsize=6, color='red')
    plt.show()

################################
# Visualization
################################

img = plt.imread(IMG_NAME)
fig, ax = plt.subplots(1, 3, figsize=(15, 5))
ax[0].axis("off")
ax[1].axis("off")
ax[2].axis("off")
ax[0].imshow(img, interpolation='nearest', cmap='jet')
ax[1].set_title('ImageWatch')
cid = fig.canvas.mpl_connect('button_press_event', onclick)
zeros_array = np.zeros((5,5), dtype='float')
ax[1].imshow(zeros_array, cmap='gnuplot2')
ax[2].imshow(zeros_array, cmap='gnuplot2')
plt.show()
