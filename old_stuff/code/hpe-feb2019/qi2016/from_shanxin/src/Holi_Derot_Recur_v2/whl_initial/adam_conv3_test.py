__author__ = 'QiYE'

import theano
import theano.tensor as T
import numpy
from load_data import  load_data_multi
from src.Model.CNN_Model import CNN_Model_multi3_conv3
from src.Model.Train import set_params
from src.utils import constants
def test_model_conv3(dataset, dataset_path_prefix,setname, model_save_name, pred_save_name,source_name,c1,c2,c3,h1_out_factor,h2_out_factor,batch_size):

    # jnt_type='base' # jnt_type : base,mid, tip

    model_info='whole_21jnts_r0r1r2_conti'
    jnt_idx = range(0,21,1)
    print jnt_idx
    src_path = '%sdata/%s/source/'%(dataset_path_prefix,setname)

    path = '%s%s%s.h5'%(src_path,dataset,source_name)
    test_set_x0, test_set_x1,test_set_x2,test_set_y= load_data_multi(batch_size, path, jnt_idx, is_shuffle=False)
    n_test_batches = test_set_x0.shape[0]/ batch_size
    print 'n_test_batches', n_test_batches
    img_size_0 = test_set_x0.shape[2]
    img_size_1 = test_set_x1.shape[2]
    img_size_2 = test_set_x2.shape[2]

    X0 = T.tensor4('source0')   # the data is presented as rasterized images
    X1 = T.tensor4('source1')
    X2 = T.tensor4('source2')
    is_train = T.iscalar('is_train')
    # x0.tag.test_value = train_set_x0.get_value()
    Y = T.matrix('target')

    model = CNN_Model_multi3_conv3(
        model_info=model_info,
        X0=X0,X1=X1,X2=X2,
              img_size_0 = img_size_0,
              img_size_1=img_size_1,
              img_size_2=img_size_2,
              is_train=is_train,
                c00= c1,
                kernel_c00= 5,
                pool_c00= 4,
                c01= c2,
                kernel_c01= 4,
                pool_c01= 2 ,
                c02=c3,
                kernel_c02= 3,
                pool_c02= 2,

                c10= c1,
                kernel_c10= 5,
                pool_c10= 2,
                c11= c2,
                kernel_c11= 3,
                pool_c11= 2 ,
                c12= c3,
                kernel_c12= 3,
                pool_c12= 2 ,

                c20= c1,
                kernel_c20= 5,
                pool_c20= 2,
                c21= c2,
                kernel_c21= 5,
                pool_c21= 1 ,
                c22= c3,
                kernel_c22= 3,
                pool_c22= 1 ,

                h1_out_factor=h1_out_factor,
                h2_out_factor=h2_out_factor,
                batch_size = batch_size,
                p=0.5)

    cost = model.cost(Y)

    save_path = '%sdata/%s/holi_derot_recur_v2/whl_initial/'%(constants.Data_Path,setname)
    model_save_path = "%s%s.npy"%(save_path,model_save_name)
    set_params(model_save_path, model.params)

    test_model = theano.function(inputs=[X0,X1,X2,is_train,Y],
        outputs=[cost,model.layers[-1].output], on_unused_input='ignore')

    cost_nbatch = 0
    uvd_norm = numpy.empty_like(test_set_y)
    for minibatch_index in xrange(n_test_batches):
        slice_idx = range(minibatch_index * batch_size,(minibatch_index + 1) * batch_size,1)
        x0 = test_set_x0[slice_idx]
        x1 = test_set_x1[slice_idx]
        x2 = test_set_x2[slice_idx]
        y = test_set_y[slice_idx]

        cost_ij, uvd_batch = test_model(x0,x1,x2,numpy.cast['int32'](0), y)
        uvd_norm[slice_idx] = uvd_batch
        cost_nbatch+=cost_ij
    print 'test cost', cost_nbatch/n_test_batches
    numpy.save("%s%s%s.npy"%(save_path,dataset,pred_save_name),uvd_norm)
if __name__ == '__main__':

    #this test result contains 8252 frames
    test_model_conv3(dataset='test',
                dataset_path_prefix=constants.Data_Path,
                setname='icvl',
                batch_size=8,
                source_name='_icvl_r0_r1_r2_uvd_bbox_21jnts_20151113_depth200',
                model_save_name = 'param_cost_uvd_bw_r012_21jnts_64_96_128_1_2_adam_lm9',
                pred_save_name = '_uvd_bw_r012_21jnts_64_96_128_1_2_adam_lm9',
                c1=64,
                c2=96,
                c3=128,
                h1_out_factor=1,
                              h2_out_factor=2)


    # train_model_conv3(setname='icvl',
    #                  dataset_path_prefix=constants.Data_Path,
    #         source_name='_icvl_r0_r1_r2_uvd_bbox_21jnts_20151113_depth200',
    #             lamda=0.00001,
    #             batch_size = 100,
    #             jnt_idx = range(0,21,1),
    #             c1=96,
    #             c2=128,
    #             c3=160,
    #             h1_out_factor=1,
    #             h2_out_factor=2)
