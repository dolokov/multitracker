
import os
import numpy as np 
import tensorflow as tf 
tf.get_logger().setLevel('INFO')
from glob import glob 
from random import shuffle 
import time 
from datetime import datetime
import cv2 as cv 
import h5py


from multitracker import util 
from multitracker.be import video
from multitracker.keypoint_detection import heatmap_drawing, model 
from multitracker.keypoint_detection import predict 
from multitracker.tracking.inference import load_model as load_keypoint_model
from multitracker.tracking.inference import load_data, load_model, get_heatmaps_keypoints
from multitracker.keypoint_detection.roi_segm import inference_heatmap, get_center
from multitracker.tracking.tracklets import get_tracklets
from multitracker.tracking.clustering import get_clustlets
from multitracker.object_detection import finetune
from multitracker.tracking.deep_sort import deep_sort_app


def main(args):
    tstart = time.time()
    config = model.get_config(project_id = args.project_id)
    config['project_id'] = args.project_id
    config['video_id'] = args.video_id
    config['keypoint_model'] = args.keypoint_model
    config['autoencoder_model'] = args.autoencoder_model 
    config['objectdetection_model'] = args.objectdetection_model
    config['minutes'] = args.minutes
    config['fixed_number'] = args.fixed_number
    config['n_blocks'] = 4

    # <load frames>
    output_dir = '/tmp/multitracker/object_detection/predictions/%i' % (config['video_id'])
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    print('[*] writing object detection bounding boxes %f minutes of video %i frames to %s' % (config['minutes'],config['video_id'],output_dir))

    frames_dir = os.path.expanduser('~/data/multitracker/projects/%i/%i/frames/train' % (config['project_id'], config['video_id']))
    frame_files = sorted(glob(os.path.join(frames_dir,'*.png')))
    if len(frame_files) == 0:
        raise Exception("ERROR: no frames found in " + str(frames_dir))
    
    if config['minutes']> 0:
        frame_files = frame_files[:int(30. * 60. * config['minutes'])]

    # </load frames>

    # <train models>
    # 1) animal bounding box finetuning -> trains and inferences 
    config['objectdetection_max_steps'] = 30000
    # train object detector
    now = str(datetime.now()).replace(' ','_').replace(':','-').split('.')[0]
    checkpoint_directory_object_detection = os.path.expanduser('~/checkpoints/bbox_detection/%s_vid%i/%s' % (config['project_name'], int(config['video_id']),now))
    object_detect_restore = None 
    if 'objectdetection_model' in config and config['objectdetection_model'] is not None:
        object_detect_restore = config['objectdetection_model']
    
    detection_model = None
    if object_detect_restore is None:
        detection_model = finetune.finetune(config, checkpoint_directory_object_detection, checkpoint_restore = object_detect_restore)
        print('[*] trained object detection model',checkpoint_directory_object_detection)
        config['object_detection_model'] = checkpoint_directory_object_detection

    ## crop bbox detections and train keypoint estimation on extracted regions
    #point_classification.calculate_keypoints(config, detection_file_bboxes)
    
    # 2) train autoencoder for tracking appearence vector
    if config['autoencoder_model'] is None:
        config_autoencoder = autoencoder.get_autoencoder_config()
        config_autoencoder['project_id'] = config['project_id']
        config_autoencoder['video_id'] = config['video_id']
        config['autoencoder_model'] = autoencoder.train(config_autoencoder)
    print('[*] trained autoencoder model',config['autoencoder_model'])

    # 4) train keypoint estimator model
    if config['keypoint_model'] is None:
        config['max_steps'] = 50000
        model.create_train_dataset(config)
        config['keypoint_model'] = model.train(config)
    print('[*] trained keypoint_model',config['keypoint_model'])
    # </train models>

    # <load models>
    # load trained object detection model
    if detection_model is None:
        #ckpt_detect, model_config_detect, detection_model = finetune.restore_weights(config['objectdetection_model'])
        from object_detection.utils import config_util
        from object_detection.builders import model_builder
        configs = config_util.get_configs_from_pipeline_file(finetune.get_pipeline_config())
        model_config = configs['model']
        model_config.ssd.num_classes = 1
        detection_model = model_builder.build(model_config=model_config, is_training=False)
        ckpt = tf.compat.v2.train.Checkpoint(detection_model=detection_model)
        ckpt.restore(tf.train.latest_checkpoint(config['objectdetection_model'])).expect_partial()

    # load trained autoencoder model for Deep Sort Tracking 
    encoder_model = deep_sort_app.load_feature_extractor(config)

    # load trained keypoint model
    keypoint_model = load_keypoint_model(config['keypoint_model'])
    # </load models>

    # 3) run bbox tracking deep sort with fixed tracks
    min_confidence = 0.5 # Detection confidence threshold. Disregard all detections that have a confidence lower than this value.
    nms_max_overlap = 1.0 # Non-maxima suppression threshold: Maximum detection overlap
    max_cosine_distance = 0.2 # Gating threshold for cosine distance metric (object appearance).
    nn_budget = None # Maximum size of the appearance descriptors gallery. If None, no budget is enforced.
    display = True # dont write vis images

    deep_sort_app.run(config, detection_model, encoder_model, keypoint_model, output_dir, 
            min_confidence, nms_max_overlap, max_cosine_distance, nn_budget, display)
    
    print('[*] done tracking')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--objectdetection_model', required=False,default=None)
    parser.add_argument('--keypoint_model', required=False,default=None)
    parser.add_argument('--autoencoder_model', required=False,default=None)
    parser.add_argument('--project_id',required=True,type=int)
    parser.add_argument('--video_id',required=True,type=int)
    parser.add_argument('--minutes',required=False,default=0.0,type=float)
    parser.add_argument('--thresh_detection',required=False,default=0.5,type=float)
    parser.add_argument('--fixed_number',required=False,default=4,type=int)
    args = parser.parse_args()
    
    #assert args.objectdetection_model is None or (args.objectdetection_model is not None and args.objectdetection_model.endswith('.index'))
    assert args.keypoint_model is None or (args.keypoint_model is not None and args.keypoint_model.endswith('.h5'))

    main(args)