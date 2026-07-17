import os
import shutil

from PySide6.QtGui import QIcon, QPainter, QPageSize, Qt, QKeySequence
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox
from PySide6.QtCore import Signal, QCoreApplication, QSizeF, QThread, Slot, \
    qInstallMessageHandler, QtMsgType
import sys
from typing import Callable
import umsgpack
import uuid
import zlib

from glossit_connect_glosses import GlossOnPageConnector
from gui_files.dialog_change_settings import ChangeSettingsDialog
from gui_files.dialog_save_on_exit import DialogSaveOnExit
from gui_files.dialog_select_files import OpenProjectFileSelectDialog
from gui_files.dialog_loading import LoadingDialog, LoadingDialogContent
from gui_files.gloss_connector_manager import ObservableGlossOnPageConnector
from gui_files.logger import LoggerSingleton
from gui_files.main_gloss_connector import Ui_MainWindow
from gui_files.program_state import ProgramStateSingleton
from gui_files.settings import SettingsKey, settings_get, settings_set, settings_revert_to_default_values
from gui_files.spatial_database import SpatialDatabase
from xml_extraction import METSBook


# TODO
class Constants:
    METS_SCHEMA: str = "./schemas/mets.xsd"
    TEI_SCHEMA: str = None  # TODO "./schemas/tei.xsd"


def show_warning_yesno_dialog(informative_text=""):
    """
    This opens a dialog informing the user of an error and asks them if they want to proceed the action.
    :param informative_text: The error message that should be displayed.
    """
    LoggerSingleton().logger.log_info(f"show_warning_yesno_dialog(informative_text={informative_text})")
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setText("WARNING")
    msg_box.setInformativeText(informative_text)
    msg_box.setWindowTitle("Warning")
    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return msg_box.exec()


class ThreadWrapper(QThread):
    """
    Class ThreadWrapper wraps some intense function into a separate thread,
    such that the main loop is not blocked.

    Attributes:
        finished (Signal[object]): This signal is emitted when the thread has finished executing its assigned function.
                                   It carries the thread_id assigned by MainWindow.thread_function.
        function_to_run (Callable): The costly function that should be run in a separate thread.
        thread_id (uuid.UUID | None): Identifier assigned by MainWindow.thread_function for cleanup bookkeeping.

    Methods:
        run: Starts executing the function passed in a separate thread. Upon finishing, the signal
             finished is emitted.
    """
    finished = Signal(object)

    def __init__(self, function_to_run: Callable = None):
        """
        Constructs an instance of class ThreadWrapper.

        :param function_to_run: The costly function that should be run in a separate thread.
        """
        super().__init__()
        self.function_to_run = function_to_run
        self.thread_id = None

    def run(self):
        """
        Executes the function in the thread and emits the
        :return:
        """
        LoggerSingleton().logger.log_threaded_function(self.function_to_run.__name__)
        try:
            self.function_to_run()
        except Exception as e:
            LoggerSingleton().logger.log_exception(e)
        finally:
            # Always emit, even on exception! Otherwise, the modal LoadingDialog is never closed
            # and the GUI is stuck behind an unclosable dialog
            self.finished.emit(self.thread_id)


