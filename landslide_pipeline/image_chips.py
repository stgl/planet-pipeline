def define(**kwargs):

    if kwargs.get('chips') is not None:
        return kwargs

    import os, ogr, subprocess

    output = kwargs['OUTPUT']
    map_name = kwargs['LANDSLIDE_MAP']['name']
    map_area_field = kwargs['LANDSLIDE_MAP']['area_field']
    min_area = kwargs['LANDSLIDE_MAP']["minimum_area"]
    reprojected_map = os.path.join(map_name, map_name + '_reproj.shp')

    subprocess.call(['ogr2ogr', '-s_srs', os.path.join(map_name, map_name + '.prj'), '-t_srs', 'EPSG:' +
                     str(output['output_projection']), reprojected_map, os.path.join(map_name, map_name + '.shp')])

    if not os.path.isdir(os.path.join(output['output_path'],'image_chips')):
        os.mkdir(os.path.join(output['output_path'],'image_chips'))

    chips = []

    ds = ogr.Open(reprojected_map, 1)
    lyr = ds.GetLayer(0)
    lyr.ResetReading()
    ft = lyr.GetNextFeature()

    feature_count = 0

    while ft is not None:
        if ft.GetField(map_area_field) >= min_area:

            geom = ft.GetGeometryRef()
            extent = geom.GetEnvelope()

            left = min([extent[0], extent[1]])
            right = max([extent[0], extent[1]])
            top = max([extent[2], extent[3]])
            bottom = min([extent[2], extent[3]])

            coordinates = {'xmin': left,
                           'xmax': right,
                           'ymin': bottom,
                           'ymax': top}

            chip_name = 'chip_' + str(feature_count)
            import os
            chips += [{'name': chip_name,
                       'coordinates': coordinates}]
            feature_count += 1
        ft = lyr.GetNextFeature()

    kwargs['chips'] = chips
    return kwargs

def refine(**kwargs):

    import pickle, os
    pickle_outfile = os.path.join(kwargs['OUTPUT']['output_path'], kwargs['OUTPUT']['output_path'] + '.p')
    chip_number = kwargs.get('chip_number', -1)
    image_name = kwargs['cloudless_scenes'][0]['filename']
    for (number, chip) in zip(range(len(kwargs['chips'])), kwargs['chips']):
        if number > chip_number:
            kwargs['chips'][number] = image_selector(image_name, chip)
            chip_number = number
            kwargs['chip_number'] = chip_number
            pickle.dump(kwargs, open(pickle_outfile, 'wb'))
    trim_chips = []
    for chip in kwargs['chips']:
        if chip is not None:
            trim_chips += [chip]
    kwargs['chips'] = trim_chips
    pickle.dump(kwargs, open(pickle_outfile, 'wb'))
    return kwargs

def create(**kwargs):

    if kwargs.get('chips_created') is not None:
        return kwargs

    import subprocess
    cloudless_scenes = kwargs['cloudless_scenes']
    output = kwargs['OUTPUT']
    for chip in kwargs['chips']:
        coordinates = chip['coordinates']
        name = chip['name']

        raster_count = 0
        left = coordinates['xmin']
        right = coordinates['xmax']
        top = coordinates['ymax']
        bottom = coordinates['ymin']

        for cloudless_scene in cloudless_scenes:

            chip_name = name + '_' + str(raster_count)
            import os
            subprocess.call(['gdalwarp', cloudless_scene['filename'], os.path.join(output['output_path'], 'image_chips', chip_name + '.TIF'), '-te',
                             str(left), str(bottom), str(right), str(top)])
            raster_count += 1

    kwargs['chips_create'] = True
    return kwargs

def convert(**kwargs):
    
    import os, subprocess, glob
    
    chips = glob.glob(os.path.join('image_chips', '*.TIF'))
    
    for chip in chips:
        chip_output = chip.replace('.TIF','.png')
        subprocess.call(['convert', chip, chip_output])
        os.remove(chip)

    return kwargs


