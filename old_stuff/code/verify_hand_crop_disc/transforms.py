import torch
import cv2
import random
import numpy as np

def _get_corners(bboxes):
    """ Get corners of bounding boxes
    Args:
        bboxes: Numpy array containing bounding boxes of shape `N X 4` where N
                is the number of bounding boxes and the bounding boxes are
                represented in the format `x1 y1 x2 y2`
    Out:
        corners: Numpy array of shape `N x 8` containing N bounding boxes each
                 described by their corner co-ordinates
                 `x1 y1 x2 y2 x3 y3 x4 y4`
    """
    width   = (bboxes[:,2] - bboxes[:,0]).reshape(-1,1)
    height  = (bboxes[:,3] - bboxes[:,1]).reshape(-1,1)

    x1      = bboxes[:,0].reshape(-1,1)
    y1      = bboxes[:,1].reshape(-1,1)

    x2      = x1 + width
    y2      = y1

    x3      = x1
    y3      = y1 + height

    x4      = bboxes[:,2].reshape(-1,1)
    y4      = bboxes[:,3].reshape(-1,1)

    corners = np.hstack((x1,y1,x2,y2,x3,y3,x4,y4))
    return corners

def _rotate_box(corners, degrees, cx, cy, w, h):
    """ Rotate the bounding box.
    Args:
        corners : Numpy array of shape `N x 8` containing N bounding boxes
                  each described by their corner co-ordinates
                  `x1 y1 x2 y2 x3 y3 x4 y4`
        degrees : angle by which the image is to be rotated in degrees
        cx      : x coordinate of the center of image
                  (about which the box will be rotated)
        cy      : y coordinate of the center of image
                  (about which the box will be rotated)
        h       : height of the image
        w       : width of the image
    Out:
        calc    : Numpy array of shape `N x 8` containing N rotated bounding
                  boxes each described by their corner co-ordinates
                  `x1 y1 x2 y2 x3 y3 x4 y4`
    """
    corners = corners.reshape(-1,2)
    corners = np.hstack((corners, np.ones((corners.shape[0],1),
                                          dtype = type(corners[0][0]))))

    M       = cv2.getRotationMatrix2D((cx, cy), degrees, 1.0)

    cos     = np.abs(M[0, 0])
    sin     = np.abs(M[0, 1])

    nW      = int((h * sin) + (w * cos))
    nH      = int((h * cos) + (w * sin))

    # Prepare the vector to be transformed
    calc    = np.dot(M,corners.T).T
    calc    = calc.reshape(-1,8)
    return calc

def _get_enclosing_box(corners):
    """ Get an enclosing box for rotated corners of a bounding box
    Args:
        corners : Numpy array of shape `N x 8` containing N bounding boxes
                  each described by their corner co-ordinates
                  `x1 y1 x2 y2 x3 y3 x4 y4`
    Out:
        final   : Numpy array containing enclosing bounding boxes of shape
                  `N X 4` where N is the number of bounding boxes and the
                  bounding boxes are represented in the format `x1 y1 x2 y2`
    """
    x_      = corners[:,[0,2,4,6]]
    y_      = corners[:,[1,3,5,7]]

    xmin    = np.min(x_,1).reshape(-1,1)
    ymin    = np.min(y_,1).reshape(-1,1)
    xmax    = np.max(x_,1).reshape(-1,1)
    ymax    = np.max(y_,1).reshape(-1,1)

    final   = np.hstack((xmin, ymin, xmax, ymax))
    return final

def update_rotate_bbox(bboxes, degrees, cx, cy, w, h):
    """ Rotate bbox points
    Args:
        bboxes  : [x_min, y_min, x_max, y_max] (4)
        degrees : angle in degrees
        cx      : x coordinate of the center of image
                  (about which the box will be rotated)
        cy      : y coordinate of the center of image
                  (about which the box will be rotated)
        h       : height of the image
        w       : width of the image
    Out:
        new_bbox: Bbox moved to new location
    """
    corners         = _get_corners(bboxes)
    corners         = np.hstack((corners, bboxes[:, 4:]))
    corners[:, :8]  = _rotate_box(corners[:, :8], degrees, cx, cy, w, h)
    new_bbox        = _get_enclosing_box(corners)
    return new_bbox

class ImgToTorch(object):
    def __call__(self, sample):
        img = sample['img']
        img_out = img/255
        img_out = img.astype('float32')
        img_out = torch.from_numpy(img_out).permute(2, 0, 1)
        sample['img'] = img_out
        return sample

class GroupImgToTorch(object):
    def __call__(self, sample):
        img_list = sample['img']
        img_out = [torch.from_numpy((img/255).astype('float32')).permute(2, 0, 1)
                   for img in img_list]
        sample['img'] = img_out
        return sample

class ImgToNumpy(object):
    def __call__(self, img):
        img_out = img.permute(0, 2, 3, 1).numpy()
        img_out = cv2.normalize(img_out, None, alpha=0, beta=255,
                                norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC3)
        return img_out

