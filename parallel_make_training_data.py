import numpy as np
from scipy import ndimage, misc, io
import os
import h5py
from multiprocessing import Pool
import multiprocessing

targets=0
ims=0

def makeFeatures(img, filename, min_idx=None, max_idx=None):
    if min_idx is None:
        min_idx = (0, 0, 0)
        max_idx = tuple(np.array(img.shape)-1)

    # The orders and scales for generating features
    orders = [[0, 0, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 2], [0, 1, 1], [1, 0, 1], [0, 2, 0], [1, 1, 0], [2, 0, 0]]
    scales = [1,2,4,8]

    print("Creating features: " + filename)
    #print(str(min_idx) + " to " + str(max_idx))
    #NOTE: force big-endian for use at scala end!
    features = np.empty((np.prod(max_idx-min_idx+1), len(orders) * len(scales)), dtype=">f")
    i = 0
    for scale in scales:
        # print("  Scale " + str(scale))
        for o in orders:
            #print("    Order " + str(o))
            f = ndimage.filters.gaussian_filter(img, scale, o)[min_idx[0]:max_idx[0]+1, min_idx[1]:max_idx[1]+1, min_idx[2]:max_idx[2]+1]
            # Puts everything into one array in row-major order
            features[:, i] = f.flatten(order = 'C')
            i += 1

    #print(features[1:100])
    #print("  Saving")

    features.tofile(filename + ".raw")
    #np.savetxt(filename + ".txt", features, fmt='%.6f')
    #io.savemat(filename + ".mat", {'features':features})

def makeTargetsAndSeg(segTrue, filename, min_idx, max_idx):
    # print("Creating targets and seg: " + filename)
    #print(str(min_idx) + " to " + str(max_idx))
    idxs = get_image_idxs(segTrue, min_idx=min_idx, max_idx=max_idx)
    targets = get_target_affinities(segTrue, idxs).astype(np.int32)
    out = np.concatenate((targets, segTrue[tuple(idxs)][:, np.newaxis]), axis=1)
    #print("  Saving")
    np.savetxt(filename + ".txt", out, fmt='%d')

def makeDimensions(shape, filename, min_idx, max_idx):
    #print("Creating dimensions: " + filename)
    print(str(min_idx) + " to " + str(max_idx))
    # print("total shape = " + str(shape))
    file = open(filename + ".txt", 'w')
    file.write(" ".join([str(i) for i in shape]) + "\n")
    file.write(" ".join([str(i) for i in min_idx]) + "\n")
    file.write(" ".join([str(i) for i in max_idx]))
    file.close()

# -------------------------------------------------
def get_steps(arr):
    return tuple(np.append(np.cumprod(np.array(arr.shape)[1:][::-1])[::-1], 1))

def get_image_idxs(im, max_idx, min_idx=(0,0,0)):
    xs, ys, zs = np.ix_(range(min_idx[0], max_idx[0] + 1), range(min_idx[1], max_idx[1] + 1),
                        range(min_idx[2], max_idx[2] + 1))
    steps = get_steps(im)
    return np.array(np.unravel_index((xs * steps[0] + ys * steps[1] + zs * steps[2]).flatten(), im.shape))

def get_target_affinities(seg, idxs):
    aff = np.empty((len(idxs[0]), 3), dtype=bool)
    aff[:, 0] = np.logical_and(seg[tuple(idxs)] != 0, seg[tuple(idxs)] == seg[tuple(idxs + [[1], [0], [0]])])
    aff[:, 1] = np.logical_and(seg[tuple(idxs)] != 0, seg[tuple(idxs)] == seg[tuple(idxs + [[0], [1], [0]])])
    aff[:, 2] = np.logical_and(seg[tuple(idxs)] != 0, seg[tuple(idxs)] == seg[tuple(idxs + [[0], [0], [1]])])
    return aff


def parFunc(a):
    box_x=a[0]
    box_y=a[1]
    box_z=a[2]
    box_size=a[3]
    mainfolder=a[4]
    outer_min_idx=a[5]
    margin=a[6]
    print("-------------\nCreating sub-volume " + str(box_x) + ", " + str(box_y) + ", " + str(box_z))
    box_offset = box_size * [box_x, box_y, box_z]
    folder = mainfolder + "/" + str(box_x) + str(box_y) + str(box_z)
    if not os.path.exists(folder): os.mkdir(folder)

    # parameters specific to this box
    box_min = outer_min_idx + box_offset
    box_max = box_min + box_size-1
    box_min_margin = box_min - margin
    box_max_margin = box_max + margin
    box_min_relative = [margin, margin, margin]
    box_max_relative = margin + box_size-1
    shape = box_max_margin - box_min_margin + 1

    # Makes an affinity map in "/targets.txt" stored as x y z trueSegmentNum
    makeTargetsAndSeg(targets, folder + "/targets", box_min, box_max)
    # Applies a multivariate gaussian filter to the images and saves them to /features.raw
    makeFeatures(ims, folder + "/features", box_min_margin, box_max_margin)

    makeDimensions(shape, folder + "/dimensions",  box_min_relative, box_max_relative)
    return

# --------------------------------------------------

