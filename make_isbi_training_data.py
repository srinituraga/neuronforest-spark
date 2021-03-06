import numpy as np
from scipy import ndimage, misc, io
import os
from libtiff import TIFF

def makeFeatures(img, filename, min_idx=None, max_idx=None):
    if min_idx is None:
        min_idx = (0, 0, 0)
        max_idx = tuple(np.array(img.shape)-1)

    orders = [[0, 0], [0, 1], [1, 0], [0, 2], [1, 1], [2, 0]]
    scales = [1, 2, 4, 8, 16, 32]

    print("Creating features: " + filename)
    print(str(min_idx) + " to " + str(max_idx))
    #NOTE: force big-endian for use at scala end!
    features = np.empty((np.prod(max_idx-min_idx+1), len(orders) * len(scales)), dtype=">f")
    i = 0
    for scale in scales:
        print("  Scale " + str(scale))
        for o in orders:
            print("    Order " + str(o))
            f = ndimage.filters.gaussian_filter(img, scale, o)[min_idx[0]:max_idx[0]+1, min_idx[1]:max_idx[1]+1]
            features[:, i] = f.flatten(order = 'C')
            i += 1

    print("  Saving")
    features.tofile(filename + ".raw")
    #np.savetxt(filename + ".txt", features, fmt='%.6f')
    #io.savemat(filename + ".mat", {'features':features})

def makeTargets(borders, filename, min_idx, max_idx):
    print("Creating targets and seg: " + filename)
    print(str(min_idx) + " to " + str(max_idx))
    idxs = get_image_idxs(borders, min_idx=min_idx, max_idx=max_idx)
    targets = get_target_affinities(borders, idxs).astype(np.int32)
    out = targets
    print("  Saving")
    np.savetxt(filename + ".txt", out, fmt='%d')

def makeDimensions(shape, filename, min_idx, max_idx):
    print("Creating dimensions: " + filename)
    print(str(min_idx) + " to " + str(max_idx))
    print("total shape = " + str(shape))
    file = open(filename + ".txt", 'w')
    file.write(" ".join([str(i) for i in shape]) + "\n")
    file.write(" ".join([str(i) for i in min_idx]) + "\n")
    file.write(" ".join([str(i) for i in max_idx]))
    file.close()

# -------------------------------------------------
def get_steps(arr):
    return tuple(np.append(np.cumprod(np.array(arr.shape)[1:][::-1])[::-1], 1))

def get_image_idxs(im, max_idx, min_idx=(0,0,0)):
    xs, ys = np.ix_(range(min_idx[0], max_idx[0] + 1), range(min_idx[1], max_idx[1] + 1))
    steps = get_steps(im)
    return np.array(np.unravel_index((xs * steps[0] + ys * steps[1]).flatten(), im.shape))

def get_target_affinities(borders, idxs):
    aff = np.empty((len(idxs[0]), 2), dtype=bool)
    aff[:, 0] = (borders[tuple(idxs)] == 255) * (borders[(idxs[0]+1, idxs[1])] == 255)
    aff[:, 1] = (borders[tuple(idxs)] == 255) * (borders[(idxs[0], idxs[1]+1)] == 255)
    return aff


