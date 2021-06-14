import numpy as np

import logging
import warnings

from .visualization import vis_image, vis_grayscale, vis_categorical_mask, vis_flow, display_plt, animate_plt
from .utils import isinteger, calculate_grid_layout, tensor_to_array

logger = logging.getLogger('TorchShow')
logger.setLevel(logging.INFO)

vis_func_dict = dict(image=vis_image,
                     grayscale=vis_grayscale,
                     categorical_mask=vis_categorical_mask,
                     flow=vis_flow)


def show(x, display=True, save=False, **kwargs):
    vis_list = None
    
    x = tensor_to_array(x)

    if isinstance(x, (np.ndarray)):
        x = x.copy()
        nrows = kwargs.get('nrows', None)
        ncols = kwargs.get('ncols', None)
        channel_mode = kwargs.get('channel_mode', 'auto')
        if channel_mode == 'auto':
            if x.shape[-1] in [1,2,3]:
                channel_mode = 'channel_last'
            else:
                channel_mode = 'channel_first'
                
        if x.ndim == 4: # (N, C, H, W) like array
            if channel_mode == 'channel_first':
                N, _, H, W = x.shape
            elif channel_mode == 'channel_last':
                N, H, W, _ = x.shape
            
            nrows, ncols = calculate_grid_layout(N, H, W, nrows, ncols)
            assert (nrows * ncols >= N)
            vis_list = [list(x[i:i + ncols]) for i in range(0, N, ncols)] # vis_list is now an list of list

            
        elif x.ndim == 3: # (C, H, W) like array
            if channel_mode == 'channel_first': # C, H, W
                C, H, W = x.shape
            elif channel_mode == 'channel_last':
                H, W, C = x.shape
                
            if C <=3:
                vis_list = [[x]] # if C is in [1,2,3], visualize it as single image
            else: # when C is greater than 3 (e.g. feature maps), visualize it in grid layout
                if channel_mode == 'channel_last':
                    x = np.transpose(x, (2,0,1)) # Transpose to C, H, W because we will visualize each individual channel
                nrows, ncols = calculate_grid_layout(C, H, W, nrows, ncols)
                assert (nrows * ncols >= C)
                vis_list = [list(x[i:i + ncols]) for i in range(0, C, ncols)]
                
        elif x.ndim == 2: # (H, W)
            vis_list = [[x]]
            
        else:
            raise TypeError("Unsupported shape of numpy array {} .".format(x.shape))
        
    elif isinstance(x, list):
        if isinstance(x[0], np.ndarray): # if the input is list of images [img1, img2], make it [[img1, img2]]
            vis_list = [x]
        else:
            vis_list = x

    else:
        raise NotImplementedError("Does not support input type \"{}\"".format(type(x)))


    # vis_list:  list of list. Outer list is for rows and inner list is the images in each row.
    # e.g.[[img1, img2], 
    #      [img3, img4]]
    
    assert isinstance(vis_list, list)
    assert np.array([isinstance(l, list) for l in vis_list]).all() # Now the input should be list of list

    plot_list = []

    for row in vis_list: 
        list_per_row = []
        for img in row:
            vis, plot_cfg = visualize(img, **kwargs)
            list_per_row.append((vis, plot_cfg))
        plot_list.append(list_per_row)
    
    if display:
        display_plt(plot_list, **kwargs)


def show_video(x, display=True, **kwargs):
    video_list = None
    
    x = tensor_to_array(x)

    if isinstance(x, (np.ndarray)):
        x = x.copy()
        assert x.ndim in [3,4], "only support 3D array (N, H, W) or 4D array (N, C, H, W) in video mode"
        video_list = [[x]] # for a single video, make it [[vid]]
        
    elif isinstance(x, list):
        if isinstance(x[0], np.ndarray): # if the input is list of array [vid1, vid2], make it [[vid1, vid2]]
            video_list = [x]
        else:
            video_list = x
            
    else:
        raise NotImplementedError("Does not support input type \"{}\"".format(type(x)))


    # video_list:  list of list. Outer list is for rows and inner list is the images in each row.
    # e.g.[[img1, img2], 
    #      [img3, img4]]
    
    assert isinstance(video_list, list)
    assert np.array([isinstance(l, list) for l in video_list]).all() # Now the input should be list of list

    video_length = max([len(vid) for l in video_list for vid in l])

    video_vis_list = [] # Reorganize frames into [t, row, col, img]

    for t in range(video_length): 
        frames_at_t = [] # [[frame_t_video1, frame_t_video2],
                         #  [frame_t_video3, frame_t_video4]]
        for row in video_list: 
            frames_at_t_per_row = [] # [frame_t_video1, frame_t_video2]
            for video in row:
                if t < len(video):
                    img = video[t]
                    vis, plot_cfg = visualize(img, **kwargs)
                else:
                    vis, plot_cfg = (None, None)

                frames_at_t_per_row.append((vis, plot_cfg)) # 
            frames_at_t.append(frames_at_t_per_row) # 
        video_vis_list.append(frames_at_t)
        
    if display:
        return animate_plt(video_vis_list, **kwargs)
        

def visualize(x, 
         mode='auto',
         auto_permute=True,
         **kwargs):

    assert isinstance(x, np.ndarray)
    
    shape = x.shape
    ndim = len(shape)
    assert ndim <= 3
    
    if auto_permute:
        if (ndim == 3) and (shape[0] in [1, 2, 3]): # For C, H, W kind of array.
            logger.debug('Detected input shape {} is in CHW format, TorchShow will automatically convert it to HWC format'.format(shape))
            x = np.transpose(x, (1,2,0))

    if ndim == 2:
        x = np.expand_dims(x, axis=-1)
    
    if mode=='auto':
        mode = infer_mode(x)
    
    vis_func = vis_func_dict.get(mode, None)
    
    if vis_func == None:
        raise ValueError("mode {} is not supported.".format(mode))
        
    return vis_func(x, **kwargs)
    

def infer_mode(x):
    shape = x.shape
    ndim = len(shape)
    if shape[-1] == 3:
        mode = 'image'
    if shape[-1] == 2:
        mode = 'flow'
    if shape[-1] == 1:
        if (x.min() >= 0) and (x.max() <= 1):
            mode = 'grayscale'
        if isinteger(np.unique(x)).all(): # If values are all integer
            mode = 'categorical_mask'
        else:
            mode = 'grayscale'
    return mode