class GroupImgToNumpy(object):
    def __call__(self, img_list):
        img_out = [cv2.normalize(img.permute(0, 2, 3, 1).numpy(),
                                None, alpha=0, beta=255,
                                norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC3)
                   for img in img_list]
        return img_out

class PtsResize(object):
    def __init__(self, in_size, out_size):
        self.in_size = in_size
        self.out_size = out_size

    def __call__(self, sample):
        pts_out = sample['pts']
        pts_out[..., 0] *= self.out_size[0]/self.in_size[0]
        pts_out[..., 1] *= self.out_size[1]/self.in_size[1]
        sample['pts'] = pts_out
        return sample

class ImgResize(object):
    def __init__(self, rsz):
        self.rsz = rsz

    def __call__(self, sample):
        img = sample['img']
        img_out = cv2.resize(img, (self.rsz, self.rsz))
        sample['img'] = img_out
        return sample

class GroupImgResize(object):
    def __init__(self, rsz):
        self.rsz = rsz

    def __call__(self, sample):
        img_list = sample['img']
        img_out = [cv2.resize(img, (self.rsz, self.rsz)) for img in img_list]
        sample['img'] = img_out
        return sample

class ImgHFlip(object):
    def __call__(self, sample):
        img_out = sample['img']
        if random.random() > 0.5:
            img_out = np.fliplr(img_out)
        sample['img'] = img_out
        return sample

class ImgPtsHFlip(object):
    def __call__(self, sample):
        img_out = sample['img']
        pts_out = sample['pts']
        if random.random() > 0.5:
            img_out = np.fliplr(img_out)
            pts_out[:, 0] = img_out.shape[1] - pts_out[:, 0]
        sample['img'] = img_out
        sample['pts'] = pts_out
        return sample

class GroupImgHFlip(object):
    def __call__(self, sample):
        img_out = sample['img']
        if random.random() > 0.5:
            img_out = [np.fliplr(img) for img in img_out]
        sample['img'] = img_out
        return sample

class ImgTranslate(object):
    def __init__(self, jitter):
        self.jitter = jitter

    def __call__(self, sample):
        img = sample['img']
        T = np.eye(3)
        T[0, 2] = (random.random()*2 - 1)*self.jitter*img.shape[1]
        T[1, 2] = (random.random()*2 - 1)*self.jitter*img.shape[0]
        img_out = cv2.warpPerspective(img, T,
                                      dsize=(img.shape[1], img.shape[0]),
                                      flags=cv2.INTER_LINEAR)
        sample['img'] = img_out
        return sample

class ImgPtsTranslate(object):
    def __init__(self, jitter):
        self.jitter = jitter

    def __call__(self, sample):
        img = sample['img']
        pts = sample['pts']
        T = np.eye(3)
        T[0, 2] = (random.random()*2 - 1)*self.jitter*img.shape[1]
        T[1, 2] = (random.random()*2 - 1)*self.jitter*img.shape[0]
        img_out = cv2.warpPerspective(img, T,
                                      dsize=(img.shape[1], img.shape[0]),
                                      flags=cv2.INTER_LINEAR)
        pts = pts.reshape(-1, 1, 2)
        pts_out = cv2.perspectiveTransform(pts, T)
        pts_out = pts_out.reshape(-1, 2)
        sample['img'] = img_out
        sample['pts'] = pts_out
        return sample

class GroupImgTranslate(object):
    def __init__(self, jitter):
        self.jitter = jitter

    def __call__(self, sample):
        img_list = sample['img']
        T = np.eye(3)
        T[0, 2] = (random.random()*2 - 1)*self.jitter*img_list[0].shape[1]
        T[1, 2] = (random.random()*2 - 1)*self.jitter*img_list[0].shape[0]
        img_out = [cv2.warpPerspective(img, T,
                                      dsize=(img.shape[1], img.shape[0]),
                                      flags=cv2.INTER_LINEAR)
                    for img in img_list]
        sample['img'] = img_out
        return sample

class ImgPtsScale(object):
    def __init__(self, scale):
        self.scale = scale

    def __call__(self, sample):
        img = sample['img']
        pts = sample['pts']
        ori_shape = img.shape
        scale_x = 1 + random.uniform(-self.scale, self.scale)
        scale_y = 1 + random.uniform(-self.scale, self.scale)
        img_out = cv2.resize(img, None, fx = scale_x, fy = scale_y)

        pts = pts.reshape(-1)
        bbox_area = np.abs(pts[2] - pts[0])*(np.abs(pts[3] - pts[1]))
        x_min = np.maximum(pts[0], 0)
        y_min = np.maximum(pts[1], 0)
        x_max = np.minimum(pts[2], img_out.shape[1])
        y_max = np.minimum(pts[3], img_out.shape[0])
        pts_out = [x_min, y_min, x_max, y_max]
        pts_out = np.reshape(pts_out, (-1, 2))

        canvas = np.zeros(ori_shape, dtype=img.dtype)
        y_lim = int(min(scale_y, 1)*ori_shape[0])
        x_lim = int(min(scale_x, 1)*ori_shape[1])
        canvas[:y_lim, :x_lim, :] =  img[:y_lim,:x_lim, :]
        img_out = canvas

        sample['img'] = img_out
        sample['pts'] = pts_out
        return sample