def makeData(numSplit=(1, 1, 1), margin=15, toPath="masters_data/spark", bounds=0):
    if not os.path.exists(toPath): os.mkdir(toPath)
    print("\nSplitting im into " + str(numSplit) + " different subvolumes".format())
    #bounds = data["boundingBox"][0, i]
    # np.maximum gives element-wise maximum, 3x1 array
    outer_min_idx = np.maximum(bounds[:, 0], margin)
    print("outer_min_idx: ", outer_min_idx)
    outer_max_idx = np.minimum(bounds[:, 1]-1, np.array(ims.shape) - margin-1) # -1 because no affinity on faces
    print ("image shape: ",np.array(ims.shape))
    print("outer_max_idx: ", outer_max_idx)
    box_size = (outer_max_idx - outer_min_idx + 1)/numSplit
    print ("box size: ",box_size)
    #mainfolder = toPath + "/im" + str(i+1)
    mainfolder  = toPath  + "/split_" + str(numSplit[0]) + str(numSplit[1]) + str(numSplit[2])
    if not os.path.exists(mainfolder ): os.mkdir(mainfolder )
    p = Pool(8)
    argsArr=[]
    # split in each dimension specified by numsplit
    for box_x in range(numSplit[0]):
        for box_y in range(numSplit[1]):
            for box_z in range(numSplit[2]):
                argsArr.append([box_x,box_y,box_z,box_size,mainfolder,outer_min_idx,margin])
    p.map(parFunc,argsArr)
# for transforming
map = {}
def lookup(x):
    return map[x]

# main method
global ims
global targets
num=520
box = np.array([ [0,num],[0,num],[0,num] ])
newMargin=65

#reading in images
print "reading ims..."
file = h5py.File("/nobackup/turaga/data/fibsem_medulla_7col/tstvol-520-1-h5/img_normalized.h5",'r')
ims = np.array(file["main"])

#reading in labels
print "reading labels..."
file = h5py.File("/nobackup/turaga/data/fibsem_medulla_7col/tstvol-520-1-h5/groundtruth_seg.h5",'r')
targets = np.array(file["main"])


dir = "/nobackup/turaga/singhc/med-data-new/111/big1a/"
split = (2,2,2)
makeData(numSplit=split, margin=newMargin, toPath=dir+str(0),bounds=box)
for i in range(1,4): #1,2,3
    print "\n\n"+str(i)+"\n\n"
    ims = np.rot90(ims)
    targets = np.rot90(targets)
    makeData(numSplit=split, margin=newMargin, toPath=dir+str(i),bounds=box)

ims = np.fliplr(ims)
targets = np.fliplr(targets)

for i in range(4,7): #4,5,6,7
    print "\n\n"+str(i)+"\n\n"
    ims = np.rot90(ims)
    targets = np.rot90(targets)
    makeData(numSplit=split, margin=newMargin, toPath=dir+str(i),bounds=box)

'''
num=250
box = np.array([ [0,num],[0,num],[0,num] ])

#reading in images
print "reading ims..."
file = h5py.File("/nobackup/turaga/data/fibsem_medulla_7col/trvol-250-1-h5/img_normalized.h5",'r')
ims = np.array(file["main"])

#reading in labels
print "reading labels..."
file = h5py.File("/nobackup/turaga/data/fibsem_medulla_7col/trvol-250-1-h5/groundtruth_seg.h5",'r')
targets = np.array(file["main"])


dir = "/nobackup/turaga/singhc/med-data-new/000/small1a/"
split = (1, 1, 1)
makeData(numSplit=split, margin=newMargin, toPath=dir+str(0),bounds=box)
for i in range(1,4): #1,2,3
    print "\n\n"+str(i)+"\n\n"
    ims = np.rot90(ims)
    targets = np.rot90(targets)
    makeData(numSplit=split, margin=newMargin, toPath=dir+str(i),bounds=box)

ims = np.fliplr(ims)
targets = np.fliplr(targets)

for i in range(4,7): #4,5,6,7
    print "\n\n"+str(i)+"\n\n"
    ims = np.rot90(ims)
    targets = np.rot90(targets)
    makeData(numSplit=split, margin=newMargin, toPath=dir+str(i),bounds=box)


#reading in images
print "reading ims..."
file = h5py.File("/nobackup/turaga/data/fibsem_medulla_7col/trvol-250-2-h5/img_normalized.h5",'r')
ims = np.array(file["main"])

#reading in labels
print "reading labels..."
file = h5py.File("/nobackup/turaga/data/fibsem_medulla_7col/trvol-250-2-h5/groundtruth_seg.h5",'r')
targets = np.array(file["main"])


dir = "/nobackup/turaga/singhc/med-data-new/000/small2a/"
split = (1, 1, 1)
makeData(numSplit=split, margin=newMargin, toPath=dir+str(0),bounds=box)
for i in range(1,4): #1,2,3
    print "\n\n"+str(i)+"\n\n"
    ims = np.rot90(ims)
    targets = np.rot90(targets)
    makeData(numSplit=split, margin=newMargin, toPath=dir+str(i),bounds=box)

ims = np.fliplr(ims)
targets = np.fliplr(targets)

for i in range(4,7): #4,5,6,7
    print "\n\n"+str(i)+"\n\n"
    ims = np.rot90(ims)
    targets = np.rot90(targets)
    makeData(numSplit=split, margin=newMargin, toPath=dir+str(i),bounds=box)
'''

print "\n\ndone\n\n"