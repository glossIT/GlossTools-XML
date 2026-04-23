import os
import shutil

from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, \
    QMessageBox
from PySide6.QtCore import Signal, QCoreApplication, QSettings, QThread, QMetaObject, Slot, Q_ARG, \
    qInstallMessageHandler, QtMsgType
import sys
from typing import Callable
import umsgpack
import uuid
import zlib

from glossit_connect_glosses import GlossOnPageConnector
from xml_extraction import METSBook
from gui_files.dialog_save_on_exit import DialogSaveOnExit
from gui_files.dialog_select_files import OpenProjectFileSelectDialog
from gui_files.dialog_loading import LoadingDialog, LoadingDialogContent
from gui_files.gloss_connector_manager import ObservableGlossOnPageConnector
from gui_files.logger import LoggerSingleton
from gui_files.main_gloss_connector import Ui_MainWindow
from gui_files.program_state import ProgramStateSingleton
from gui_files.spatial_database import SpatialDatabase


# TODO
class Constants:
    METS_SCHEMA: str = "./schemas/mets.xsd"
    TEI_SCHEMA: str = None  # TODO "./schemas/tei.xsd"


def show_warning_yesno_dialog(informative_text=""):
    """
    This opens a dialog informing the user of an error and asks them if they want to proceed the action.
    :param informative_text: The error message that should be displayed.
    """
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
        finished (Signal): This signal is emitted when the thread has finished executing its assigned function.
        function_to_run (Callable): The costly function that should be run in a separate thread.

    Methods:
        run: Starts executing the function passed in a separate thread. Upon finishing, the signal
             finished is emitted.
    """
    finished = Signal()

    def __init__(self, function_to_run: Callable = None):
        """
        Constructs an instance of class ThreadWrapper.

        :param function_to_run: The costly function that should be run in a separate thread.
        """
        super().__init__()
        self.function_to_run = function_to_run

    def run(self):
        """
        Executes the function in the thread and emits the
        :return:
        """
        LoggerSingleton().logger.log_threaded_function(self.function_to_run.__name__)
        try:
            self.function_to_run()
            self.finished.emit()
        except Exception as e:
            LoggerSingleton().logger.log_exception(e)


class MainWindow(QMainWindow):
    """
    Class MainWindow represents the gloss connector main window.

    Attributes:
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
        _close_thread (uuid.UUID): Closes the thread with the passed ID and removes it from the list threads.
        _enable_buttons: Enables all buttons that can only be accessed after a project is loaded or created.
    """

    def __init__(self):
        super().__init__()
        program_state = ProgramStateSingleton().program_state
        program_state._main_window = self

        QCoreApplication.setOrganizationName("GlossIT")
        QCoreApplication.setApplicationName("GlossIT Gloss Connector")
        QCoreApplication.setOrganizationDomain("https://glossit.uni-graz.at")
        self.setWindowIcon(program_state.icon)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Load window geometry
        self.settings = QSettings("GlossIT", "GlossIT Gloss Connector")
        self.restoreGeometry(self.settings.value("windowGeometry"))

        # connect buttons to actions
        self.ui.buttonNewProject.clicked.connect(self._new_project)
        self.ui.buttonOpenProject.clicked.connect(self._open_project)
        self.ui.buttonSaveProject.clicked.connect(self._save_project)
        self.ui.buttonSaveAsProject.clicked.connect(self._save_as_project)
        self.ui.buttonReplacePageXml.clicked.connect(self._replace_pagexml)
        self.ui.buttonExportTei.clicked.connect(self._export_tei)
        self.ui.buttonExportMets.clicked.connect(self._export_mets)

        self.threads = dict()

    def keyPressEvent(self, event):
        """
        Overrides QMainWindow.keyPressEvent to enable keyboard shortcuts.
        :param event: Passed event.
        """
        key = event.key()
        LoggerSingleton().logger.log_info(f"keyPressEvent ({key})")
        program_state = ProgramStateSingleton().program_state

        if key == Qt.Key.Key_Escape:
            program_state.currently_selected_object = None
        elif key == Qt.Key.Key_N and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._new_project()
        elif key == Qt.Key.Key_O and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._open_project()
        elif (key == Qt.Key.Key_S and
              event.modifiers() & Qt.KeyboardModifier.ControlModifier and
              event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._save_as_project()
        elif key == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._save_project()
        elif key == Qt.Key.Key_R and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._replace_pagexml()
        elif key == Qt.Key.Key_E and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._export_tei()
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
        elif key == Qt.Key.Key_M and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._export_mets()

    def closeEvent(self, event):
        """
        Overrides QMainWindow.closeEvent to enable for saving window geometry.
        :param event: Passed close event.
        """
        LoggerSingleton().logger.log_info("closeEvent")

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

        self.settings.setValue("windowGeometry", self.saveGeometry())
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
        :param tqdm_progress: Progress bar that is displayed.
        :param exit_after: Closes the main window after the thread has finished.
        """
        if loading_window_content is None:
            loading_window_content = LoadingDialogContent()
        loading_dialog = LoadingDialog(self, content=loading_window_content)
        loading_dialog.show()
        new_thread = ThreadWrapper(function_to_run)
        thread_id = uuid.uuid4()
        self.threads[thread_id] = {"thread": new_thread, "loading_dialog": loading_dialog}
        new_thread.finished.connect(self._close_thread(thread_id=thread_id))
        if exit_after:
            new_thread.finished.connect(self.close)
        new_thread.start()
        return new_thread

    @Slot(str, str)
    def _show_error_dialog(self, title: str, message: str):
        QMessageBox.critical(None, title, message)

    def _new_project(self):
        """
        Opens an OpenProjectFileSelectDialog and initializes the program state singleton accordingly.
        """
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
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to read file from file system.")
                    )
                    return

                try:
                    loaded_uncompressed = zlib.decompress(loaded_compressed)
                except zlib.error as e:
                    LoggerSingleton().logger.log_exception(e)
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to decompress data.")
                    )
                    return

                try:
                    loaded_unserialized = umsgpack.loads(loaded_uncompressed)
                except (EOFError, umsgpack.UnpackException) as e:
                    LoggerSingleton().logger.log_exception(e)
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to unserialize data.")
                    )
                    return

                loading_window_content.action_text = "Loading file contents into program state"
                loading_window_content.progress_bar_visible = True
                try:
                    program_state.from_dict(loaded_unserialized, tqdm_progress=loading_window_content.callback_tqdm)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to read file contents. Is this a valid GlossIT project file?")
                    )
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
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Some error has occurred.")
                    )
                    loading_window_content.callback_tqdm.close()

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
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to serialize data.")
                    )

                try:
                    compressed_data = zlib.compress(serialized_data)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to compress data.")
                    )

                try:
                    with open(save_path, "wb") as file:
                        file.write(compressed_data)
                except umsgpack.PackException as e:
                    LoggerSingleton().logger.log_exception(e)
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to write file to file system.")
                    )
                    return
                # Update the status of the saved changes
                program_state.has_unsaved_changes = False

            self.thread_function(on_save, loading_window_content=loading_window_content, exit_after=exit_after)

    def _replace_pagexml(self):
        """
        Asks the user for a path to a PageXML and adapted TEI file to replace the currently selected page.
        """
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
                QMetaObject.invokeMethod(
                    self,
                    "_show_error_dialog",
                    Qt.QueuedConnection,
                    Q_ARG(str, "Error"),
                    Q_ARG(str, "Failed to read files or perform OCR recognition.")
                )
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
                QMetaObject.invokeMethod(
                    self,
                    "_show_error_dialog",
                    Qt.QueuedConnection,
                    Q_ARG(str, "Error"),
                    Q_ARG(str, "Failed to replace old TEI data by new TEI data.")
                )
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
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to apply connections to TEI data.")
                    )
                    return

                loading_window_content.action_text = "Saving to file system"
                try:
                    with open(save_path, "w", encoding="utf-8") as file:
                        file.write(save_tei)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    QMetaObject.invokeMethod(
                        self,
                        "_show_error_dialog",
                        Qt.QueuedConnection,
                        Q_ARG(str, "Error"),
                        Q_ARG(str, "Failed to save file to file system.")
                    )
                    return

            self.thread_function(on_export, loading_window_content=loading_window_content)

    def _export_mets(self):
        """
        Asks the user to select a folder to which the METS file, the PageXML data and manuscript page
        images are exported.
        """
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
                        QMetaObject.invokeMethod(
                            self,
                            "_show_error_dialog",
                            Qt.QueuedConnection,
                            Q_ARG(str, "Error"),
                            Q_ARG(str, f"Failed to delete contents of directory {create_export_path}.")
                        )

        # Now, save the METS file, the images and the PageXML
        def on_export_mets():
            with open(os.path.join(create_export_path, f"METS.xml"), "w") as file:
                file.write(program_state.mets_book.construct_mets().prettify())
            for idx, page in enumerate(program_state.mets_book):
                with open(os.path.join(create_export_path, f"{idx:04d}.xml"), "w") as file:
                    file.write(page.pagexml.prettify())
                page.pageimg.save(os.path.join(create_export_path, f"{idx:04d}.jpg"))

        self.thread_function(on_export_mets)

    def _close_thread(self, thread_id: uuid.UUID) -> Callable:
        """
        Returns a function handle to a function that closes the thread with the passed ID and removes it
        from the list threads.
        :param thread_id: ID of the thread to be closed.
        :return: Function handle.
        """

        def close_thread():
            if thread_id in self.threads:
                self.threads[thread_id]["loading_dialog"].close_dialog()
                self.threads[thread_id]["thread"].terminate()
                del self.threads[thread_id]

        return close_thread

    def _enable_buttons(self):
        """
        Enables all buttons that can only be accessed after a project is loaded or created.
        """
        self.ui.buttonSaveProject.setEnabled(True)
        self.ui.buttonSaveAsProject.setEnabled(True)
        self.ui.buttonReplacePageXml.setEnabled(True)
        self.ui.buttonExportTei.setEnabled(True)
        self.ui.buttonExportMets.setEnabled(True)
        self.ui.buttonPreviousPage.setEnabled(True)
        self.ui.buttonNextPage.setEnabled(True)
        self.ui.checkboxDisplayText.setEnabled(True)
        self.ui.lineEditCurrentPage.setEnabled(True)


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
