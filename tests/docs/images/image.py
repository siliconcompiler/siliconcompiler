import os
import filecmp


def compare(module, image):
    test_img = os.path.join('..', '_images', image)
    assert os.path.isfile(test_img)
    base_img = os.path.join(os.path.dirname(module.__file__), test_img)
    assert filecmp.cmp(test_img, base_img)