class MainWindow(QMainWindow):
    """
    Class MainWindow represents the gloss connector main window.

    Attributes:
        show_error_dialog (Signal[str, str]): This signal is emitted when an error message dialog should be displayed.
                                              First string is the title, second string is the error message.
        ui (Ui_MainWindow): The user interface associated with the main window.
        settings (QSettings): Stores settings such as window geometry to restore after restarting the software.
        threads (list[ThreadWrapper]): A list of threads that are currently being executed.

    Methods:
        closeEvent (QEvent): Overrides QMainWindow.closeEvent for asking the user to save and to enable saving window
                             geometry.
        keyPressEvent (QEvent): Overrides QMainWindow.keyPressEvent to enable keyboard shortcuts.
        thread_function (Callable, LoadingWindowContent, bool): Executes the function in a separate thread and displays
                                                                a LoadingDialog while not finished.

    Private Methods:
        _new_project: Opens an OpenProjectFileSelectDialog and initializes the program state singleton accordingly.
        _open_project: Asks the user to select a glp file and loads it into the program state.
        _save_project (bool): Saves the current project to the previously saved file. If this is the first save,
                       _save_as_project is called.
        _save_as_project (bool): Saves the current project to a file.
        _save_project_to_path (str, bool): Saves the current project to the location provided.
        _replace_pagexml: Asks the user for a path to a PageXML and adapted TEI file to replace the currently
                          selected page.
        _export_tei: Asks the user to select a file to which the TEI including connection data is exported.
        _export_mets: Asks the user to select a folder to which the METS file, the PageXML data and manuscript page
                      images are exported.
        _open_settings: Opens the settings dialog window and applies them to the program.
        _close_thread (uuid.UUID): Closes the thread with the passed ID and removes it from the list threads.
        _enable_buttons: Enables all buttons that can only be accessed after a project is loaded or created.
        _show_toast (str, str, ToastPreset): Forwards a show_toast signal to the UI on the main thread.
    """
    show_error_dialog = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.show_error_dialog.connect(self._show_error_dialog)

        program_state = ProgramStateSingleton().program_state
        program_state._main_window = self

        QCoreApplication.setOrganizationName("GlossIT")
        QCoreApplication.setApplicationName("GlossIT Gloss Connector")
        QCoreApplication.setOrganizationDomain("https://glossit.uni-graz.at")
        self.setWindowIcon(program_state.icon)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Connect to a bound method of this QObject to show toasts
        program_state.show_toast.connect(self._show_toast)

        # Check if all settings are set, otherwise reset them to default values
        for key in SettingsKey:
            if settings_get(key) is None:
                settings_revert_to_default_values()
                LoggerSingleton().logger.log_warning(f"Invalid setting value '{settings_get(key)}' for key '{key}'. "
                                                     f"Revert all settings to default.")
                break

        # Load window geometry
        self.restoreGeometry(settings_get(SettingsKey.GEOMETRY))
        self.restoreState(settings_get(SettingsKey.WINDOW_STATE))

        # Set debug logging
        LoggerSingleton().logger.enable_debug_logging(settings_get(SettingsKey.DEBUG_ENABLED))

        # connect buttons to actions
        self.ui.actionNewProject.triggered.connect(self._new_project)
        self.ui.actionNewProject.setShortcut(QKeySequence("Ctrl+N"))

        self.ui.actionOpenProject.triggered.connect(self._open_project)
        self.ui.actionOpenProject.setShortcut(QKeySequence("Ctrl+O"))

        self.ui.actionSaveProject.triggered.connect(self._save_project)
        self.ui.actionSaveProject.setShortcut(QKeySequence("Ctrl+S"))

        self.ui.actionSaveAsProject.triggered.connect(self._save_as_project)
        self.ui.actionSaveAsProject.setShortcut(QKeySequence("Ctrl+Shift+S"))

        self.ui.actionReplacePageXml.triggered.connect(self._replace_pagexml)
        self.ui.actionReplacePageXml.setShortcut(QKeySequence("Ctrl+R"))

        self.ui.actionExportTei.triggered.connect(self._export_tei)
        self.ui.actionExportTei.setShortcut(QKeySequence("Ctrl+E"))

        self.ui.actionExportMets.triggered.connect(self._export_mets)

        self.ui.actionExportView.triggered.connect(self._export_view)

        self.ui.actionOpenSettings.triggered.connect(self._open_settings)

        self.threads = dict()

    def keyPressEvent(self, event):
        """
        Overrides QMainWindow.keyPressEvent to enable keyboard shortcuts.
        :param event: Passed event.
        """
        key = event.key()
        LoggerSingleton().logger.log_info(f"MainWindow.keyPressEvent ({key})")
        program_state = ProgramStateSingleton().program_state

        if key == Qt.Key.Key_Escape:
            program_state.currently_selected_object = None

        elif key == Qt.Key.Key_Left and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            def shortcut_to_previous_page():
                program_state.go_to_previous_page()

            self.thread_function(shortcut_to_previous_page)
        elif key == Qt.Key.Key_Right and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            def shortcut_to_next_page():
                program_state.go_to_next_page()

            self.thread_function(shortcut_to_next_page)
        elif (key == Qt.Key.Key_Z and
              event.modifiers() & Qt.KeyboardModifier.ControlModifier and
              event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.thread_function(program_state.redo)
        elif key == Qt.Key.Key_Y and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.thread_function(program_state.redo)
        elif key == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.thread_function(program_state.undo)
        elif key == Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            import objgraph
            objgraph.show_growth(limit=10)
            print("\n")

    def closeEvent(self, event):
        """
        Overrides QMainWindow.closeEvent to enable for saving window geometry.
        :param event: Passed close event.
        """
        LoggerSingleton().logger.log_info("MainWindow.closeEvent")

        if ProgramStateSingleton().program_state.has_unsaved_changes:
            # ask the user how they want to proceed when unsaved changes are present
            action_value = DialogSaveOnExit().exec()

            if action_value == DialogSaveOnExit.CANCEL:
                event.ignore()
                return
            elif action_value == DialogSaveOnExit.DISCARD:
                pass
            elif action_value == DialogSaveOnExit.SAVE:
                event.ignore()
                self._save_project(exit_after=True)
                return

        settings_set(SettingsKey.GEOMETRY, self.saveGeometry())
        settings_set(SettingsKey.WINDOW_STATE, self.saveState())
        event.accept()

    def thread_function(
            self,
            function_to_run: Callable,
            loading_window_content: LoadingDialogContent = None,
            exit_after: bool = False
    ):
        """
        Executes the function in a separate thread and displays a LoadingDialog while not finished.

        :param function_to_run: Function that should be executed.
        :param loading_window_content: Containing information about what should be shown in the loading dialog.
        :param exit_after: Closes the main window after the thread has finished.
        """
        if loading_window_content is None:
            loading_window_content = LoadingDialogContent()
        loading_dialog = LoadingDialog(self, content=loading_window_content)
        loading_dialog.show()
        new_thread = ThreadWrapper(function_to_run)
        thread_id = uuid.uuid4()
        new_thread.thread_id = thread_id
        self.threads[thread_id] = {"thread": new_thread, "loading_dialog": loading_dialog}

        # Connect to the bound method (a slot on this QObject) so the cleanup runs on the
        # main thread via a queued connection. Connecting a plain closure here
        # would make Qt invoke it in the emitting worker thread, where closing the dialog
        # (a GUI operation) is NOT allowed and deadlocks the application!
        new_thread.finished.connect(self._close_thread)

        if exit_after:
            new_thread.finished.connect(self.close)
        new_thread.start()
        return new_thread


    @Slot(str, str)
    def _show_error_dialog(self, title: str, message: str):
        LoggerSingleton().logger.log_info(f"MainWindow._show_error_dialog(title={title}, message={message})")
        QMessageBox.critical(self, title, message)

    def _new_project(self):
        """
        Opens an OpenProjectFileSelectDialog and initializes the program state singleton accordingly.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._new_project()")
        program_state = ProgramStateSingleton().program_state

        program_state.save_file_path = None  # Reset save file name to prevent accidentally overriding other data!

        open_project_dialog = OpenProjectFileSelectDialog()
        path_to_mets, path_to_tei, path_to_model = open_project_dialog.exec()
        LoggerSingleton().logger.log_info(f"User selected METS path {path_to_mets}")
        LoggerSingleton().logger.log_info(f"User selected TEI path {path_to_tei}")
        LoggerSingleton().logger.log_info(f"User selected model path {path_to_model}")
        if path_to_mets and path_to_tei and path_to_model:
            program_state.path_to_mets = path_to_mets
            program_state.path_to_tei = path_to_tei
            program_state.path_to_model = path_to_model

            loading_window_content = LoadingDialogContent()

            def on_new():
                loading_window_content.action_text = "Loading METS and word boundary box recognition"
                loading_window_content.progress_bar_visible = True

                program_state.mets_book = METSBook(
                    mets_path=program_state.path_to_mets,
                    tei_path=program_state.path_to_tei,
                    ocr_model_path=program_state.path_to_model,
                    tqdm_progress=loading_window_content.callback_tqdm
                )
                loading_window_content.callback_tqdm.close()
                loading_window_content.action_text = "Extracting gloss connections from pages"

                loading_window_content.callback_tqdm.iterable = program_state.mets_book
                loading_window_content.callback_tqdm.total = len(program_state.mets_book)
                loading_window_content.callback_tqdm.reset()
                connections = []
                for page in loading_window_content.callback_tqdm:
                    connections.append(ObservableGlossOnPageConnector(page))
                loading_window_content.callback_tqdm.close()

                program_state.gloss_connection_handler.connector_list = connections

                loading_window_content.progress_bar_visible = False
                loading_window_content.action_text = "Setting up graphics"
                program_state.construct_current_page_graphics()
                loading_window_content.progress_bar_visible = True

                loading_window_content.action_text = "Setting up spatial database"
                program_state.spatial_database = SpatialDatabase(
                    program_state.mets_book,
                    tqdm_progress=loading_window_content.callback_tqdm
                )

            self.thread_function(on_new, loading_window_content=loading_window_content)

            # Now, we allow saving, exporting, and going to previous/next pages
            self._enable_buttons()

    def _open_project(self):
        """
        Asks the user to select a *.glp file and loads it into the program state.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._open_project()")
        program_state = ProgramStateSingleton().program_state

        # get path of where the file should be saved
        load_path, _ = QFileDialog.getOpenFileName(
            self,
            caption="Open GlossIT Project File",
            filter="GlossIT Project File (*.glp);;All Files (*.*)"
        )
        LoggerSingleton().logger.log_info(f"User selected model path {load_path}")
        if load_path is not None and load_path != "":
            loading_window_content = LoadingDialogContent()

            def on_load():
                loading_window_content.status_text = "Please wait..."
                loading_window_content.action_text = "Reading from file system"
                program_state.save_file_path = load_path
                try:
                    with open(load_path, "rb") as file:
                        loaded_compressed = file.read()
                except (EOFError, umsgpack.UnpackException) as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to read file from file system.")
                    return

                try:
                    loaded_uncompressed = zlib.decompress(loaded_compressed)
                except zlib.error as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to decompress data.")
                    return

                try:
                    loaded_unserialized = umsgpack.loads(loaded_uncompressed)
                except (EOFError, umsgpack.UnpackException) as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to unserialize data.")
                    return

                loading_window_content.action_text = "Loading file contents into program state"
                loading_window_content.progress_bar_visible = True
                try:
                    program_state.from_dict(loaded_unserialized, tqdm_progress=loading_window_content.callback_tqdm)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error",
                                                "Failed to read file contents. Is this a valid GlossIT project file?")
                    return

                loading_window_content.callback_tqdm.close()

                try:
                    program_state.construct_current_page_graphics()
                    loading_window_content.action_text = "Setting up spatial database"

                    program_state.spatial_database = SpatialDatabase(
                        program_state.mets_book,
                        tqdm_progress=loading_window_content.callback_tqdm
                    )
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Some error has occurred.")
                    loading_window_content.callback_tqdm.close()
                    return

                program_state.has_unsaved_changes = False

            self.thread_function(on_load, loading_window_content=loading_window_content)

            # Now, we allow saving, exporting, and going to previous/next pages
            self._enable_buttons()

    def _save_project(self, exit_after: bool = False):
        """
        Saves the current project to the previously saved file. If this is the first save,
        _save_as_project is called.
        :param exit_after: Exit after saving the project.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._save_project(exit_after={exit_after})")
        program_state = ProgramStateSingleton().program_state
        default_filename = program_state.save_file_path
        if default_filename is None:
            self._save_as_project(exit_after=exit_after)
        else:
            self._save_project_to_path(default_filename, exit_after=exit_after)

    def _save_as_project(self, exit_after: bool = False):
        """
        Saves the current project to a file.
        :param exit_after: Exit after saving the project.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._save_as_project(exit_after={exit_after})")
        program_state = ProgramStateSingleton().program_state
        default_filename = program_state.save_file_path
        if default_filename is None:
            default_filename = os.path.join(os.path.dirname(program_state.path_to_mets), "project.glp")

        # get path of where the file should be saved
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save GlossIT Project File",
            dir=default_filename,
            filter="GlossIT Project File (*.glp);;All Files (*.*)"
        )
        self._save_project_to_path(save_path, exit_after=exit_after)

    def _save_project_to_path(self, save_path: str, exit_after: bool = False):
        """
        Saves the current project to the location provided.
        :param exit_after: Exit after saving the project.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._save_project_to_path(save_path={save_path}, "
                                          f"exit_after={exit_after})")
        program_state = ProgramStateSingleton().program_state
        if save_path is not None and save_path != "":
            if save_path.split(".")[-1] != "glp":
                save_path += ".glp"
            program_state.save_file_path = save_path
            loading_window_content = LoadingDialogContent()

            def on_save():
                loading_window_content.status_text = "Please wait..."
                loading_window_content.action_text = "Constructing save file"
                loading_window_content.progress_bar_visible = True
                save_file = program_state.to_dict(tqdm_progress=loading_window_content.callback_tqdm)
                loading_window_content.callback_tqdm.close()
                loading_window_content.progress_bar_visible = False

                loading_window_content.action_text = "Saving to file system"
                loading_window_content.status_text = "Please wait..."
                try:
                    serialized_data = umsgpack.dumps(save_file)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to serialize data.")
                    return

                try:
                    compressed_data = zlib.compress(serialized_data)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to compress data.")
                    return

                try:
                    with open(save_path, "wb") as file:
                        file.write(compressed_data)
                except umsgpack.PackException as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to write file to file system.")
                    return
                # Update the status of the saved changes
                program_state.has_unsaved_changes = False

            self.thread_function(on_save, loading_window_content=loading_window_content, exit_after=exit_after)

    def _replace_pagexml(self):
        """
        Asks the user for a path to a PageXML and adapted TEI file to replace the currently selected page.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._replace_pagexml()")
        program_state = ProgramStateSingleton().program_state
        loading_window_content = LoadingDialogContent()

        current_page_index = program_state.current_page_index
        current_page = program_state.mets_book[current_page_index]

        replace_pagexml_dialog = OpenProjectFileSelectDialog(ask_for_pagexml=True)
        path_to_pagexml, path_to_tei, path_to_model = replace_pagexml_dialog.exec()
        LoggerSingleton().logger.log_info(f"User selected PageXML path {path_to_pagexml}")
        LoggerSingleton().logger.log_info(f"User selected TEI path {path_to_tei}")
        LoggerSingleton().logger.log_info(f"User selected model path {path_to_model}")

        def replace_pagexml():
            # 1) Load the file contents
            try:
                loading_window_content.status_text = "Please wait..."
                loading_window_content.action_text = "Reading from file system and performing OCR recognition"
                current_page.replace_pagexml(
                    pagexml_path=path_to_pagexml,
                    tei_path=path_to_tei,
                    ocr_model_path=path_to_model
                )
            except Exception as e:
                LoggerSingleton().logger.log_exception(e)
                self.show_error_dialog.emit("Error",
                                            f"Failed to read files or perform OCR recognition.")
                return

            # 2) Replace old TEI data by new TEI data
            try:
                loading_window_content.status_text = "Please wait..."
                loading_window_content.action_text = "Replacing old TEI data by new TEI data."
                tei = current_page.tei
                clean_tei = GlossOnPageConnector.remove_connections(tei)
                for page_idx, page in enumerate(program_state.mets_book):
                    page.tei_path = path_to_tei
                    page.tei = clean_tei
                    program_state.gloss_connection_handler[page_idx].clean_tei = clean_tei
            except Exception as e:
                LoggerSingleton().logger.log_exception(e)
                self.show_error_dialog.emit("Error",
                                            f"Failed to replace old TEI data with new TEI data.")
                return

            # 3) Remove current page connections
            program_state.gloss_connection_handler[current_page_index].connections = []
            program_state.spatial_database.construct_page_by_index(current_page, current_page_index)

            # 4) Clean cache and update page graphics
            program_state.clear_metsbook_cache()
            program_state.construct_current_page_graphics()

        if path_to_pagexml and path_to_tei and path_to_model:
            self.thread_function(replace_pagexml, loading_window_content=loading_window_content)

    def _export_tei(self):
        """
        Asks the user to select a file to which the TEI including connection data is exported.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._export_tei()")
        program_state = ProgramStateSingleton().program_state
        if program_state.save_file_path is not None:
            default_filename = "".join(program_state.save_file_path.split(".")[:-1])  # remove extension
        else:
            default_filename = "export"
        default_filename += "_connected.xml"

        # get path of where the file should be saved
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Export GlossIT TEI with connections",
            dir=default_filename,
            filter="TEI XML File (*.xml);;All Files (*.*)"
        )
        if save_path is not None and save_path != "":
            if save_path.split(".")[-1] != "xml":
                save_path += ".xml"
            loading_window_content = LoadingDialogContent()

            def on_export():
                loading_window_content.status_text = "Please wait..."
                loading_window_content.action_text = "Constructing connected TEI"

                try:
                    save_tei = program_state.gloss_connection_handler[0].clean_tei
                    for connector in program_state.gloss_connection_handler:
                        save_tei = connector.apply_connections(connector.connection_chains, input_tei=save_tei)
                    save_tei = str(save_tei)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error",
                                                f"Failed to apply connections to TEI data.")
                    return

                loading_window_content.action_text = "Saving to file system"
                try:
                    with open(save_path, "w", encoding="utf-8") as file:
                        file.write(save_tei)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error",
                                                f"Failed to save file to file system.")
                    return

            self.thread_function(on_export, loading_window_content=loading_window_content)

    def _export_mets(self):
        """
        Asks the user to select a folder to which the METS file, the PageXML data and manuscript page
        images are exported.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._export_mets()")
        program_state = ProgramStateSingleton().program_state
        if program_state.save_file_path is not None:
            base_folder = os.path.dirname(program_state.save_file_path)  # remove extension
        else:
            base_folder = "."

        # get path of where the file should be saved
        base_folder = QFileDialog.getExistingDirectory(
            self,
            caption="Export GlossIT METS, PageXML and Images (without connections)",
            dir=base_folder,
            options=QFileDialog.Option.ShowDirsOnly
        )

        if program_state.save_file_path is not None:
            export_folder_name = f'{"".join(program_state.save_file_path.split('.')[:-1])}_export'
        else:
            export_folder_name = "export"

        create_export_path = os.path.join(base_folder, export_folder_name)

        try:
            os.makedirs(create_export_path, exist_ok=False)
        except OSError:
            do_overwrite_files = show_warning_yesno_dialog(
                informative_text=f"The contents of folder {create_export_path} will be overwritten. Proceed?"
            ) == QMessageBox.Yes
            if not do_overwrite_files:  # exit if the user does not want the contents to be overwritten
                return
            else:  # clear directory
                for filename in os.listdir(create_export_path):
                    file_path = os.path.join(create_export_path, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except OSError as e:
                        LoggerSingleton().logger.log_exception(e)
                        self.show_error_dialog.emit("Error",
                                                    f"Failed to delete contents of directory {create_export_path}.")
                        return

        # Now, save the METS file, the images and the PageXML
        def on_export_mets():
            with open(os.path.join(create_export_path, f"METS.xml"), "w") as file:
                file.write(program_state.mets_book.construct_mets().prettify())
            for idx, page in enumerate(program_state.mets_book):
                with open(os.path.join(create_export_path, f"{idx:04d}.xml"), "w") as file:
                    file.write(page.pagexml.prettify())
                page.pageimg.save(os.path.join(create_export_path, f"{idx:04d}.jpg"))

        self.thread_function(on_export_mets)

    def _export_view(self):
        """
        Asks the user to select a file to which the currently displayed view is exported as PDF.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._export_view()")
        program_state = ProgramStateSingleton().program_state
        if program_state.save_file_path is not None:
            default_filename = "".join(program_state.save_file_path.split(".")[:-1])  # remove extension
        else:
            default_filename = "export"
        default_filename += "_view.pdf"

        # get path of where the file should be saved
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Export current view as PDF",
            dir=default_filename,
            filter="PDF File (*.xml);;All Files (*.*)"
        )
        if save_path is not None and save_path != "":
            if save_path.split(".")[-1] != "pdf":
                save_path += ".pdf"
            loading_window_content = LoadingDialogContent()

            def on_export():
                loading_window_content.status_text = "Please wait..."
                loading_window_content.action_text = "Constructing view"

                try:
                    printer = QPrinter()
                    printer.setOutputFormat(QPrinter.PdfFormat)
                    printer.setOutputFileName(save_path)

                    scene = self.ui.imageGraphicsView.scene
                    rect = scene.sceneRect()

                    page_size = QPageSize(QSizeF(rect.width(), rect.height()), QPageSize.Point)
                    printer.setPageSize(page_size)

                    printer.setFullPage(True)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error",
                                                f"Failed to construct PDF printer.")
                    return

                loading_window_content.action_text = "Saving to file system"
                try:
                    painter = QPainter(printer)
                    scene.render(painter)
                    painter.end()
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error",
                                                f"Failed to save file to file system.")
                    return

            self.thread_function(on_export, loading_window_content=loading_window_content)

    def _open_settings(self):
        """
        Opens the settings dialog window and applies them to the program.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._open_settings()")

        change_settings_dialog = ChangeSettingsDialog()
        settings_dict = change_settings_dialog.exec()
        if settings_dict is not None:
            for key, value in settings_dict.items():
                settings_set(key, value)

        program_state = ProgramStateSingleton().program_state
        LoggerSingleton().logger.enable_debug_logging(settings_get(SettingsKey.DEBUG_ENABLED))
        if program_state.draw_image is not None:
            program_state.construct_current_page_graphics()

    @Slot(object)
    def _close_thread(self, thread_id: uuid.UUID):
        """
        Closes the loading dialog belonging to the finished thread and removes the thread from the
        dictionary threads. Invoked on the main thread via the ThreadWrapper.finished signal.
        :param thread_id: ID of the thread to be closed.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._close_thread(thread_id={thread_id})")
        entry = self.threads.pop(thread_id, None)
        if entry is not None:
            entry["loading_dialog"].close_dialog()
            # The thread has already left its run() method (the signal finished was emitted at its end).
            # Now, wait for the OS thread to fully terminate before dropping the last reference.
            entry["thread"].wait()

    def _enable_buttons(self):
        """
        Enables all buttons that can only be accessed after a project is loaded or created.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._enable_buttons()")
        self.ui.actionSaveProject.setEnabled(True)
        self.ui.actionSaveAsProject.setEnabled(True)
        self.ui.actionReplacePageXml.setEnabled(True)
        self.ui.actionExportTei.setEnabled(True)
        self.ui.actionExportMets.setEnabled(True)
        self.ui.actionExportView.setEnabled(True)
        self.ui.buttonPreviousPage.setEnabled(True)
        self.ui.buttonNextPage.setEnabled(True)
        self.ui.checkboxDisplayText.setEnabled(True)
        self.ui.lineEditCurrentPage.setEnabled(True)

    def _show_toast(self, toast_title, toast_text, toast_preset):
        """
        Forwards a show_toast signal to the UI on the main thread.
        """
        self.ui.show_toast(toast_title, toast_text, toast_preset)


def start_gui():
    """
    Starts the GlossIT Gloss Connector GUI.
    """

    def qt_message_handler(mode, context, message):
        # Choose logging level based on message type
        logger = LoggerSingleton().logger
        if mode == QtMsgType.QtDebugMsg:
            logger.log_debug(message)
        elif mode == QtMsgType.QtInfoMsg:
            logger.log_info(message)
        elif mode == QtMsgType.QtWarningMsg:
            logger.log_warning(message)
        elif mode == QtMsgType.QtCriticalMsg:
            logger.log_error(message)
        elif mode == QtMsgType.QtFatalMsg:
            logger.log_error(message)
        else:
            logger.log_info(message)

    try:
        app = QApplication(sys.argv)

        # Redirect Qt stderr output to the logger
        qInstallMessageHandler(qt_message_handler)

        icon = QIcon()
        icon.addFile("./gui_files/icon.png")
        app.setWindowIcon(icon)
        ProgramStateSingleton().program_state.icon = icon
        window = MainWindow()
        window.setWindowIcon(icon)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        LoggerSingleton().logger.log_exception(e)


if __name__ == "__main__":
    start_gui()