# --------------------------------------------------
def makeISBIData(toPath, tif, labelstif=None, margin=15, isTest=False):
    if not os.path.exists(toPath): os.mkdir(toPath)
    k = 0
    for (rawimage, rawlabels) in zip(TIFF.open(tif).iter_images(), TIFF.open(labelstif).iter_images()):
    	rawimage = np.pad(rawimage, [(margin, margin), (margin, margin)], 'edge')
    	rawlabels = np.pad(rawlabels, [(margin, margin), (margin, margin)], 'edge')
    	for rotation in range(4):
    		for flip in range(2):
	        	print("-------------\n Rotation " + str(rotation) + " Flip " + str(flip) + "Slice " + str(k))
		        folder = toPath + "/r" + str(rotation) + "f" + str(flip) + "s" + str(k) + "/"
		        if not os.path.exists(folder): os.mkdir(folder)

		        image = np.rot90(rawimage, rotation)
		        labels = np.rot90(rawlabels, rotation)
		        if(flip == 1):
		        	image = np.fliplr(image)
		        	labels = np.fliplr(labels)

		        box_size = np.array(image.shape)
		        box_min = np.array((margin, margin))
		        box_max = box_size - (margin, margin) - 1
		        box_min_margin = np.array([0, 0])
		        box_max_margin = box_size-1
		        shape = box_max_margin - box_min_margin + 1

		        makeFeatures(image, folder + "/features", box_min_margin, box_max_margin)
		        makeDimensions(shape, folder + "/dimensions",  box_min, box_max)
		        makeTargets(labels, folder + "/targets", box_min, box_max)
        k+=1


makeISBIData(toPath="/isbi_data_32", tif='isbi/train-volume.tif', labelstif='isbi/train-labels.tif', margin=64)



#makeISBIData(toPath="image_test_data", imagesDir='BSDS500/data/images/test', groundTruthDir='BSDS500/data/groundTruth/test')
#makeImageData(toPath="shifted", imagesDir='/home/luke/Desktop/testimage/shifted', groundTruthDir='/home/luke/Desktop/testimage/shifted_groundtruth')

# def makeData(numSplit=(1, 1, 1), margin=15, imageNums=[1], toPath="masters_data/spark"):
#     print "Loading Helmstaedter2013 data"
#     Helmstaedter2013 = io.loadmat("Helmstaedter.mat")

#     for q in imageNums:
#     	i = q-1
#         print("\nSplitting im" + str(i+1)+ " into " + str(numSplit) + " different subvolumes".format())
#         bounds = Helmstaedter2013["boundingBox"][0, i]
#         outer_min_idx = np.maximum(bounds[:, 0], margin)
#         outer_max_idx = np.minimum(bounds[:, 1]-1, np.array(Helmstaedter2013["im"][0,i].shape) - margin-1) # -1 because no affinity on faces
#         box_size = (outer_max_idx - outer_min_idx + 1)/numSplit
#         mainfolder = toPath + "/im" + str(i+1)
#         if not os.path.exists(mainfolder ): os.mkdir(mainfolder )
#         mainfolder  = mainfolder  + "/split_" + str(numSplit[0]) + str(numSplit[1]) + str(numSplit[2])
#         if not os.path.exists(mainfolder ): os.mkdir(mainfolder )
#         for box_x in range(numSplit[0]):
#             for box_y in range(numSplit[1]):
#                 for box_z in range(numSplit[2]):
#                     print("-------------\nCreating sub-volume " + str(box_x) + ", " + str(box_y) + ", " + str(box_z))
#                     box_offset = box_size * [box_x, box_y, box_z]
#                     folder = mainfolder + "/" + str(box_x) + str(box_y) + str(box_z)
#                     if not os.path.exists(folder): os.mkdir(folder)

#                     box_min = outer_min_idx + box_offset
#                     box_max = box_min + box_size-1
#                     box_min_margin = box_min - margin
#                     box_max_margin = box_max + margin
#                     box_min_relative = [margin, margin, margin]
#                     box_max_relative = margin + box_size-1
#                     shape = box_max_margin - box_min_margin + 1

#                     if not os.path.exists(folder): os.mkdir(folder)
#                     makeTargetsAndSeg(Helmstaedter2013["segTrue"][0, i], folder + "/targets", box_min, box_max)
#                     makeFeatures(Helmstaedter2013["im"][0, i], folder + "/features", box_min_margin, box_max_margin)
#                     makeDimensions(shape, folder + "/dimensions",  box_min_relative, box_max_relative)

# makeData(numSplit=(2, 2, 2), imageNums=[1], toPath="data")
# #makeData(numSplit=(1, 2, 2), imageNums=[5,6,7,8,9,10,11,12], toPath="data")
