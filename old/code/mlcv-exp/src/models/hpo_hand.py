import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm

from src import ROOT
from src.models.base_model import Base_Model
from src.datasets import get_dataloader, get_dataset
from src.networks.hpo_hand_net import HPO_Hand_Net
from src.optimizers import get_optimizer
from src.schedulers import get_scheduler
from src.loss.hpo_hand_loss import HPO_Hand_Loss
from src.utils import *

class HPO_Hand(Base_Model):
    def __init__(self, cfg, mode, load_epoch):
        super().__init__(cfg, mode, load_epoch)
        self.net        = HPO_Hand_Net(cfg).cuda()
        self.optimizer  = get_optimizer(cfg, self.net)
        self.scheduler  = get_scheduler(cfg, self.optimizer)
        
        self.train_dataloader   = get_dataloader(cfg, get_dataset(cfg, 'train'))
        self.val_dataloader     = get_dataloader(cfg, get_dataset(cfg, 'val'))
        
        self.pretrain = cfg['pretrain']
        self.load_weights()

        self.loss       = HPO_Hand_Loss(cfg)
        self.hand_root  = int(cfg['hand_root'])
        self.ref_depth  = int(cfg['ref_depth'])
        
        self.val_xyz_21_error       = []

        self.best_pred_uvd_list     = []
        self.topk_pred_uvd_list     = []
        self.pred_conf_list         = []

    # ========================================================
    # TRAINING
    # ========================================================

    def train_step(self, data_load):
        img, uvd_gt         = data_load
        img                 = img.cuda()
        uvd_gt              = uvd_gt.cuda()
        hand_out            = self.net(img)
        loss, *hand_losses  = self.loss(hand_out, uvd_gt)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        loss_u, loss_v, loss_d, loss_conf = hand_losses
        loss_dict = {
            'loss'          : '{:04f}'.format(loss.item()),
            'loss_u'        : '{:04f}'.format(loss_u.item()),
            'loss_v'        : '{:04f}'.format(loss_v.item()),
            'loss_d'        : '{:04f}'.format(loss_d.item()),
            'loss_conf'     : '{:04f}'.format(loss_conf.item()),
        }

        return loss_dict

    # ========================================================
    # VALIDATION
    # ========================================================

    def valid_step(self, data_load):
        img, uvd_gt             = data_load
        uvd_gt                  = uvd_gt.numpy()
        batch_size              = img.shape[0]
        img                     = img.cuda()

        pred_hand               = self.net(img)
        W                       = pred_hand.shape[3]
        H                       = pred_hand.shape[2]
        D                       = 5
        pred_hand               = pred_hand.view(batch_size, 64, D, H, W)
        pred_hand               = pred_hand.permute(0, 1, 3, 4, 2)

        # Hand
        uvd_gt[..., 0]          *= FPHA.ORI_WIDTH
        uvd_gt[..., 1]          *= FPHA.ORI_HEIGHT
        uvd_gt[..., 2]          *= self.ref_depth
        xyz_gt                  = FPHA.uvd2xyz_color(uvd_gt)

        for batch in range(batch_size):
            cur_pred_hand   = pred_hand[batch]
            pred_uvd        = cur_pred_hand[:63, :, :, :].view(21, 3, H, W, D)
            pred_conf       = torch.sigmoid(cur_pred_hand[63, :, :, :])

            FT              = torch.FloatTensor
            yv, xv, zv      = torch.meshgrid([torch.arange(H),
                                              torch.arange(W),
                                              torch.arange(D)])
            grid_x          = xv.repeat((21, 1, 1, 1)).type(FT).cuda()
            grid_y          = yv.repeat((21, 1, 1, 1)).type(FT).cuda()
            grid_z          = zv.repeat((21, 1, 1, 1)).type(FT).cuda()

            pred_uvd[self.hand_root, :, :, :, :] = \
                torch.sigmoid(pred_uvd[self.hand_root, :, :, :, :])
            pred_uvd[:, 0, :, :, :] = (pred_uvd[:, 0, :, :, :] + grid_x)/W
            pred_uvd[:, 1, :, :, :] = (pred_uvd[:, 1, :, :, :] + grid_y)/H
            pred_uvd[:, 2, :, :, :] = (pred_uvd[:, 2, :, :, :] + grid_z)/D

            pred_uvd                = pred_uvd.contiguous().view(21, 3, -1)
            pred_conf               = pred_conf.contiguous().view(-1)

            top_idx                 = torch.topk(pred_conf, 1)[1]
            best_pred_uvd           = pred_uvd[:, :, top_idx].squeeze().cpu().numpy()
            best_pred_uvd[..., 0]   *= FPHA.ORI_WIDTH
            best_pred_uvd[..., 1]   *= FPHA.ORI_HEIGHT
            best_pred_uvd[..., 2]   *= self.ref_depth
            best_pred_xyz           = FPHA.uvd2xyz_color(best_pred_uvd)
            cur_xyz_gt              = xyz_gt[batch]

            self.val_xyz_21_error.append(np.sqrt(np.sum(np.square(
                best_pred_xyz-cur_xyz_gt), axis=-1) + 1e-8 ))

    def get_valid_loss(self):
        eps                 = 1e-5
        val_xyz_l2_error    = np.mean(self.val_xyz_21_error)
        val_xyz_squeezed    = np.squeeze(np.asarray(self.val_xyz_21_error))
        pck                 = get_pck(val_xyz_squeezed)
        thresholds          = np.arange(0, 85, 5)
        auc                 = calc_auc(pck, thresholds)

        val_loss_dict = {
            'xyz_l2_error'  : val_xyz_l2_error,
            'AUC_0_85'      : auc,
        }

        self.val_xyz_21_error = []
        return val_loss_dict

    # ========================================================
    # PREDICTION
    # ========================================================

    def predict_step(self, data_load):
        img                     = data_load[0]
        img                     = img.cuda()
        pred_hand               = self.net(img)
        batch_size              = img.shape[0]
        W                       = pred_hand.shape[3]
        H                       = pred_hand.shape[2]
        D                       = 5
        pred_hand               = pred_hand.view(batch_size, 64, D, H, W)
        pred_hand               = pred_hand.permute(0, 1, 3, 4, 2)

        for batch in range(batch_size):
            # Hand
            cur_pred_hand   = pred_hand[batch]
            pred_uvd        = cur_pred_hand[:63, :, :, :].view(21, 3, H, W, D)
            pred_conf       = torch.sigmoid(cur_pred_hand[63, :, :, :])

            FT              = torch.FloatTensor
            yv, xv, zv      = torch.meshgrid([torch.arange(H),
                                              torch.arange(W),
                                              torch.arange(D)])
            grid_x          = xv.repeat((21, 1, 1, 1)).type(FT).cuda()
            grid_y          = yv.repeat((21, 1, 1, 1)).type(FT).cuda()
            grid_z          = zv.repeat((21, 1, 1, 1)).type(FT).cuda()

            pred_uvd[self.hand_root, :, :, :, :] = \
                torch.sigmoid(pred_uvd[self.hand_root, :, :, :, :])
            pred_uvd[:, 0, :, :, :] = (pred_uvd[:, 0, :, :, :] + grid_x)/W
            pred_uvd[:, 1, :, :, :] = (pred_uvd[:, 1, :, :, :] + grid_y)/H
            pred_uvd[:, 2, :, :, :] = (pred_uvd[:, 2, :, :, :] + grid_z)/D

            pred_uvd    = pred_uvd.contiguous().view(21, 3, -1)
            pred_conf   = pred_conf.contiguous().view(-1)

            topk_pred_uvd = []
            best_pred_uvd = []
            topk_idx = torch.topk(pred_conf, 10)[1]
            for idx in topk_idx:
                topk_pred_uvd.append(pred_uvd[:, :, idx].cpu().numpy())
            self.best_pred_uvd_list.append(topk_pred_uvd[0])
            self.topk_pred_uvd_list.append(topk_pred_uvd)
            self.pred_conf_list.append(pred_conf.cpu().numpy())

    def save_predictions(self, data_split):
        pred_save = "predict_{}_{}_best.txt".format(self.load_epoch,
                                                    data_split)
        pred_file = Path(ROOT)/self.exp_dir/pred_save
        np.savetxt(pred_file, np.reshape(self.best_pred_uvd_list, (-1, 63)))
        
        pred_save = "predict_{}_{}_topk.txt".format(self.load_epoch,
                                                    data_split)
        pred_file = Path(ROOT)/self.exp_dir/pred_save
        np.savetxt(pred_file, np.reshape(self.topk_pred_uvd_list, (-1, 630)))
        
        pred_save = "predict_{}_{}_conf.txt".format(self.load_epoch,
                                                    data_split)
        pred_file = Path(ROOT)/self.exp_dir/pred_save
        np.savetxt(pred_file, self.pred_conf_list)

        self.pred_list              = []
        self.best_pred_uvd_list     = []
        self.topk_pred_uvd_list     = []
        self.pred_conf_list         = []
        
    # ========================================================
    # DETECT
    # ========================================================

    # def detect(self, img):
    #     with torch.no_grad():
    #         FT          = torch.FloatTensor
    #         img         = np.asarray(img.copy())
    #         ori_w       = img.shape[1]
    #         ori_h       = img.shape[0]
    #         img         = IMG.resize_img(img, (416, 416))
    #         img         = img/255.0
    #         img         = IMG.imgshape2torch(img)
    #         img         = np.expand_dims(img, 0)
    #         img         = FT(img)
    #         img         = img.cuda()
    #         pred_hand   = self.net(img)[0]
    #         W           = pred_hand.shape[3]
    #         H           = pred_hand.shape[2]
    #         D           = 5
    #         batch_size  = 1
    #         pred_hand   = pred_hand.view(batch_size, 64, D, H, W)
    #         pred_hand   = pred_hand.permute(0, 1, 3, 4, 2)
    #         pred_hand   = pred_hand[0]
            
    #         pred_uvd    = pred_hand[:63, :, :, :].view(21, 3, H, W, D)
    #         pred_conf   = torch.sigmoid(pred_hand[63, :, :, :])

    #         yv, xv, zv  = torch.meshgrid([torch.arange(H),
    #                                       torch.arange(W),
    #                                       torch.arange(D)])
    #         grid_x      = xv.repeat((21, 1, 1, 1)).type(FT).cuda()
    #         grid_y      = yv.repeat((21, 1, 1, 1)).type(FT).cuda()
    #         grid_z      = zv.repeat((21, 1, 1, 1)).type(FT).cuda()

    #         pred_uvd[self.hand_root, :, :, :, :] = \
    #             torch.sigmoid(pred_uvd[self.hand_root, :, :, :, :])
    #         pred_uvd[:, 0, :, :, :] = (pred_uvd[:, 0, :, :, :] + grid_x)/W
    #         pred_uvd[:, 1, :, :, :] = (pred_uvd[:, 1, :, :, :] + grid_y)/H
    #         pred_uvd[:, 2, :, :, :] = (pred_uvd[:, 2, :, :, :] + grid_z)/D

    #         pred_uvd        = pred_uvd.contiguous().view(21, 3, -1)
    #         pred_conf       = pred_conf.contiguous().view(-1)

    #         top_idx         = torch.topk(pred_conf, 1)[1]
    #         best_pred_uvd   = pred_uvd[:, :, top_idx].squeeze().cpu().numpy()
    #         best_pred_uvd   = IMG.scale_points_WH(best_pred_uvd, 
    #                                             (1, 1),
    #                                             (ori_w, ori_h))

    #         best_pred_uvd[..., 2]   *= FPHA.REF_DEPTH