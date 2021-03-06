# -*- coding: utf-8 -*-
"""
Created on Tue Jun  9 11:51:28 2015

@author: ajaver
"""

import time
import datetime
import numpy as np

def _tictoc():
    tic = time.time()

    def _toc():
        print('Elapse time %f' % (time.time() - tic))
    return _toc


class TimeCounter:

    def __init__(self, task_str='', tot_frames=None):
        self.initial_time = time.time()
        self.last_frame = 0
        self.task_str = task_str
        self.fps_time = time.time()
        self.tot_frames = tot_frames

    def get_str(self, frame_number):
        # calculate the progress and put it in a string
        time_str = str(
            datetime.timedelta(
                seconds=round(
                    time.time() -
                    self.initial_time)))
        
        try:
            fps = (frame_number - self.last_frame + 1) / \
                (time.time() - self.fps_time)
        except ZeroDivisionError:
            fps = np.nan
            
        progress_str = '%s Total time = %s, fps = %2.1f; Frame %i'\
            % (self.task_str, time_str, fps, frame_number)
        self.fps_time = time.time()
        self.last_frame = frame_number
        if self.tot_frames is not None:
            progress_str += ' of %i' % self.tot_frames

        return progress_str

    def get_time_str(self):
        return str(
            datetime.timedelta(
                seconds=round(
                    time.time() -
                    self.initial_time)))
