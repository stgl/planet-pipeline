def chips_to_tfrecords(*args, **kwargs):
    
    import glob
    import tensorflow as tf
    from object_detection.utils import dataset_util
    from PIL import Image
    import os, io
    import json
    import random
    from landslide_pipeline.pipeline import TRAINING_FRACTION

    def create_tf_example(image_object, extent_dictionary):

        (_, _, width, height) = image_object.getbbox()
        filename = str.encode(image_object.filename)
        iodata = io.BytesIO()
        
        image_object.save(iodata, format = image_object.format) # Encoded image bytes
        encoded_image_data = iodata.getvalue()
        xmins = [extent_dictionary['xmin']]
        xmaxs = [extent_dictionary['xmax']]
        ymins = [extent_dictionary['ymin']]
        ymaxs = [extent_dictionary['ymax']] 
        
        classes_text = [b'landslide'] 
        classes = [0] 

        image_format = None
        
        if image_object.format == 'PNG':
            image_format = b'png'
        elif image_object.format == 'JPG':
            image_format = b'jpg'
            
        tf_example = tf.train.Example(features=tf.train.Features(feature={
            'image/height': dataset_util.int64_feature(height),
            'image/width': dataset_util.int64_feature(width),
            'image/filename': dataset_util.bytes_feature(filename),
            'image/source_id': dataset_util.bytes_feature(filename),
            'image/encoded': dataset_util.bytes_feature(encoded_image_data),
            'image/format': dataset_util.bytes_feature(image_format),
            'image/object/bbox/xmin': dataset_util.float_list_feature(xmins),
            'image/object/bbox/xmax': dataset_util.float_list_feature(xmaxs),
            'image/object/bbox/ymin': dataset_util.float_list_feature(ymins),
            'image/object/bbox/ymax': dataset_util.float_list_feature(ymaxs),
            'image/object/class/text': dataset_util.bytes_list_feature(classes_text),
            'image/object/class/label': dataset_util.int64_list_feature(classes),
        }))

        return tf_example

    chips = glob.glob('image_chips/*.png')

    if not os.path.exists('data'):
        os.makedirs('data')

    writer_train = tf.python_io.TFRecordWriter('data/landslide_train.record')
    writer_val = tf.python_io.TFRecordWriter('data/landslide_val.record')
    
    for chip in chips:
        image = Image.open(chip)
        extent_dictionary = json.load(open(chip.replace('.png','.json'), 'r'))
        tf_example = create_tf_example(image, extent_dictionary)
        if random.random() >= TRAINING_FRACTION:
            writer_val.write(tf_example.SerializeToString())
        else:
            writer_train.write(tf_example.SerializeToString())
        
    writer_train.close()
    writer_val.close()
    
    f = open('data/landslide.pbtxt', 'w')
    f.write("item {\n  id: 1\n  name:'landslide'\n}")
    f.close()
    
    return kwargs
        
def train(*args, **kwargs):
    
    import subprocess
    from landslide_pipeline.pipeline import TRAINING_CONFIG_PATH, TRAINING_EXEC_PATH, EVAL_EXEC_PATH, TRAINING_PATH, EVAL_PATH
    import os
    
    if not os.path.exists(TRAINING_PATH):
        os.makedirs(TRAINING_PATH)
    if not os.path.exists(EVAL_PATH):
        os.makedirs(EVAL_PATH)
        
    subprocess.Popen(['python', TRAINING_EXEC_PATH, '--logtostderr', '--pipeline_config_path=' + TRAINING_CONFIG_PATH, '--train_dir=' + TRAINING_PATH])
    subprocess.Popen(['python', EVAL_EXEC_PATH, '--logtostderr', '--pipeline_config_path=' + TRAINING_CONFIG_PATH, '--checkpoint_dir=' + TRAINING_PATH, '--eval_dir=' + EVAL_PATH])
    
    return kwargs

