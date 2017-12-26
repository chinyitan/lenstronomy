__author__ = 'sibirrer'

from lenstronomy.LensModel.lens_model import LensModel
import lenstronomy.Util.param_util as param_util

import scipy.optimize
import numpy as np


class Solver4Point(object):
    """
    class to make the constraints for the solver
    """
    def __init__(self, lens_model_list=['SPEP'], foreground_shear=False, decoupling=True):
        self._lens_mode_list = lens_model_list
        self.lensModel = LensModel(lens_model_list, foreground_shear)
        self._decoupling = decoupling

    def constraint_lensmodel(self, x_pos, y_pos, kwargs_list, kwargs_else=None, xtol=1.49012e-10):
        """

        :param x_pos: list of image positions (x-axis)
        :param y_pos: list of image position (y-axis)
        :param init: initial parameters
        :param kwargs_list: list of lens model kwargs
        :return: updated lens model that satisfies the lens equation for the point sources
        """
        init = self._extract_array(kwargs_list)
        if self._decoupling:
            alpha_0_x, alpha_0_y = self.lensModel.alpha(x_pos, y_pos, kwargs_list, kwargs_else)
            alpha_1_x, alpha_1_y = self.lensModel.alpha(x_pos, y_pos, kwargs_list, kwargs_else, k=0)
            x_sub = alpha_1_x - alpha_0_x
            y_sub = alpha_1_y - alpha_0_y
        else:
            x_sub, y_sub = np.zeros(4), np.zeros(4)
        a = self._subtract_constraint(x_sub, y_sub)
        x = self.solve(x_pos, y_pos, init, kwargs_list, kwargs_else, a, xtol)
        kwargs_list = self._update_kwargs(x, kwargs_list)
        return kwargs_list

    def solve(self, x_pos, y_pos, init, kwargs_list, kwargs_else, a, xtol=1.49012e-10):
        x = scipy.optimize.fsolve(self._F, init, args=(x_pos, y_pos, kwargs_list, kwargs_else, a), xtol=xtol)#, factor=0.1)
        return x

    def _F(self, x, x_pos, y_pos, kwargs_list, kwargs_else, a=0):
        kwargs_list = self._update_kwargs(x, kwargs_list)
        if self._decoupling:
            beta_x, beta_y = self.lensModel.ray_shooting(x_pos, y_pos, kwargs_list, kwargs_else, k=0)
        else:
            beta_x, beta_y = self.lensModel.ray_shooting(x_pos, y_pos, kwargs_list, kwargs_else)
        y = np.zeros(6)
        y[0] = beta_x[0] - beta_x[1]
        y[1] = beta_x[0] - beta_x[2]
        y[2] = beta_x[0] - beta_x[3]
        y[3] = beta_y[0] - beta_y[1]
        y[4] = beta_y[0] - beta_y[2]
        y[5] = beta_y[0] - beta_y[3]
        return y - a

    def _subtract_constraint(self, x_sub, y_sub):
        """

        :param x_pos:
        :param y_pos:
        :param x_sub:
        :param y_sub:
        :return:
        """
        a = np.zeros(6)
        a[0] = - x_sub[0] + x_sub[1]
        a[1] = - x_sub[0] + x_sub[2]
        a[2] = - x_sub[0] + x_sub[3]
        a[3] = - y_sub[0] + y_sub[1]
        a[4] = - y_sub[0] + y_sub[2]
        a[5] = - y_sub[0] + y_sub[3]
        return a

    def _update_kwargs(self, x, kwargs_list):
        """

        :param x: list of parameters corresponding to the free parameter of the first lens model in the list
        :param kwargs_list: list of lens model kwargs
        :return: updated kwargs_list
        """
        lens_model = self._lens_mode_list[0]
        if lens_model in ['SPEP', 'SPEMD', 'SIE', 'COMPOSITE']:
            [theta_E, e1, e2, center_x, center_y, no_sens_param] = x
            phi_G, q = param_util.elliptisity2phi_q(e1, e2)
            kwargs_list[0]['theta_E'] = theta_E
            kwargs_list[0]['q'] = q
            kwargs_list[0]['phi_G'] = phi_G
            kwargs_list[0]['center_x'] = center_x
            kwargs_list[0]['center_y'] = center_y
        elif lens_model in ['NFW_ELLIPSE']:
            [theta_Rs, e1, e2, center_x, center_y, no_sens_param] = x
            phi_G, q = param_util.elliptisity2phi_q(e1, e2)
            kwargs_list[0]['theta_Rs'] = theta_Rs
            kwargs_list[0]['q'] = q
            kwargs_list[0]['phi_G'] = phi_G
            kwargs_list[0]['center_x'] = center_x
            kwargs_list[0]['center_y'] = center_y
        elif lens_model in ['SHAPELET_CART']:
            [c00, c10, c01, c20, c11, c02] = x
            coeffs = list(kwargs_list[0]['coeffs'])
            coeffs[1: 6] = [c10, c01, c20, c11, c02]
            kwargs_list[0]['coeffs'] = coeffs
        else:
            raise ValueError("Lens model %s not supported for 4-point solver!" % lens_model)
        return kwargs_list

    def _extract_array(self, kwargs_list):
        """
        inverse of _update_kwargs
        :param kwargs_list:
        :return:
        """
        lens_model = self._lens_mode_list[0]
        if lens_model in ['SPEP', 'SPEMD', 'SIE', 'COMPOSITE']:
            q = kwargs_list[0]['q']
            phi_G = kwargs_list[0]['phi_G']
            center_x = kwargs_list[0]['center_x']
            center_y = kwargs_list[0]['center_y']
            e1, e2 = param_util.phi_q2_elliptisity(phi_G, q)
            theta_E = kwargs_list[0]['theta_E']
            x = [theta_E, e1, e2, center_x, center_y, 0]
        elif lens_model in ['NFW_ELLIPSE']:
            q = kwargs_list[0]['q']
            phi_G = kwargs_list[0]['phi_G']
            center_x = kwargs_list[0]['center_x']
            center_y = kwargs_list[0]['center_y']
            e1, e2 = param_util.phi_q2_elliptisity(phi_G, q)
            theta_Rs = kwargs_list[0]['theta_Rs']
            x = [theta_Rs, e1, e2, center_x, center_y, 0]
        elif lens_model in ['SHAPELETS_CART']:
            coeffs = list(kwargs_list[0]['coeffs'])
            [c10, c01, c20, c11, c02] = coeffs[1: 6]
            x = [0, c10, c01, c20, c11, c02]
        else:
            raise ValueError("Lens model %s not supported for 4-point solver!" % lens_model)
        return x



