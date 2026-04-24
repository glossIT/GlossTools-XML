import numpy as np
from rtree import index
import tqdm

from coordinate_manipulation import get_rectangle_area, rectangle_transform, shrink_rectangle
from glossit_connect_glosses import Word
from glossit_dataclasses import GlossLine
from xml_extraction import METSPage, polygon_to_rectangle, METSBook

from .logger import LoggerSingleton


class SpatialDatabase:
    """
    Class SpatialDatabase acts as a fast lookup table which coordinate points
    belong to which object on the manuscript page.

    Methods:
        construct_page_by_index (METSPage, int):
        get_object_by_coordinate (int, int, int): Returns the object on the page which contains the coordinate point.

    Private Attributes:
        _book (METSBook): The METSBook whose objects on each page should be indexed.
        _gloss_index (list[index.Index]): Stores the lookup table for glosses/references on each METSBook page.
        _word_index (list[index.Index]): Stores the lookup table for main text words on each METSBook page.
        _objects_per_page (list[dict[str, Word | GlossLine]]): Contains the link between object identifiers
                                                               and the objects on each METSBook page.

    """
    def __init__(self, book: METSBook, tqdm_progress: tqdm.tqdm = None):
        """
        Initialize the SpatialDatabase class.

        :param book: The METSBook whose objects on each page should be indexed.
        :param tqdm_progress: A tqdm progress bar for tracking METSBook construction process.
        """
        self._book = book
        number_of_pages = self._book.number_of_pages

        self._gloss_index = [None] * number_of_pages
        self._word_index = [None] * number_of_pages
        self._objects_per_page = [None] * number_of_pages

        if tqdm_progress is not None:
            tqdm_progress.iterable = range(number_of_pages)
            tqdm_progress.total = number_of_pages
            tqdm_progress.reset()
        else:
            tqdm_progress = tqdm.tqdm(range(number_of_pages), disable=True)

        for current_page in tqdm_progress:
            self.construct_page_by_index(self._book[current_page], current_page)

    def construct_page_by_index(self, page: METSPage, page_index: int):
        """
        Given a METSPage and a page_index, updates the spatial database at position page_index with the
        spatial contents of the page.
        :param page: METSPage to use for updating the spatial database.
        :param page_index: Index of the spatial database that is updated.
        """
        object_dictionary = {}

        current_gloss_index = index.Index()
        object_idx = 0
        for gloss_line in page.get_gloss_lines():
            rectangle = shrink_rectangle(polygon_to_rectangle(gloss_line.coordinates.exterior.coords))
            if rectangle is not None:
                coordinates = rectangle_transform(rectangle)
                current_gloss_index.insert(
                    id=object_idx,
                    coordinates=coordinates
                )
                object_dictionary[object_idx] = gloss_line
                object_idx += 1
            else:
                LoggerSingleton().logger.log_warning(f"Could not get rectangle of {gloss_line}.")

        current_word_index = index.Index()
        for line in page.get_main_text_lines():
            for word_idx, word_bounding_box in enumerate(line.word_bounding_boxes):
                rectangle = shrink_rectangle(word_bounding_box)
                if rectangle is not None:
                    coordinates = rectangle_transform(
                        rectangle
                    )
                    if not np.inf in coordinates and not np.nan in coordinates:
                        current_word_index.insert(
                            id=object_idx,
                            coordinates=coordinates
                        )
                        object_dictionary[object_idx] = Word(line, word_idx)
                    object_idx += 1
                else:
                    LoggerSingleton().logger.log_warning(f"Could not get rectangle of word {word_idx} in {line}.")

        self._gloss_index[page_index] = current_gloss_index
        self._word_index[page_index] = current_word_index
        self._objects_per_page[page_index] = object_dictionary

    def get_object_by_coordinate(self, page_index: int, x: int, y: int) -> GlossLine | Word | None:
        """
        Given some coordinates, returns an object whose bounding box contains the coordinate.
        First, glosses and reference signs are checked, then main text words.

        :param page_index: METSPage on which the objects to be checked are.
        :param x: X coordinate.
        :param y: Y coordinate.
        :return: Object whose bounding box contains the coordinate, or None if there is none.
        """
        def get_smallest_object(idx_list: list[index.Index]) -> GlossLine | Word | None:
            """
            Retrieve the smallest object (with respect to its bounding box) that contains the coordinate (x, y).

            :param idx_list: Spatial database index list.
            :return: The smallest object that contains the coordinate, or None if there is none.
            """
            minimal_object = None
            minimal_area = np.inf
            for intersection_id in idx_list[page_index].intersection((x, y, x, y)):
                object = self._objects_per_page[page_index][intersection_id]
                object_area = get_rectangle_area(object.get_bounding_box())

                if object_area < minimal_area:
                    minimal_area = object_area
                    minimal_object = object
            return minimal_object

        smallest_gloss = get_smallest_object(self._gloss_index)
        return smallest_gloss if smallest_gloss is not None else get_smallest_object(self._word_index)

