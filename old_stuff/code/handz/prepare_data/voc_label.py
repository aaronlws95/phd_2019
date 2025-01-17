import xml.etree.ElementTree as ET
import pickle
import os
from os import listdir, getcwd
from os.path import join
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils.VOC_utils as VOC

# wget http://pjreddie.com/media/files/voc_label.py
# cat 2007_train.txt 2007_val.txt 2012_*.txt > voc_train.txt
sets=[('2012', 'train'), ('2012', 'val'), ('2007', 'train'), ('2007', 'val'), ('2007', 'test')]

classes = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

def convert(size, box):
    dw = 1./size[0]
    dh = 1./size[1]
    x = (box[0] + box[1])/2.0
    y = (box[2] + box[3])/2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    x = x*dw
    w = w*dw
    y = y*dh
    h = h*dh
    return (x,y,w,h)

def convert_annotation(year, image_id):
    in_file_name = join(VOC.DIR, 'VOC%s/Annotations/%s.xml'%(year, image_id))
    in_file = open(in_file_name)
    out_file_name = join(VOC.DIR, 'VOC%s/labels/%s.txt'%(year, image_id))
    out_file = open(out_file_name, 'w')
    tree=ET.parse(in_file)
    root = tree.getroot()
    size = root.find('size')
    w = int(size.find('width').text)
    h = int(size.find('height').text)

    for obj in root.iter('object'):
        difficult = obj.find('difficult').text
        cls = obj.find('name').text
        if cls not in classes or int(difficult) == 1:
            continue
        cls_id = classes.index(cls)
        xmlbox = obj.find('bndbox')
        b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text), float(xmlbox.find('ymin').text), float(xmlbox.find('ymax').text))
        bb = convert((w,h), b)
        out_file.write(str(cls_id) + " " + " ".join([str(a) for a in bb]) + '\n')

# wd = getcwd()

for year, image_set in sets:
    label_file = join(VOC.DIR, 'VOC%s/labels/'%(year))
    if not os.path.exists(label_file):
        os.makedirs(label_file)
    image_ids_file = join(VOC.DIR, 'VOC%s/ImageSets/Main/%s.txt'%(year, image_set))
    image_ids = open(image_ids_file).read().strip().split()
    list_file = open('%s_%s.txt'%(year, image_set), 'w')
    for image_id in image_ids:
        list_file_name = join(VOC.DIR, 'VOC%s/JPEGImages/%s.jpg\n'%(year, image_id))
        # list_file.write('%s/VOCdevkit/VOC%s/JPEGImages/%s.jpg\n'%(wd, year, image_id))
        list_file.write(list_file_name)
        convert_annotation(year, image_id)
    list_file.close()