def export(*args, **kwargs):
    
    import subprocess
    from landslide_pipeline.pipeline import TRAINING_CONFIG_PATH, TRAINING_PATH, TRAINING_EXPORT_EXEC_PATH, TRAINING_EXPORT_PATH
    import glob
    ckpts = glob.glob('./models/model/train/model.ckpt-*.meta')
    number = 0
    
    for ckpt in ckpts:
        if float(ckpt.split('.ckpt-')[1].replace('.meta','')) > number:
            number = float(ckpt.split('.ckpt-')[1].replace('.meta',''))
    
    number = int(number)
    
    subprocess.call(['python', TRAINING_EXPORT_EXEC_PATH, '--input_type', 'image_tensor', '--pipeline_config_path', TRAINING_CONFIG_PATH, '--trained_checkpoint_prefix', TRAINING_PATH + '/model.ckpt-' + str(number), '--output_directory', TRAINING_EXPORT_PATH])

def classify(*args, **kwargs):
    
    import numpy as np
    import os
    import six.moves.urllib as urllib
    import sys
    import tarfile
    import tensorflow as tf
    import zipfile
    
    from collections import defaultdict
    from io import StringIO
    from matplotlib import pyplot as plt
    from PIL import Image
    
    # This is needed since the notebook is stored in the object_detection folder.
    sys.path.append("..")
    from object_detection.utils import ops as utils_ops
    
    if tf.__version__ < '1.4.0':
        raise ImportError('Please upgrade your tensorflow installation to v1.4.* or later!')
  
    from utils import label_map_util
    from utils import visualization_utils as vis_util
    PATH_TO_CKPT = './models/model/export/frozen_inference_graph.pb'
    PATH_TO_LABELS = './data/landslide.pbtxt'
    
    NUM_CLASSES = 1
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')
    
    def load_image_into_numpy_array(image):
        (im_width, im_height) = image.size
        return np.array(image.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)
        
    IMAGE_SIZE = (12, 8)
    label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
    category_index = label_map_util.create_category_index(categories)
    
    def run_inference_for_single_image(image, graph):
        with graph.as_default():
            with tf.Session() as sess:
                # Get handles to input and output tensors
                ops = tf.get_default_graph().get_operations()
                all_tensor_names = {output.name for op in ops for output in op.outputs}
                tensor_dict = {}
                for key in [
                    'num_detections', 'detection_boxes', 'detection_scores',
                    'detection_classes', 'detection_masks'
                ]:
                    tensor_name = key + ':0'
                    if tensor_name in all_tensor_names:
                        tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
                          tensor_name)
                if 'detection_masks' in tensor_dict:
                    # The following processing is only for single image
                    detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
                    detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
                    # Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
                    real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
                    detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
                    detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
                    detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
                        detection_masks, detection_boxes, image.shape[0], image.shape[1])
                    detection_masks_reframed = tf.cast(
                        tf.greater(detection_masks_reframed, 0.5), tf.uint8)
                    # Follow the convention by adding back the batch dimension
                    tensor_dict['detection_masks'] = tf.expand_dims(
                        detection_masks_reframed, 0)
                image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')
                
                # Run inference
                output_dict = sess.run(tensor_dict,
                                       feed_dict={image_tensor: np.expand_dims(image, 0)})
                
                # all outputs are float32 numpy arrays, so convert types as appropriate
                output_dict['num_detections'] = int(output_dict['num_detections'][0])
                output_dict['detection_classes'] = output_dict[
                    'detection_classes'][0].astype(np.uint8)
                output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
                output_dict['detection_scores'] = output_dict['detection_scores'][0]
                if 'detection_masks' in output_dict:
                    output_dict['detection_masks'] = output_dict['detection_masks'][0]
        return output_dict

    from landslide_pipeline.pipeline import CLASSIFY_IMAGE
    
    image = Image.open(CLASSIFY_IMAGE)
    image_np = load_image_into_numpy_array(image)
    output_dict = run_inference_for_single_image(image_np, detection_graph)
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_np,
        output_dict['detection_boxes'],
        output_dict['detection_classes'],
        output_dict['detection_scores'],
        category_index,
        instance_masks=output_dict.get('detection_masks'),
        use_normalized_coordinates=True,
        line_thickness=8)
    plt.figure(figsize=IMAGE_SIZE)
    plt.imshow(image_np)
    
    kwargs['output_dict'] = output_dict
    return kwargs
    