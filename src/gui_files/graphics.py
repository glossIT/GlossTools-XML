import numpy as np
from PySide6.QtGui import QColor

from coordinate_manipulation import get_optimal_fontsize, get_optimal_position, shrink_rectangle
from glossit_connect_glosses import ConnectedPair, Word
from glossit_dataclasses import GlossLine, LineType
from xml_extraction import METSPage, polygon_to_rectangle

from .gloss_connector_manager import ObservableGlossOnPageConnector
from .graphics_item import ArrowItem, GraphicsItem, PolygonItem, TextItem
from .logger import LoggerSingleton


def construct_word_and_gloss_graphics_from_mets_page(page: METSPage, display_text: bool) -> list[GraphicsItem]:
    """
    Given a METSPage, this function constructs a list of GraphicsItem for drawing the contents and bounding boxes
    for each gloss line and main text word.

    :param page: METSPage from which the graphics should be constructed.
    :param display_text: If True, the words are rendered inside the bounding boxes.
    :return: List of GraphicsItem objects.
    """
    def get_gloss_color(gloss: GlossLine):
        if gloss.type == LineType.REFERENCE_SIGN:
            return QColor(0, 0, 128, 255)
        else:
            return QColor(0, 128, 0, 255)

    def get_gloss_text_color(gloss: GlossLine):
        if gloss.type == LineType.REFERENCE_SIGN:
            return QColor(20, 20, 255, 128)
        else:
            return QColor(20, 255, 20, 128)

    objects = []

    # Gloss lines
    for gloss_line in page.get_gloss_lines():
        gloss_coordinate = shrink_rectangle(polygon_to_rectangle(gloss_line.coordinates.exterior.coords))
        if gloss_coordinate is not None:
            polygon_item = PolygonItem(gloss_coordinate, get_gloss_color(gloss_line), filled=False)
            objects.append(polygon_item)

            if display_text:
                fontsize = get_optimal_fontsize(gloss_coordinate, gloss_line.text)
                text_item = TextItem(
                    text=gloss_line.text,
                    position=get_optimal_position(gloss_coordinate, fontsize),
                    color=get_gloss_text_color(gloss_line),
                    fontsize=fontsize
                )
                objects.append(text_item)
        else:
            LoggerSingleton().logger.log_warning(f"Could not get rectangle of {gloss_line}.")

    red = QColor(128, 0, 0, 255)
    white = QColor(255, 255, 255, 128)

    # Individual word BBs and word annotations
    for line in page.get_main_text_lines():
        for word_text, word_coordinate in zip(line.words, line.word_bounding_boxes):
            rectangle = shrink_rectangle(word_coordinate)
            if rectangle is not None:
                polygon_item = PolygonItem(rectangle, red, filled=False)
                objects.append(polygon_item)

                if display_text:
                    fontsize = get_optimal_fontsize(rectangle, word_text)
                    word_item = TextItem(
                        text=word_text,
                        position=get_optimal_position(rectangle, fontsize),
                        color=white,
                        fontsize=fontsize
                    )
                    objects.append(word_item)
            else:
                LoggerSingleton().logger.log_warning(f"Could not get rectangle of word '{word_text}' in {line}.")

    return objects


def construct_connection_graphics_from_connector(connector: ObservableGlossOnPageConnector) -> list[GraphicsItem]:
    """
    Given a list of connection cycles on a METSPage, this function constructs a list of GraphicsItem for drawing
    the individual connections in the cycles.

    :param connector: ObservableGlossOnPageConnector object from which the graphics should be constructed.
    :return: List of GraphicsItem objects.
    """
    def get_gloss_color(gloss: GlossLine):
        if gloss.type == LineType.REFERENCE_SIGN:
            return QColor(0, 0, 255, 48)
        else:
            return QColor(0, 255, 0, 48)

    page_chains = connector.connection_chains
    objects = []

    for chain in page_chains:
        for connection in chain:
            red = QColor(255, 0, 0, 48)
            # starting point from a connection must always be a gloss line
            assert (isinstance(connection.start, GlossLine))
            # end point of a connection can either be a word or a gloss line
            assert (isinstance(connection.end, (Word, GlossLine)))
            # circular relations are not allowed
            # assert (isinstance(connection.end, (Word, GlossLine)))

            # draw start gloss
            color = get_gloss_color(connection.start)
            rectangle = shrink_rectangle(polygon_to_rectangle(connection.start.coordinates.exterior.coords))
            if rectangle is not None:
                item_bounding_box = PolygonItem(
                    rectangle,
                    color
                )
                objects.append(item_bounding_box)
            else:
                LoggerSingleton().logger.log_warning(f"Could not get rectangle of {connection.start}.")


            start_center = np.mean(connection.start.baseline, axis=0)

            # draw end gloss/word
            if isinstance(connection.end, Word):
                rectangle = shrink_rectangle(connection.end.bounding_box)
                if rectangle is not None:
                    item_bounding_box = PolygonItem(rectangle, red)
                    objects.append(item_bounding_box)
                end_center = np.mean(connection.end.bounding_box, axis=0)
            else:  # connection.end must be gloss in this case
                color = get_gloss_color(connection.end)
                rectangle = shrink_rectangle(polygon_to_rectangle(connection.end.coordinates.exterior.coords))
                if rectangle is not None:
                    item_bounding_box = PolygonItem(
                        rectangle,
                        color
                    )
                    objects.append(item_bounding_box)

                end_center = np.mean(connection.end.baseline, axis=0)

            arrow_item = ArrowItem(start_center, end_center, QColor(0, 0, 0))
            objects.append(arrow_item)

    return objects


def construct_currently_selected_object_graphic(object: GlossLine | Word) -> GraphicsItem:
    def get_object_color(object: GlossLine | Word):
        if isinstance(object, GlossLine):
            if object.type == LineType.REFERENCE_SIGN:
                return QColor(0, 0, 80, 80)
            return QColor(0, 80, 0, 80)
        else:  # Word
            return QColor(80, 0, 0, 80)

    if isinstance(object, GlossLine):
        coords = shrink_rectangle(polygon_to_rectangle(object.coordinates.exterior.coords))
    else:
        coords = shrink_rectangle(object.line.word_bounding_boxes[object.word_idx])

    if coords is not None:
        color = get_object_color(object)
        polygon_item = PolygonItem(coords, color, filled=True)
        return polygon_item
    else:
        LoggerSingleton().logger.log_warning(f"Could not get rectangle of {object}.")