class ImgRotate(object):
    def __init__(self, deg):
        self.deg = deg

    def __call__(self, sample):
        img = sample['img']
        a = random.random()*2*self.deg - self.deg
        R = cv2.getRotationMatrix2D(center=(img.shape[1]/2, img.shape[0]/2), angle=a, scale=1)
        img_out = cv2.warpAffine(img, R, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR)
        sample['img'] = img_out
        return sample

class ImgBboxRotate(object):
    def __init__(self, deg):
        self.deg = deg

    def __call__(self, sample):
        img = sample['img']
        pts = sample['pts']
        a = random.random()*2*self.deg - self.deg
        R = cv2.getRotationMatrix2D(center=(img.shape[1]/2, img.shape[0]/2), angle=a, scale=1)
        img_out = cv2.warpAffine(img, R, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR)

        pts_out = pts.reshape(1, -1)
        pts_out = update_rotate_bbox(pts_out, a, img.shape[0]/2, img.shape[1]/2, img.shape[1], img.shape[0])
        pts_out = pts_out.reshape(-1, 2)

        sample['img'] = img_out
        sample['pts'] = pts_out
        return sample

class ImgPtsRotate(object):
    def __init__(self, deg):
        self.deg = deg

    def __call__(self, sample):
        img = sample['img']
        pts = sample['pts']
        a = random.random()*2*self.deg - self.deg
        R = cv2.getRotationMatrix2D(center=(img.shape[1]/2, img.shape[0]/2), angle=a, scale=1)
        img_out = cv2.warpAffine(img, R, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR)

        pts_out = np.hstack((pts, np.ones((pts.shape[0], 1))))
        pts_out = np.dot(R, pts_out.T).T

        sample['img'] = img_out
        sample['pts'] = pts_out
        return sample

class ImgDistortHSV(object):
    def __init__(self, hue, sat, val):
        self.hue = hue
        self.sat = sat
        self.val = val

    def __call__(self, sample):
        img = sample['img']
        img_hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        H = img_hsv[:, :, 0].astype('float32')
        S = img_hsv[:, :, 1].astype('float32')
        V = img_hsv[:, :, 2].astype('float32')

        hue = random.uniform(-self.hue, self.hue)
        sat = (random.random()*2 - 1)*self.sat + 1
        val = (random.random()*2 - 1)*self.val + 1

        H += hue*255
        H[H > 255] -= 255
        H[H < 255] += 255
        S *= sat
        V *= val

        img_hsv[:, :, 0] = H
        img_hsv[:, :, 1] = S if sat < 1 else S.clip(None, 255)
        img_hsv[:, :, 2] = V if val < 1 else V.clip(None, 255)
        img_out = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
        sample['img'] = img_out
        return sample

class GroupImgDistortHSV(object):
    def __init__(self, hue, sat, val):
        self.hue = hue
        self.sat = sat
        self.val = val

    def __call__(self, sample):
        img_list = sample['img']
        img_hsv = [cv2.cvtColor(img, cv2.COLOR_RGB2HSV) for img in img_list]
        H = [img[:, :, 0].astype('float32') for img in img_hsv]
        S = [img[:, :, 1].astype('float32') for img in img_hsv]
        V = [img[:, :, 2].astype('float32') for img in img_hsv]

        hue = random.uniform(-self.hue, self.hue)
        sat = (random.random()*2 - 1)*self.sat + 1
        val = (random.random()*2 - 1)*self.val + 1

        new_H = []
        for x in H:
            new_x = x + hue*255
            new_x[new_x > 255] -= 255
            new_x[new_x < 255] += 255
            new_H.append(new_x)
        S = [x*sat for x in S]
        V = [v*val for v in V]

        img_out = []
        for i in range(len(img_hsv)):
            new_img = img_hsv[i].copy()
            new_img[:, :, 0] = new_H[i]
            new_img[:, :, 1] = S[i] if sat < 1 else S[i].clip(None, 255)
            new_img[:, :, 2] = V[i] if val < 1 else V[i].clip(None, 255)
            img_out.append(new_img)
        img_out = [cv2.cvtColor(img, cv2.COLOR_HSV2RGB) for img in img_out]
        sample['img'] = img_out
        return sample

class PtsScale(object):
    def __init__(self, i_shape, o_shape):
        self.i_shape = i_shape
        self.o_shape = o_shape

    def __call__(self, sample):
        pts_out = sample['pts']
        pts_out[..., 0] *= self.o_shape[0]/self.i_shape[0]
        pts_out[..., 1] *= self.o_shape[1]/self.i_shape[1]
        sample['pts'] = pts_out
        return sample