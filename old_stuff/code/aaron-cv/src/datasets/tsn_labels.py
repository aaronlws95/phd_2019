import os
import os.path
import torch.utils.data                         as data
import numpy                                    as np
from PIL                    import Image
from numpy.random           import randint

from src.utils              import DATA_DIR
class VideoRecord(object):
    def __init__(self, row):
        self._data = row

    @property
    def path(self):
        return self._data[0]

    @property
    def num_frames(self):
        return int(self._data[1])

    @property
    def label(self):
        return int(self._data[2])

class TSN_Labels(data.Dataset):
    def __init__(self, cfg, list_file, transform, random_shift, test_mode):
        super().__init__()
        img_root = cfg['img_root']
        self.list_file = os.path.join(DATA_DIR, 
                                      img_root,
                                      list_file)
        if test_mode:
            self.num_segments = int(cfg['test_segments'])
        else:
            self.num_segments = int(cfg['num_segments'])
        self.modality = cfg['modality']
        if self.modality == 'RGB':
            self.new_length = 1
        elif self.modality in ['Flow', 'RGBDiff']:
            self.new_length = 5
        self.image_tmpl = cfg['img_tmpl']

        self.transform      = transform
        self.random_shift   = random_shift
        self.test_mode      = test_mode

        if self.modality == 'RGBDiff':
            # Diff needs one more image to calculate diff
            self.new_length += 1

        self._parse_list()

        if cfg['len'] == 'max':
            self.num_data = len(self.video_list)
        else:
            self.num_data = int(cfg['len'])

    def _load_image(self, directory, idx):
        if self.modality == 'RGB' or self.modality == 'RGBDiff':
            return [Image.open(os.path.join(directory, self.image_tmpl.format(idx))).convert('RGB')]
        elif self.modality == 'Flow':
            x_img = Image.open(os.path.join(directory, self.image_tmpl.format('x', idx))).convert('L')
            y_img = Image.open(os.path.join(directory, self.image_tmpl.format('y', idx))).convert('L')
        
            return [x_img, y_img]

    def _parse_list(self):
        self.video_list = [VideoRecord(x.strip().split(' ')) for x in open(self.list_file)]

    def _sample_indices(self, record):
        """
        :param record: VideoRecord
        :return: list
        """
        average_duration = (record.num_frames - self.new_length + 1) // self.num_segments
        if average_duration > 0:
            offsets = np.multiply(list(range(self.num_segments)), average_duration) + randint(average_duration, size=self.num_segments)
        elif record.num_frames > self.num_segments:
            offsets = np.sort(randint(record.num_frames - self.new_length + 1, size=self.num_segments))
        else:
            offsets = np.zeros((self.num_segments,))
        return offsets

    def _get_val_indices(self, record):
        if record.num_frames > self.num_segments + self.new_length - 1:
            tick = (record.num_frames - self.new_length + 1) / float(self.num_segments)
            offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)])
        else:
            offsets = np.zeros((self.num_segments,))

        return offsets

    def _get_test_indices(self, record):
        tick = (record.num_frames - self.new_length + 1) / float(self.num_segments)
        offsets = np.array([int(tick / 2.0 + tick * x) for x in range(self.num_segments)])

        return offsets

    def __getitem__(self, index):
        record = self.video_list[index]

        if not self.test_mode:
            segment_indices = self._sample_indices(record) if self.random_shift else self._get_val_indices(record)
        else:
            segment_indices = self._get_test_indices(record)

        return self.get(record, segment_indices)

    def get(self, record, indices):
        images = list()
        for seg_ind in indices:
            p = int(seg_ind)
            for i in range(self.new_length):
                seg_imgs = self._load_image(record.path, p)
                images.extend(seg_imgs)
                if p < record.num_frames:
                    p += 1
        process_data = self.transform(images)
        
        return process_data, record.label

    def __len__(self):
        return self.num_data