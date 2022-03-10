import mermaid.finite_differences as fdt
import numpy as np
import torch
import torch.nn as nn
from utils.general import get_class
from utils.utils import sigmoid_decay


class loss(nn.Module):
    def __init__(self, opt):
        super(loss, self).__init__()
        self.sim_factor = 1.
        self.sim = get_class(opt["sim_class", 'layers.losses.NCCLoss', 'Similarity class'])()
        self.initial_reg_factor = opt[('initial_reg_factor', 10, 'initial regularization factor')]
        """initial regularization factor"""
        self.min_reg_factor = opt[('min_reg_factor', 1e-3, 'minimum regularization factor')]
        """minimum regularization factor"""
        self.reg_factor_decay_from = opt[('reg_factor_decay_from', 10, 'regularization factor starts to decay from # epoch')]

    def forward(self, input):
        # Parse input data
        source_proj = input["source_proj"]
        target_proj = input["target_proj"]
        warped_proj = input["warped_proj"]
        warped_proj_inv = input["warped_proj_inv"]

        params = input["params"]
        epoch = input["epoch"]


        sim_loss = self.sim(warped_proj, target_proj) + self.sim(source_proj, warped_proj_inv)
        reg_loss = self.compute_reg_loss(params[0]) + self.compute_reg_loss(params[1])
        total_loss = self.sim_factor * sim_loss + self.get_reg_factor(epoch) * reg_loss
        outputs = {
            "total_loss": total_loss,
            "sim_loss": sim_loss.item(),
            "reg_loss": reg_loss.item()
        }

        return outputs

    def get_reg_factor(self, epoch):
        """
        get the regularizer factor according to training strategy

        :return:
        """
        decay_factor = 2
        factor_scale = float(
            max(sigmoid_decay(epoch, static=self.reg_factor_decay_from, k=decay_factor) * self.initial_reg_factor , self.min_reg_factor))
        return factor_scale
    
    def compute_reg_loss(self, affine_param):
        disp = affine_param
        spacing = 1. / ( np.array(affine_param.shape[2:]) - 1)
        fd = fdt.FD_torch(spacing*2)
        l2 = fd.dXc(disp[:, 0, ...])**2 +\
            fd.dYc(disp[:, 0, ...])**2 +\
            fd.dZc(disp[:, 0, ...])**2 +\
            fd.dXc(disp[:, 1, ...])**2 +\
            fd.dYc(disp[:, 1, ...])**2 +\
            fd.dZc(disp[:, 1, ...])**2 +\
            fd.dXc(disp[:, 2, ...])**2 +\
            fd.dYc(disp[:, 2, ...])**2 +\
            fd.dZc(disp[:, 2, ...])**2

        reg = torch.mean(l2, dim=[1,2,3]).sum()
        return reg
