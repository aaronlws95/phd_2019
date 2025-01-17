

__author__ = 'QiYE'

import numpy
import scipy.io
from src.utils import constants
import matplotlib.pyplot as plt
dataset_path_prefix=constants.Data_Path
setname='msrc'

thresholds=range(0,81,1)


keypoints = scipy.io.loadmat('%sdata/%s/source/test_%s_xyz_21joints.mat' % (dataset_path_prefix,setname,setname))
xyz_true = keypoints['xyz']


joint_num = 21

color = [(255/255.0, 56/255.0, 37/255.0),
         (0/255.0, 118/255.0, 255/255.0),
         (84/255.0 ,200/255.0, 253/255.0),
         (67/255.0 ,219/255.0, 94/255.0),
         (255/255.0 ,206/255.0, 0/255.0),
         (250/255.0, 98/255.0, 195/255.0),
         (255/255.0 ,150/255.0 ,0)]
accuracy_hsf_gt_quaternion = [0,0,0,0,0,0,0,0,0,0.3,1.2,2.8,4.9,7.5,11.6,16.4,20.9,26.7,32.4,37.1,40.7,45.1,50.1,54.7,57.9,63,66.7,69.1,70.6,73.3,76.4,78.6,81,83,84.1,85.3,86.8,88.5,89.3,90.3,91.1,91.7,92,92.4,92.9,93.2,93.5,93.9,94.2,94.5,94.6,95.2,95.5,96,96.2,96.2,96.2,96.2,96.8,97,97,97.1,97.2,97.2,97.3,97.3,97.4,97.4,97.5,97.5,97.5,97.6,97.7,97.7,97.8,97.8,97.8,97.9,98.1,98.1,98.1];
accuracy_original_gt_quaternion = [0,0,0,0,0,0,0,0,0,0,0.2,0.6,0.8,1.6,3.2,5.5,7.2,9.7,13.3,16,20.1,22.8,26.6,30.7,34.4,37.6,41,45,47.9,51.2,54.3,56.6,59.3,62.4,65.6,68.2,70,72.5,74.4,76.6,78,79,80.3,82,83.2,84.8,86.5,87.3,88.6,89.8,90.5,91.1,91.4,91.7,92.9,93.4,93.8,94,94.3,94.6,94.9,95.3,95.3,95.7,96.1,96.1,96.3,96.3,96.3,96.4,96.6,96.6,96.6,96.8,97.1,97.2,97.4,97.5,97.7,97.7,97.7];

accuracy_hsf = [0,0,0,0,0,0,0,0,0.21834,0.21834,0.65502,1.31,2.1834,3.7118,5.2402,8.5153,10.4803,13.7555,19.214,22.4891,25.9825,31.0044,33.8428,36.8996,41.7031,44.5415,46.7249,48.9083,50.655,53.7118,55.8952,57.2052,59.3886,60.262,61.5721,63.5371,65.5022,67.6856,70.0873,71.179,73.1441,73.7991,74.6725,74.8908,76.4192,77.7293,78.821,79.476,80.5677,81.8777,83.1878,83.4061,84.4978,86.0262,87.7729,88.8646,89.5197,90.1747,91.2664,91.7031,92.3581,93.0131,93.2314,94.1048,94.3231,94.7598,94.9782,95.1965,95.1965,95.1965,95.1965,95.1965,95.4148,95.4148,95.6332,95.8515,96.0699,96.0699,96.0699,96.0699,96.0699]
accuracy_original = [0,0,0,0,0,0,0,0,0,0.1,0.3,0.6,1.5,2.8,3.4,5,6.6,8.9,10.8,13,14.8,17.3,19.8,22.5,24.9,26.7,29.1,31.8,34.3,36.9,39.5,41.3,43.2,46.1,47.8,49.5,50.8,53.5,55.1,57.1,58.3,60,61.4,61.8,63.4,64.7,65.6,66.6,67.4,68.4,69.3,70.9,72.1,73.8,74.8,76.1,78,78.8,80.2,81.1,82.1,82.7,83.7,84.3,84.8,86,86.6,87.5,88.2,88.8,89.4,89.8,90,90.5,90.8,91.2,91.8,91.9,92.1,92.1,92.2]

hier_derot_recur_xyz = numpy.empty((xyz_true.shape[0],21,3))
for i in xrange(0,21,1):

    hier_derot_recur_xyz[:,i,:]=scipy.io.loadmat('%sdata/HDJIF_cmp_prior/MSRC_hybrid_v2/jnt%d_xyz.mat'% (dataset_path_prefix,i))['jnt']
print 'msrc hier_derot_recur_v2 error ',numpy.mean(numpy.mean( numpy.sqrt(numpy.sum((hier_derot_recur_xyz- xyz_true)**2,axis=-1))))
tmp = numpy.sqrt(numpy.sum((hier_derot_recur_xyz- xyz_true)**2,axis=-1))*1000
err_hier_derot_recur_v2 =tmp.reshape((tmp.shape[0]*tmp.shape[1],1))

all_size=err_hier_derot_recur_v2.shape[0]

accuracy_hier_derot_recur  = numpy.zeros((len(thresholds)),dtype='float32')
for t in xrange(len(thresholds)):
    loc_bl_t = numpy.where(err_hier_derot_recur_v2  <= thresholds[t])
    accuracy_hier_derot_recur[t] = 100.0 * loc_bl_t[0].shape[0] / all_size


plt.figure()

c1, = plt.plot(thresholds,accuracy_hier_derot_recur,linewidth=1,c='r', hold=True)

c2, = plt.plot(thresholds, accuracy_hsf,linewidth=1,c='b', hold=True)
c3, = plt.plot(thresholds, accuracy_original,linewidth=1,c='g',hold=True)
c4,=plt.plot(thresholds, accuracy_hsf_gt_quaternion,'--',linewidth=1,c='b', hold=True)
c5,=plt.plot(thresholds, accuracy_original_gt_quaternion,'--',linewidth=1,c='g')
plt.legend([c1,c2,c3,c4,c5], ['Ours','HSO[19]','Sharp et al.[3]','HSO+GroundTruth[19]','Sharp et al.+GroundTruth[3]'],loc=4)

plt.xlabel('error threshold D (mm)',fontsize=20)
plt.ylabel('proportion of joints within error < D (%)',fontsize=15)
plt.yticks(range(0,101,10))

plt.grid('on')
# plt.show()
plt.savefig('C:/Proj/Proj_Hier_Hand_eccv2016_07042016/Proj_CNN_Hier/data/HDJIF_cmp_prior/eccv2016_fig/msrchybridv2joint.eps',format='eps', dpi=300)
# plt.savefig('C:/Users/QiYE/OneDrive/Doc_ProgressReport/eccv2016/images/msrccmp.eps',format='eps', dpi=300)

