def select_single_training_image(training_image_name):

    from imageio import imread
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button

    class ImageSelector(object):

        def __init__(self, image, **kwargs):
            plt.ioff()
            self.value = "Undefined"
            self.__image = image
            fig, ax = plt.subplots()
            plt.subplots_adjust(bottom=0.2)
            plt.imshow(image)
            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)
            ax_no = plt.axes([0.2, 0.05, 0.1, 0.075])
            ax_maybe = plt.axes([0.45, 0.05, 0.1, 0.075])
            ax_yes = plt.axes([0.75, 0.05, 0.1, 0.075])
            self._b_no = Button(ax_no, 'No')
            self._b_maybe = Button(ax_maybe, "Maybe")
            self._b_yes = Button(ax_yes, "Yes")
            self._b_no.on_clicked(self.answer)
            self._b_maybe.on_clicked(self.answer)
            self._b_yes.on_clicked(self.answer)
            plt.show()

        def answer(self, event):
            self.value = event.inaxes.texts[0]._text
            plt.close()

    imageobj = imread(training_image_name)
    selector = ImageSelector(imageobj)
    return selector.value

#TODO: Make cropper for visible classified image to extract Yes/No/Maybe images.
#    Return these cropped filenames in kwargs['identified_images']

def human_training(*args, **kwargs):
    responses = [] 
    for image in kwargs['identified_images']
        responses += [select_single_training_image(image)]
    kwargs['human_responses'] = responses
    return kwargs

