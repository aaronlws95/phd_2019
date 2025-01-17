__author__ = 'QiYE'
import h5py
from . import xyz_uvd
import numpy
import matplotlib.pyplot as plt
import cv2
from . import hand_utils,math

def get_err_from_normuvd(path,normuvd,dataset,jnt_idx,setname):
    if setname =='icvl':
        centerU=320/2
    if setname =='nyu':
        centerU=640/2
    if setname =='msrc':
        centerU=512/2
    if setname=='mega':
        centerU=315.944855

    f = h5py.File(path, 'r')
    xyz_gt=f['xyz_gt'][...]
    # uvd_norm_gt=f['uvd_norm_gt'][...]
    uvd_hand_centre=f['uvd_hand_centre'][...]
    bbsize=f['bbsize'][...]
    # imgs=f['img0'][...]
    f.close()
    uvd_hand_centre=numpy.expand_dims(uvd_hand_centre,axis=1)
    numImg=uvd_hand_centre.shape[0]
    print(numImg)
    # tmp_gt=uvd_norm_gt[:,jnt_idx]
    # norm_err= numpy.sum((tmp_gt.reshape(-1,18)-normuvd[:uvd_norm_gt.shape[0]].reshape(-1,18))**2,axis=-1)
    # print(numpy.mean(norm_err))
    # square_root = numpy.sqrt(numpy.sum((tmp_gt-normuvd[:uvd_norm_gt.shape[0]])**2,axis=-1))
    # print(numpy.mean(square_root))
    # for i in numpy.random.randint(0,numImg,3):
    #     hand_utils.show_two_palm_skeleton(normuvd[i],uvd_norm_gt[i,jnt_idx])
    #     # hand_utils.show_hand_skeleton(normuvd[i])
    #     plt.figure()
    #     plt.imshow(imgs[i],'gray')
    #     plt.scatter(normuvd[i,:,0]*96+48,normuvd[i,:,1]*96+48,c='b')
    #     plt.scatter(uvd_norm_gt[i,jnt_idx,0]*96+48,uvd_norm_gt[i,jnt_idx,1]*96+48,c='r')
    #     plt.show()


    bbsize_array = numpy.ones((numImg,3))*bbsize
    print(uvd_hand_centre.shape)
    bbsize_array[:,2]=uvd_hand_centre[:,0,2]
    bbox_uvd = xyz_uvd.xyz2uvd(setname=setname,xyz=bbsize_array)
    normUVSize = numpy.array(numpy.ceil(bbox_uvd[:,0]) - centerU,dtype='int32')
    normuvd=normuvd[:numImg].reshape(numImg,len(jnt_idx),3)
    uvd = numpy.empty_like(normuvd)
    uvd[:,:,2]=normuvd[:,:,2]*bbsize
    uvd[:,:,0:2]=normuvd[:,:,0:2]*normUVSize.reshape(numImg,1,1)
    uvd += uvd_hand_centre

    xyz_pred = xyz_uvd.uvd2xyz(setname=setname,uvd=uvd)


    err = numpy.mean(numpy.sqrt(numpy.sum((xyz_pred-xyz_gt[:,jnt_idx,:])**2,axis=-1)),axis=0)

    print(dataset,'err', err,numpy.mean(err))

    return xyz_pred,xyz_gt, err

# def get_normuvd_from_offset(offset,previous_pred_uvd):
#
#     rot_angle = math.get_angle_between_two_lines(line0=(previous_pred_uvd[:,3,:]-previous_pred_uvd[:,0,:])[:,0:2])
#
#     for i in range(offset.shape[0]):
#
#         M = cv2.getRotationMatrix2D((48,96+48),-rot_angle[i],1)
#         for j in range(offset.shape[1]):
#             offset[i,j] = numpy.dot(M,numpy.array([offset[i,j,0]*96,offset[i,j,1]*96,1]))/96
#     pred_uvd = previous_pred_uvd+offset
#     return pred_uvd

# def get_normuvd_from_offset(offset,previous_pred_uvd,uvd_hand_center):
#
#     rot_angle = math.get_angle_between_two_lines(line0=(previous_pred_uvd[:,3,:]-previous_pred_uvd[:,0,:])[:,0:2])
#
#     for i in range(offset.shape[0]):
#
#         cur_pred_uvd = previous_pred_uvd[i,:,:]
#         mean_pred_uvd = numpy.mean(cur_pred_uvd,axis=0)
#
#         scale_ratio = (mean_pred_uvd[2]*300+uvd_hand_center[i,2])/uvd_hand_center[i,2]
#         M = cv2.getRotationMatrix2D((48,48),-rot_angle[i],1/(1.8*scale_ratio))
#
#         for j in range(offset.shape[1]):
#             offset[i,j,0:2] = (numpy.dot(M,numpy.array([offset[i,j,0]*96+48,offset[i,j,1]*96+48,1]))-48)/96
#
#     pred_uvd = numpy.mean(previous_pred_uvd,axis=1,keepdims=True)+offset
#     return pred_uvd

def get_normuvd_from_offset(offset,pred_palm,jnt_uvd_in_prev_layer,scale):

    rot_angle = math.get_angle_between_two_lines(line0=(pred_palm[:,3,:]-pred_palm[:,0,:])[:,0:2])
    for i in range(offset.shape[0]):
        M = cv2.getRotationMatrix2D((48,48),-rot_angle[i],1/scale)
        for j in range(offset.shape[1]):
            offset[i,j,0:2] = (numpy.dot(M,numpy.array([offset[i,j,0]*96+48,offset[i,j,1]*96+48,1]))-48)/96

    pred_uvd = jnt_uvd_in_prev_layer+offset
    return pred_uvd



