import numpy as np


def polygon_to_rectangle(polygon: list) -> list:
    """
    This function takes a polygon and returns the minimal axis-aligned rectangle
    such that all polygon points are contained in it.

      _______        _________
     /   _  |_  ->  |        |
     |__/ |__|      |________|

    :param polygon: A list of points (w, h) defining a (closed) polygon.
    :return: The minimal rectangle containing all polygon points stored as a list of four points (w, h).
    """
    min_w = np.inf
    max_w = 0
    min_h = np.inf
    max_h = 0
    for point in polygon:
        w, h = point
        min_w = min(min_w, w)
        max_w = max(max_w, w)
        min_h = min(min_h, h)
        max_h = max(max_h, h)
    return [
        (min_w, max_h),
        (max_w, max_h),
        (max_w, min_h),
        (min_w, min_h)
    ]


def get_rectangle_area(rectangle: list[tuple[int, int]]) -> float:
    """
    Calculates and returns the area of the rectangle given in polygon format.
    :param rectangle: Rectangle.
    :return: The area of the rectangle.
    """
    min_w, max_h = rectangle[0]
    max_w, min_h = rectangle[2]
    return (max_w - min_w) * (max_h - min_h)


def divide_rectangle_into_equal_parts(rectangle: list, num_parts: int) -> list:
    """
    This function takes a rectangle, and splits it into num_parts rectangles of
    equal length horizontally. A list containing all num_parts resulting rectangles is returned.
     _________        _________
    |        |   ->  |  |  |  |
    |________|       |__|__|__|

    :param rectangle: A list of four coordinate points (w, h) defining a rectangle.
    :param num_parts: The number of parts the rectangle should be split into horizontally.
    :return: A list of rectangles (each of them consisting of four points (w, h)).
    """
    top_left, top_right, bottom_right, bottom_left = rectangle
    width = (top_right[0] - top_left[0])/num_parts

    list_of_subrectangles = []
    for idx in range(num_parts):
        list_of_subrectangles.append([
            (top_left[0] + idx * width, top_left[1]),
            (top_left[0] + (idx + 1) * width, top_right[1]),
            (bottom_right[0] + (idx + 1) * width, bottom_right[1]),
            (bottom_left[0] + idx * width, bottom_left[1])
        ])

    return list_of_subrectangles


def rectangle_xywh(rectangle: tuple[tuple[int, int]]) -> tuple[int, int, int, int]:
    """
    Brings the rectangle coordinates into the form (x, y, width, height).

    :param rectangle: The rectangle to be transformed.
    :return: The rectangle in (x, y, width, height) format.
    """
    x_min, x_max = np.min([point[0] for point in rectangle]), np.max([point[0] for point in rectangle])
    y_min, y_max = np.min([point[1] for point in rectangle]), np.max([point[1] for point in rectangle])
    return x_min, y_min, x_max-x_min, y_max-y_min


def rectangle_transform(rectangle: tuple[tuple[int, int]]) -> tuple[int, int, int, int]:
    """
    Brings the rectangle coordinates into the right form for RTree.

    :param rectangle: The rectangle to be transformed.
    :return: The rectangle in (x_min, y_min, x_max, y_max) format.
    """
    x_min, x_max = np.min([point[0] for point in rectangle]), np.max([point[0] for point in rectangle])
    y_min, y_max = np.min([point[1] for point in rectangle]), np.max([point[1] for point in rectangle])
    return x_min, y_min, x_max, y_max


def rectangle_untransform(x_min: int, y_min: int, x_max: int, y_max: int) -> list[tuple[int, int]]:
    """
    Given a rectangle in (x_min, y_min, x_max, y_max) format, returns the rectangle as four (x, y) points.

    :param x_min: x_min of the rectangle.
    :param y_min: y_min of the rectangle.
    :param x_max: x_max of the rectangle.
    :param y_max: y_max of the rectangle.
    :return:
    """
    return [
        (x_min, y_min),
        (x_max, y_min),
        (x_max, y_max),
        (x_min, y_max),
    ]


def shrink_rectangle(rectangle: tuple[tuple[int, int]], shrink_factor: float = 0.6):
    """
    Shrinks the lengths by the given factor, keeping the center point intact.

    :param rectangle: Rectangle to shrink.
    :param shrink_factor: Shrink factor between 0 and 1.
    :return: The shrunk rectangle (or None in case a valid rectangle could not be constructed)
    """
    x_min, y_min, x_max, y_max = rectangle_transform(rectangle)
    x_center = (x_max + x_min) / 2
    y_center = (y_max + y_min) / 2
    x_length = (x_max - x_min) / 2
    y_length = (y_max - y_min) / 2

    try:
        return rectangle_untransform(
            x_min=int(x_center - shrink_factor * x_length),
            y_min=int(y_center - shrink_factor * y_length),
            x_max=int(x_center + shrink_factor * x_length),
            y_max=int(y_center + shrink_factor * y_length)
        )
    except Exception:
        return None


def get_optimal_fontsize(rectangle: tuple[tuple[int, int]], text: str):
    """
    Determines the optimal font size for the given rectangle and text.
    :param rectangle: Rectangle in which the text should be placed.
    :param text: Text to be placed.
    :return: Optimal fontsize.
    """

    x_min, y_min, x_max, y_max = rectangle_transform(rectangle)
    width = x_max - x_min
    height = y_max - y_min

    aspect_ratio = min(width/height, height/width)

    fontsize = width/len(text) * aspect_ratio**(1/5) if len(text) > 0 else 20

    return fontsize


def get_optimal_position(rectangle: tuple[tuple[int, int]], fontsize: int) -> tuple[float, float]:
    """
    Determines the optimal position for the text to be placed in the given rectangle.
    :param rectangle: Rectangle in which the text should be placed.
    :param fontsize: Font size of the text.
    :return: Optimal position (x, y).
    """

    x_min, y_min, x_max, y_max = rectangle_transform(rectangle)
    width = x_max - x_min
    height = y_max - y_min

    optimal_height = (y_min + height/2 - y_max)/(max(fontsize/20, 1)) + y_max

    return x_min + width//2, optimal_height
