import numpy as np

from coordinate_manipulation import get_optimal_fontsize, get_optimal_position, get_display_rectangle
from glossit_connect_glosses import ConnectedPair, Word
from glossit_dataclasses import GlossLine, LineType
from xml_extraction import METSPage, polygon_to_rectangle

from .gloss_connector_manager import ObservableGlossOnPageConnector
from .graphics_item import ArrowItem, GraphicsItem, PolygonItem, TextItem
from .logger import LoggerSingleton
from .settings import SettingsKey, settings_get


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
            return settings_get(SettingsKey.REFERENCE_SIGN_FILL)
        else:
            return settings_get(SettingsKey.GLOSS_FILL)

    def get_gloss_text_color(gloss: GlossLine):
        if gloss.type == LineType.REFERENCE_SIGN:
            col = settings_get(SettingsKey.REFERENCE_SIGN_TEXT)
            col.setAlpha(int(settings_get(SettingsKey.TEXT_TRANSPARENCY)))
            return col
        else:
            col = settings_get(SettingsKey.GLOSS_TEXT)
            col.setAlpha(int(settings_get(SettingsKey.TEXT_TRANSPARENCY)))
            return col

    objects = []

    # Gloss lines
    for gloss_line in page.get_gloss_lines():
        gloss_coordinate = get_display_rectangle(polygon_to_rectangle(gloss_line.coordinates.exterior.coords))
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

    # Individual word BBs and word annotations
    for line in page.get_main_text_lines():
        for word_text, word_coordinate in zip(line.words, line.word_bounding_boxes):
            rectangle = get_display_rectangle(word_coordinate)
            if rectangle is not None:
                polygon_item = PolygonItem(rectangle, settings_get(SettingsKey.MAIN_WORD_FILL), filled=False)
                objects.append(polygon_item)

                if display_text:
                    fontsize = get_optimal_fontsize(rectangle, word_text)
                    color = settings_get(SettingsKey.MAIN_WORD_TEXT)
                    color.setAlpha(int(settings_get(SettingsKey.TEXT_TRANSPARENCY)))
                    word_item = TextItem(
                        text=word_text,
                        position=get_optimal_position(rectangle, fontsize),
                        color=color,
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
            col = settings_get(SettingsKey.REFERENCE_SIGN_FILL)
            col.setAlpha(int(settings_get(SettingsKey.FILL_TRANSPARENCY)))
            return col
        else:
            col = settings_get(SettingsKey.GLOSS_FILL)
            col.setAlpha(int(settings_get(SettingsKey.FILL_TRANSPARENCY)))
            return col

    page_chains = connector.connection_chains
    objects = []

    isolated_glosses = connector.isolated_glosses

    # draw all isolated gloss lines
    for isolated_gloss in isolated_glosses:
        color = get_gloss_color(isolated_gloss)

        rectangle = get_display_rectangle(polygon_to_rectangle(isolated_gloss.coordinates.exterior.coords))
        if rectangle is not None:
            item_bounding_box = PolygonItem(
                rectangle,
                color
            )
            objects.append(item_bounding_box)
        else:
            LoggerSingleton().logger.log_warning(f"Could not get rectangle of {isolated_gloss}.")

    for chain in page_chains:
        if True in [connection.is_visible for connection in chain]:  # draw chain if at least one connection is visible
            for connection in chain:
                # starting point from a connection must always be a gloss line
                assert (isinstance(connection.start, GlossLine))
                # end point of a connection can either be a word or a gloss line
                assert (isinstance(connection.end, (Word, GlossLine)))
                # circular relations are not allowed
                # assert (isinstance(connection.end, (Word, GlossLine)))

                # draw start gloss
                color = get_gloss_color(connection.start)
                rectangle = get_display_rectangle(polygon_to_rectangle(connection.start.coordinates.exterior.coords))
                if rectangle is not None:
                    item_bounding_box = PolygonItem(
                        rectangle,
                        color
                    )
                    objects.append(item_bounding_box)
                else:
                    LoggerSingleton().logger.log_warning(f"Could not get rectangle of {connection.start}.")

                start_center = np.mean(rectangle, axis=0)

                # draw end gloss/word
                if isinstance(connection.end, Word):
                    rectangle = get_display_rectangle(connection.end.bounding_box)
                    if rectangle is not None:
                        color = settings_get(SettingsKey.MAIN_WORD_FILL)
                        color.setAlpha(int(settings_get(SettingsKey.FILL_TRANSPARENCY)))

                        item_bounding_box = PolygonItem(rectangle, color)
                        objects.append(item_bounding_box)
                        objects.append(item_bounding_box)
                    end_center = np.mean(connection.end.bounding_box, axis=0)
                else:  # connection.end must be gloss in this case
                    color = get_gloss_color(connection.end)
                    rectangle = get_display_rectangle(polygon_to_rectangle(connection.end.coordinates.exterior.coords))
                    if rectangle is not None:
                        item_bounding_box = PolygonItem(
                            rectangle,
                            color
                        )
                        objects.append(item_bounding_box)

                    end_center = np.mean(rectangle, axis=0)

                arrow_item = ArrowItem(start_center, end_center, settings_get(SettingsKey.ARROW_FILL))
                objects.append(arrow_item)

    return objects


def construct_currently_selected_object_graphic(object: GlossLine | Word) -> GraphicsItem:
    def get_object_color(object: GlossLine | Word):
        if isinstance(object, GlossLine):
            if object.type == LineType.REFERENCE_SIGN:
                return settings_get(SettingsKey.REFERENCE_SIGN_FILL)
            return settings_get(SettingsKey.GLOSS_FILL)
        else:  # Word
            return settings_get(SettingsKey.MAIN_WORD_FILL)

    if isinstance(object, GlossLine):
        coords = get_display_rectangle(polygon_to_rectangle(object.coordinates.exterior.coords))
    else:
        coords = get_display_rectangle(object.line.word_bounding_boxes[object.word_idx])

    if coords is not None:
        color = get_object_color(object)
        color.setAlpha(int(settings_get(SettingsKey.SELECTION_TRANSPARENCY)))
        polygon_item = PolygonItem(coords, color, filled=True)
        return polygon_item
    else:
        LoggerSingleton().logger.log_warning(f"Could not get rectangle of {object}.")

