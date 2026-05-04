import threading
import tqdm
from PIL import Image, ImageEnhance
from PySide6.QtCore import Signal, QObject, QTimer, Slot
from pyqttoast import ToastPreset

from xml_extraction import METSBook
from glossit_connect_glosses import ConnectedPair, Word
from glossit_dataclasses import GlossLine

from .gloss_connector_manager import GlossConnectionHandler
from .graphics import construct_connection_graphics_from_connector, construct_word_and_gloss_graphics_from_mets_page
from .graphics_item import GraphicsItem
from .logger import LoggerSingleton
from .cyclic_access import CyclicCounter, CyclicList
from .undo_redo import UndoRedoList
from .spatial_database import SpatialDatabase


class _ProgramState(QObject):
    """
    Class _ProgramState stores the program's current state, meaning everything that affects
    what should be displayed in the widgets, the results of user interactions, etc.

    Properties:
        data_changed (Signal): Signal that is emitted when data has been changed in the program state.
        show_toast (Signal[str, str, ToastPreset]): Signal that is emitted when a toast should be displayed.
                                                    The arguments are title, message, and ToastPreset.
        _request_debounce (Signal): Signal that is emitted when the debounce is requested.

        has_unsaved_changes (bool): If True, the program state has unsaved changes.
        icon (QIcon | None): Stores the application icon.
        path_to_xml (str | None): Stores the path to the METS file.
        path_to_tei (str | None): Stores the path to the TEI file.
        path_to_model (str | None): Stores the path to the Kraken OCR MLModel.
        save_file_path (str | None): Stores the path to which file the user has saved the project.
        mets_book (METSBook | None): The METSBook on which the GUI operates.
        gloss_connection_handler (list[GlossOnPageConnector] | None): The gloss/reference/word connection on the
                                                                  current METSPage.
        draw_image (Image.Image | None): The image of the manuscript that is to be drawn in the view.
        draw_word_gloss_objects (list[GraphicsItem] | None): List of words and glosses on the current METSPage in
                                                             drawable form.
        draw_connection_objects (list[GraphicsItem] | None): List of gloss connections on the current METSPage in
                                                             drawable form.
        spatial_database (SpatialDatabase): Database for quick lookup of objects in the scene based on their
                                            coordinates. Used for selecting the right object when clicking on
                                            it in the ImageGraphicsView widget.
        current_page_index (int | None): Read-only. The index of the currently selected page.
        number_of_pages (int | None): Read-only. Returns the currently available number of pages.
        page_counter_text (str): Read-only. The text representation of the currently selected page index, e.g., '1 / 9'.
        unconnected_gloss_lines (CyclicList): Read-only. Contains all gloss line ids that are not connected.

    Methods:
        reset: Resets all member variables to None and frees the memory.
        to_dict (tqdm.tqdm): Returns a dictionary of the most important features for saving.
        from_dict: Resets the _ProgramState class with the values loaded from a save file dictionary.
        go_to_next_page: Sets the page counter object to the next page. Call from separate thread!
        go_to_previous_page: Sets the page counter object to the previous page. Call from separate thread!
        go_to_page (int): Sets the page counter object to the indicated page index. Call from separate thread!
        update_display_text (bool): Indicates whether the text of gloss/word objects should be drawn and redraws
                                    the page if needed. Call from separate thread!
        construct_current_page_graphics: Updates the graphics for the currently selected page for display.
                                         Call from separate thread!
        page_index_is_valid (int): Check if the given page index is valid.
        has_undo_actions: Return True if there are actions that can be undone.
        has_redo_actions: Return True if there are actions that can be redone.
        undo: If possible, undo the last action.
        redo: If possible, redo the last action.
        select_or_connect_on_coordinate (int, int): Given a set of x and y coordinates, selects the object that is
                                                    found on this place, and if another object was selected previously,
                                                    attempts to connect them.
                                                    Call from separate thread!
        remove_connection (int): Deletes the connection that has the passed index. Call from separate thread!
        clear_metsbook_cache: Cleans the METSBook cache. Must be invoked whenever the METSBook is changed!

    Private Attributes:
        _debounce_timer (QTimer): Timer for debouncing change signals, i.e., the signal is only emitted after
                                  a certain time period to prevent too frequent GUI updates.
        _pending_changes (bool): Is set to True if a signal must be emitted after the debounce timer has timed out.
        _page_counter (PageCounter | None): Stores the current METSBook page (METSPage) number.
        _mets_book_cache (list[dict] | None): Caches the METSBook serialization for faster saving times.
        _display_text (bool): If True, the annotation text inside each box is drawn.

    Private Methods:
        _start_debounce_timer: Starts the debounce timer (on timeout, the signal data_changed may be emitted).
        _emit_data_changed: If pending changes are present, the data_changed signal is emitted with a summary of
                            changes.
        _schedule_emit (str): Adds a program state change (with change name provided) to the list of _pending_changes.
        _update_unconnected_gloss_lines: Updates the unconnected gloss lines for this page.
    """
    data_changed = Signal(str)
    show_toast = Signal(str, str, ToastPreset)
    _request_debounce = Signal()

    def __init__(self):
        """
        Initializes an instance of the _ProgramState class.
        """
        super().__init__()

        self._request_debounce.connect(self._start_debounce_timer)

        self.icon = None

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_data_changed)
        self._pending_changes = set()

        self._mets_book_cache: dict | None = None

        self.path_to_mets: str | None = None
        self.path_to_tei: str | None = None
        self.path_to_model: str | None = None
        self.save_file_path: str | None = None

        self._display_text: bool = True

        self._page_counter: CyclicCounter | None = None
        self._mets_book: METSBook | None = None

        self._currently_selected_object: GlossLine | Word | None = None
        self._draw_image: Image.Image | None = None
        self._draw_word_gloss_objects: list[GraphicsItem] | None = None
        self._draw_connection_objects: list[GraphicsItem] | None = None
        self._spatial_database: SpatialDatabase | None = None

        self.unconnected_gloss_lines: CyclicList | None = None
        self._undo_redo_list: UndoRedoList = UndoRedoList()
        self._gloss_connection_handler = None

        def connector_callback():
            self._update_unconnected_gloss_lines()

        self._gloss_connection_handler: GlossConnectionHandler = GlossConnectionHandler(
            callback=connector_callback
        )

    def __repr__(self):
        return (f"ProgramState(\n"
                f"   Path to METS: {self.path_to_mets}\n"
                f"   Path to TEI: {self.path_to_tei}\n"
                f"   Path to Model: {self.path_to_model}\n"
                f")"
                )

    def reset(self):
        """
        Resets all member variables to None and frees the memory.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.reset()")
        self.path_to_mets = None
        self.path_to_tei = None
        self.path_to_model = None

        # We keep the save file path
        # self.save_file_path = None

        del self._page_counter
        self._page_counter = None

        del self._mets_book
        self._mets_book = None

        self._gloss_connection_handler.reset()

        del self._currently_selected_object
        self._currently_selected_object = None

        del self._draw_image
        self._draw_image = None

        del self._draw_word_gloss_objects
        self._draw_word_gloss_objects = None

        del self._draw_connection_objects
        self._draw_connection_objects = None

        del self._spatial_database
        self._spatial_database = None

        self.clear_metsbook_cache()
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element([])

    def to_dict(self, tqdm_progress: tqdm.tqdm) -> dict:
        """
        Returns a dictionary of the most important features for saving.
        :param tqdm_progress: A tqdm progress bar for tracking METSBook construction process.
        :return: Dictionary of the most important _ProgramState features.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.to_dict(...)")
        if self._mets_book_cache is None:
            mets_book_dict = self.mets_book.to_dict(tqdm_progress=tqdm_progress)
            self._mets_book_cache = mets_book_dict
        else:
            mets_book_dict = self._mets_book_cache

        return {
            "mets_book": mets_book_dict,
            "page_counter": self._page_counter.to_dict(),
            "page_connections": self._gloss_connection_handler.to_dict(),
        }

    def from_dict(self, dictionary: dict, tqdm_progress: tqdm.tqdm = None):
        """
        Resets the _ProgramState class with the values loaded from a save file dictionary.
        :param tqdm_progress: A tqdm progress bar for tracking METSBook construction process.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.from_dict(...)")
        self.reset()

        self._mets_book = METSBook.from_dict(dictionary["mets_book"])
        self._page_counter = CyclicCounter.from_dict(dictionary["page_counter"])

        self._gloss_connection_handler.from_dict(
            dict_list=dictionary["page_connections"],
            mets_book=self._mets_book,
            tqdm_progress=tqdm_progress
        )

        self._mets_book_cache = dictionary["mets_book"]
        self._currently_selected_object = None
        self.unconnected_gloss_lines = CyclicList(
            self._gloss_connection_handler[self.current_page_index].get_unconnected_gloss_line_ids()
        )
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(self._gloss_connection_handler[self.current_page_index].connections)
        self.data_changed.emit("from_save_file")

    def go_to_next_page(self):
        """
        Sets the page counter object to the next page. Call from separate thread!
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.go_to_next_page()")
        self._page_counter.next_index()
        self.construct_current_page_graphics()
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(self._gloss_connection_handler[self.current_page_index].connections)
        self.data_changed.emit("go_to_next_page")

    def go_to_previous_page(self):
        """
        Sets the page counter object to the previous page. Call from separate thread!
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.go_to_previous_page()")
        self._page_counter.previous_index()
        self.construct_current_page_graphics()
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(self._gloss_connection_handler[self.current_page_index].connections)
        self.data_changed.emit("go_to_previous_page")

    def go_to_page(self, page_idx: int):
        """
        Sets the page counter object to the page of index page_idx. Call from separate thread!
        :param page_idx: Page index to which the page counter should be set.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.go_to_page(page_idx={page_idx})")
        self._page_counter.go_to_index(page_idx)
        self.construct_current_page_graphics()
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(self._gloss_connection_handler[self.current_page_index].connections)
        self.data_changed.emit("go_to_page")

    def update_display_text(self, value: bool):
        """
        Updates whether the text inside the word/gloss bounding boxes should be rendered. Call from separate thread!
        :param value: True if the text should be rendered.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.update_display_text(value={value})")
        if self._display_text != value:
            self._display_text = value
            self._schedule_emit("display_text")
            self.construct_current_page_graphics()

    def construct_current_page_graphics(self):
        """
        Updates the graphics for the currently selected page for display. Call from separate thread!
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.construct_current_page_graphics()")
        enhancer = ImageEnhance.Brightness(
            self.mets_book[self.current_page_index].pageimg
        )
        self._draw_image = enhancer.enhance(0.67)
        self._draw_word_gloss_objects = construct_word_and_gloss_graphics_from_mets_page(
            self.mets_book[self.current_page_index],
            display_text=self._display_text
        )
        self._draw_connection_objects = construct_connection_graphics_from_connector(
            self.gloss_connection_handler[self.current_page_index]
        )
        self._update_unconnected_gloss_lines()
        self._currently_selected_object = None
        self.data_changed.emit("construct_current_page_graphics")

    def page_index_is_valid(self, page_idx: int) -> bool:
        """
        Check if the given page index is valid.
        :param page_idx: Page index to check.
        :return: True if the page index is valid.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.page_index_is_valid(page_idx={page_idx})")
        return self._page_counter.index_is_valid(page_idx)

    def has_undo_actions(self):
        """
        Return True if there are actions that can be undone.
        :return: True if there are actions that can be undone.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.has_undo_actions()")
        return self._undo_redo_list.has_elements_before()

    def has_redo_actions(self):
        """
        Return True if there are actions that can be redone.
        :return: True if there are actions that can be redone.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.has_redo_actions()")
        return self._undo_redo_list.has_elements_after()

    def undo(self):
        """
        If possible, undo the last action.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.undo()")
        if self._undo_redo_list.has_elements_before():
            self._gloss_connection_handler[
                self.current_page_index
            ].connections = self._undo_redo_list.previous_element()
            self._draw_connection_objects = construct_connection_graphics_from_connector(
                self._gloss_connection_handler[self._page_counter.current_index]
            )
            self._schedule_emit("undo")

    def redo(self):
        """
        If possible, redo the last action.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.redo()")
        if self._undo_redo_list.has_elements_after():
            self._gloss_connection_handler[self.current_page_index].connections = self._undo_redo_list.next_element()
            self._draw_connection_objects = construct_connection_graphics_from_connector(
                self._gloss_connection_handler[self._page_counter.current_index]
            )
            self._schedule_emit("redo")

    def select_or_connect_on_coordinate(self, x: int, y: int):
        """
        Given a set of x and y coordinates, selects the object that is found on this place,
        and if another object was selected previously, attempts to connect them.
        Call from separate thread!
        :param x: X coordinate.
        :param y: Y coordinate.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.select_or_connect_on_coordinate(x={x}, y={y})")
        previous_object = self._currently_selected_object
        current_object = self.spatial_database.get_object_by_coordinate(
            page_index=self.current_page_index,
            x=x,
            y=y
        )
        self._currently_selected_object = current_object

        # Only do something if we have a previously selected and currently selected object
        if previous_object is not None and current_object is not None:
            all_start = [
                connection.start for connection in
                self.gloss_connection_handler[self.current_page_index].connections
            ]

            # we can only register when:
            # 1) the previous object is a gloss!
            # 2) the previous and current object are not the same
            # 3) the previous object is not already the start of another connection
            # 4) the two objects to be connected are not allowed to result in some kind of circular connection,
            #    e.g., a -> b -> c -> a

            new_connection = ConnectedPair(previous_object, current_object)

            # 1) previous object is not a gloss
            if not isinstance(previous_object, GlossLine):
                pass
            # 2) previous and current object are the same
            elif previous_object == current_object:
                pass
            # 3) previous object already is start of another connection
            elif previous_object in all_start:
                self.show_toast.emit("Error: Can't connect",
                                     f"{previous_object} already points to another object", ToastPreset.ERROR)
            # 4) the two objects would form a circular connection
            elif self.gloss_connection_handler[
                self.current_page_index].check_if_connection_results_in_circular_relation(
                    ConnectedPair(previous_object, current_object)):
                self.show_toast.emit("Error: Can't connect",
                                     f"This connection leads to a circular relation", ToastPreset.ERROR)
            else:
                self.gloss_connection_handler.append_connection_to_connector(
                    connector_idx=self.current_page_index,
                    connection=new_connection
                )

                # in this case, also update the undo_redo list!
                self._undo_redo_list.add_element(self.gloss_connection_handler[self.current_page_index].connections)

        self._draw_connection_objects = construct_connection_graphics_from_connector(
            self.gloss_connection_handler[self.current_page_index]
        )

        self._schedule_emit("select_or_connect_on_coordinate")

    def remove_connection(self, index_to_delete: int):
        """
        Deletes the connection that has the passed index. Call from separate thread!
        :param index_to_delete: Index of the connection to delete.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.remove_connection(index_to_delete={index_to_delete})")
        chains = self.gloss_connection_handler[
            self.current_page_index
        ].connection_chains
        del chains[index_to_delete]

        new_connections = []
        for chain in chains:
            new_connections += chain

        self.gloss_connection_handler[
            self.current_page_index
        ].connections = new_connections

        self._undo_redo_list.add_element(new_connections)

        self._draw_connection_objects = construct_connection_graphics_from_connector(
            self.gloss_connection_handler[self.current_page_index]
        )
        self._schedule_emit("remove_connection")

    def clear_metsbook_cache(self):
        """
        Cleans the METSBook cache. Must be invoked whenever the METSBook is changed!
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.clear_metsbook_cache()")
        self._mets_book_cache = None

    @Slot()
    def _start_debounce_timer(self):
        """
        Starts the debounce timer (on timeout, the signal data_changed may be emitted).
        """
        LoggerSingleton().logger.log_info(f"_ProgramState._start_debounce_timer()")
        self._debounce_timer.start(100)  # 100 ms debounce interval

    @Slot()
    def _emit_data_changed(self):
        """
        If pending changes are present, the data_changed signal is emitted with a summary of changes.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState._emit_data_changed()")
        LoggerSingleton().logger.log_info(f"Emitting _ProgramState.data_changed signal {self._pending_changes}")
        if self._pending_changes:
            # Emit the signal with a summary of changes
            self.data_changed.emit(", ".join(self._pending_changes))
            self._pending_changes.clear()

    def _schedule_emit(self, property_name):
        """
        Adds a program state change (with change name provided) to the list of _pending_changes.

        :param property_name: Name of the property to be changed.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState._schedule_emit(property_name={property_name})")
        self._pending_changes.add(property_name)
        self._request_debounce.emit()

    def _update_unconnected_gloss_lines(self):
        """
        Updates the unconnected gloss lines for this page.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState._update_unconnected_gloss_lines()")
        if self.current_page_index < len(self._gloss_connection_handler):
            self.unconnected_gloss_lines = CyclicList(
                self._gloss_connection_handler[self.current_page_index].get_unconnected_gloss_line_ids()
            )

    @property
    def has_unsaved_changes(self):
        return self._gloss_connection_handler.has_unsaved_changes

    @has_unsaved_changes.setter
    def has_unsaved_changes(self, value: bool):
        if self._gloss_connection_handler.has_unsaved_changes != value:
            self._gloss_connection_handler.has_unsaved_changes = value
            self._schedule_emit("has_unsaved_changes")

    @property
    def mets_book(self):
        return self._mets_book

    @mets_book.setter
    def mets_book(self, value):
        if self._mets_book != value:
            self._mets_book = value
            self._page_counter = CyclicCounter(len(self._mets_book))
            self._schedule_emit("mets_book")

    @property
    def gloss_connection_handler(self):
        return self._gloss_connection_handler

    @gloss_connection_handler.setter
    def gloss_connection_handler(self, value):
        if self._gloss_connection_handler != value:
            self._gloss_connection_handler = value
            self._draw_connection_objects = construct_connection_graphics_from_connector(
                self._gloss_connection_handler[self._page_counter.current_index]
            )
            self._schedule_emit("gloss_connection_handler")

    @property
    def currently_selected_object(self):
        return self._currently_selected_object

    @currently_selected_object.setter
    def currently_selected_object(self, value):
        if self._currently_selected_object != value:
            self._currently_selected_object = value
            self._schedule_emit(f"currently_selected_object ({value})")

    @property
    def draw_image(self):
        return self._draw_image

    @draw_image.setter
    def draw_image(self, value):
        if self._draw_image != value:
            self._draw_image = value
            self._schedule_emit("draw_image")

    @property
    def draw_word_gloss_objects(self):
        return self._draw_word_gloss_objects

    @draw_word_gloss_objects.setter
    def draw_word_gloss_objects(self, value):
        if self._draw_word_gloss_objects != value:
            self._draw_word_gloss_objects = value
            self._schedule_emit("draw_word_gloss_objects")

    @property
    def draw_connection_objects(self):
        return self._draw_connection_objects

    @draw_connection_objects.setter
    def draw_connection_objects(self, value):
        if self._draw_connection_objects != value:
            self._draw_connection_objects = value
            self._schedule_emit("draw_connection_objects")

    @property
    def spatial_database(self):
        return self._spatial_database

    @spatial_database.setter
    def spatial_database(self, value):
        if self._spatial_database != value:
            self._spatial_database = value
            self._schedule_emit("spatial_database")

    @property
    def current_page_index(self):
        if self._page_counter is not None:
            return self._page_counter.current_index

    @property
    def number_of_pages(self):
        if self._page_counter is not None:
            return self._page_counter.number_of_indices

    @property
    def page_counter_text(self):
        return str(self._page_counter) if self._page_counter is not None else ""


class ProgramStateSingleton:
    """
    Class ProgramStateSingleton encapsulates the _ProgramState in a global singleton.

    Attributes:
        program_state: The program state that is held by the singleton.

    Private Attributes:
        _instance: The global instance of the singleton.
        _lock: The mechanism ensuring thread safety.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProgramStateSingleton, cls).__new__(cls)
                    cls._instance.program_state = _ProgramState()
        return cls._instance