def resample(*args, **kwargs):

    from landslide_pipeline.utils import resample_image
    import glob, os
    from PIL import Image

    max_chip_dimension = kwargs['MAX_CHIP_DIMENSION']
    chips = glob.glob(os.path.join('image_chips','*.png'))

    for chip in chips:
        image = Image.open(chip)
        image = resample_image(image, max_dim_size=max_chip_dimension)
        image.save(chip)

    return kwargs

def image_selector(image_name, chip):

    def create_image_for_viewer(image_name, chip):
        import subprocess, os
        try:
            os.remove('.tmp_display_image.tif')
        except:
            pass

        left = chip['coordinates']['xmin']
        right = chip['coordinates']['xmax']
        top = chip['coordinates']['ymax']
        bottom = chip['coordinates']['ymin']

        width = right - left
        height = top - bottom

        left -= width
        right += width
        top += height
        bottom -= height

        subprocess.call(['gdalwarp', image_name,
                         '.tmp_display_image.tif', '-te',
                         str(left), str(bottom), str(right), str(top)])

        import imageio

        im = imageio.imread('.tmp_display_image.tif')
        extent = (left, right, bottom, top)

        return im, extent

    import numpy as np
    import matplotlib.pyplot as plt
    plt.ion()

    class DraggableResizeableRectangle:
        """
        Draggable and resizeable rectangle with the animation blit techniques.
        Based on example code at
    http://matplotlib.sourceforge.net/users/event_handling.html
        If *allow_resize* is *True* the recatngle can be resized by dragging its
        lines. *border_tol* specifies how close the pointer has to be to a line for
        the drag to be considered a resize operation. Dragging is still possible by
        clicking the interior of the rectangle. *fixed_aspect_ratio* determines if
        the recatngle keeps its aspect ratio during resize operations.
        """
        lock = None  # only one can be animated at a time

        def __init__(self, rect, border_tol=.15, allow_resize=True,
                     fixed_aspect_ratio=True):
            self.rect = rect
            self.border_tol = border_tol
            self.allow_resize = allow_resize
            self.fixed_aspect_ratio = fixed_aspect_ratio
            self.press = None
            self.background = None

        def connect(self):
            'connect to all the events we need'
            self.cidpress = self.rect.figure.canvas.mpl_connect(
                'button_press_event', self.on_press)
            self.cidrelease = self.rect.figure.canvas.mpl_connect(
                'button_release_event', self.on_release)
            self.cidmotion = self.rect.figure.canvas.mpl_connect(
                'motion_notify_event', self.on_motion)

        def on_press(self, event):
            'on button press we will see if the mouse is over us and store some data'
            if event.inaxes != self.rect.axes: return
            if DraggableResizeableRectangle.lock is not None: return
            contains, attrd = self.rect.contains(event)
            if not contains: return
            # print 'event contains', self.rect.xy
            x0, y0 = self.rect.xy
            w0, h0 = self.rect.get_width(), self.rect.get_height()
            aspect_ratio = np.true_divide(w0, h0)
            self.press = x0, y0, w0, h0, aspect_ratio, event.xdata, event.ydata
            DraggableResizeableRectangle.lock = self

            # draw everything but the selected rectangle and store the pixel buffer
            canvas = self.rect.figure.canvas
            axes = self.rect.axes
            self.rect.set_animated(True)
            canvas.draw()
            self.background = canvas.copy_from_bbox(self.rect.axes.bbox)

            # now redraw just the rectangle
            axes.draw_artist(self.rect)

            # and blit just the redrawn area
            canvas.blit(axes.bbox)

        def on_motion(self, event):
            'on motion we will move the rect if the mouse is over us'
            if DraggableResizeableRectangle.lock is not self:
                return
            if event.inaxes != self.rect.axes: return
            x0, y0, w0, h0, aspect_ratio, xpress, ypress = self.press
            self.dx = event.xdata - xpress
            self.dy = event.ydata - ypress
            # self.rect.set_x(x0+dx)
            # self.rect.set_y(y0+dy)

            self.update_rect()

            canvas = self.rect.figure.canvas
            axes = self.rect.axes
            # restore the background region
            canvas.restore_region(self.background)

            # redraw just the current rectangle
            axes.draw_artist(self.rect)

            # blit just the redrawn area
            canvas.blit(axes.bbox)

        def on_release(self, event):
            'on release we reset the press data'
            if DraggableResizeableRectangle.lock is not self:
                return

            self.press = None
            DraggableResizeableRectangle.lock = None

            # turn off the rect animation property and reset the background
            self.rect.set_animated(False)
            self.background = None

            # redraw the full figure
            self.rect.figure.canvas.draw()

        def disconnect(self):
            'disconnect all the stored connection ids'
            self.rect.figure.canvas.mpl_disconnect(self.cidpress)
            self.rect.figure.canvas.mpl_disconnect(self.cidrelease)
            self.rect.figure.canvas.mpl_disconnect(self.cidmotion)

        def update_rect(self):
            x0, y0, w0, h0, aspect_ratio, xpress, ypress = self.press
            dx, dy = self.dx, self.dy
            bt = self.border_tol
            fixed_ar = self.fixed_aspect_ratio
            if (not self.allow_resize or
                    (abs(x0 + np.true_divide(w0, 2) - xpress) < np.true_divide(w0, 2) - bt * w0 and
                     abs(y0 + np.true_divide(h0, 2) - ypress) < np.true_divide(h0, 2) - bt * h0)):
                self.rect.set_x(x0 + dx)
                self.rect.set_y(y0 + dy)
            elif abs(x0 - xpress) < bt * w0:
                self.rect.set_x(x0 + dx)
                self.rect.set_width(w0 - dx)
                if fixed_ar:
                    dy = np.true_divide(dx, aspect_ratio)
                    self.rect.set_y(y0 + dy)
                    self.rect.set_height(h0 - dy)
            elif abs(x0 + w0 - xpress) < bt * w0:
                self.rect.set_width(w0 + dx)
                if fixed_ar:
                    dy = np.true_divide(dx, aspect_ratio)
                    self.rect.set_height(h0 + dy)
            elif abs(y0 - ypress) < bt * h0:
                self.rect.set_y(y0 + dy)
                self.rect.set_height(h0 - dy)
                if fixed_ar:
                    dx = dy * aspect_ratio
                    self.rect.set_x(x0 + dx)
                    self.rect.set_width(w0 - dx)
            elif abs(y0 + h0 - ypress) < bt * h0:
                self.rect.set_height(h0 + dy)
                if fixed_ar:
                    dx = dy * aspect_ratio
                    self.rect.set_width(w0 + dx)

    from matplotlib.widgets import Button

    class ChipSelector(object):

        def __init__(self, image_name, chip, **kwargs):
            plt.ioff()
            self.chip = chip
            fig, ax = plt.subplots()
            im, extent = create_image_for_viewer(image_name, chip)
            plt.imshow(np.flipud(im), extent=extent)
            xy = (chip['coordinates']['xmin'], chip['coordinates']['ymin'])
            width = chip['coordinates']['xmax'] - chip['coordinates']['xmin']
            height = chip['coordinates']['ymax'] - chip['coordinates']['ymin']

            from matplotlib.patches import Rectangle
            self.__rect = Rectangle(xy, width, height, fill=False, color='r')
            ax.add_patch(self.__rect)
            drr = DraggableResizeableRectangle(self.__rect, fixed_aspect_ratio=False)
            drr.connect()

            plt.subplots_adjust(bottom=0.2)

            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)
            ax_reject = plt.axes([0.2, 0.05, 0.1, 0.075])
            ax_accept = plt.axes([0.75, 0.05, 0.1, 0.075])
            self._b_reject = Button(ax_reject, 'Reject')
            self._b_accept = Button(ax_accept, "Accept")
            self._b_reject.on_clicked(self.answer)
            self._b_accept.on_clicked(self.answer)
            plt.show()

        def answer(self, event):
            if event.inaxes.texts[0]._text == 'Accept':
                self.chip = {'name': self.chip['name'],
                             'coordinates': {'xmin': self.__rect.get_x(),
                                             'ymin': self.__rect.get_y(),
                                             'xmax': self.__rect.get_x()+self.__rect.get_width(),
                                             'ymax': self.__rect.get_y()+self.__rect.get_height()}
                             }
            else:
                self.chip = None
            plt.close()

    chip = ChipSelector(image_name, chip)
    return chip.chip







