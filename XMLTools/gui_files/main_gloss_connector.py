# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_gloss_connector.ui'
##
## Created by: Qt User Interface Compiler version 6.9.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, QRect,
                            QSize, Qt, QRectF, QTimer)
from PySide6.QtGui import (QIcon, QGuiApplication)
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout,
                               QLabel, QMainWindow, QMenuBar,
                               QPushButton, QSizePolicy, QStatusBar, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget, QCheckBox)
from pyqttoast import Toast, ToastPreset, ToastPosition

from coordinate_manipulation import rectangle_xywh
from glossit_connect_glosses import ConnectedPair, Word
from glossit_dataclasses import GlossLine, LineType

from .graphics import construct_connection_graphics_from_connector, \
    construct_currently_selected_object_graphic
from .logger import LoggerSingleton
from .widgets_modified import ClickableLabel, FocusableLineEdit
from .program_state import ProgramStateSingleton
from .widget_imagegraphicsview import ImageGraphicsView


WINDOW_TITLE = u"GlossIT Gloss Connector"

class Ui_MainWindow(object):
    """
    Class Ui_MainWindow represents the Gloss Connector main window user interface.

    Attributes:
        main_window (MainWindow): Reference to the parent main window.
        buttonNewProject (QPushButton): Pushing it creates a new project.
        buttonOpenProject (QPushButton): Pushing it loads a project.
        buttonSaveProject (QPushButton): Pushing it saves the project including connections as TEI.
        buttonExportTei (QPushButton): Pushing it exports the connections independent of TEI.
        buttonExportMets (QPushButton): Pushing it exports the PageXML, Image and METS file.
        buttonPreviousPage (QPushButton): Pushing it goes to the previous METSBook page.
        lineEditCurrentPage (QLabel): Displays the current page.
        buttonNextPage (QPushButton): Pushing it goes to the next METSBook page.
        treeDisplayChains (QTreeWidget): Tree widget for displaying and manipulating currently stored
                                         gloss/reference/word connection chains.
        buttonRemoveChain (QPushButton): Pushing it removes the currently selected connection chain.
        buttonUndo (QPushButton): Pushing it performs undo on the last action.
        buttonRedo (QPushButton): Pushing it performs redo on the last action.

    Methods:
        setupUI (QMainWindow): Sets up the UI window attributes.
        retranslateUi (QMainWindow): Sets label contents, button displayed names, etc.

    Private Methods:
        _tree_from_chains (list[list[ConnectedPair]]): Updates the treeDisplayChains widget according to the
                                                       content of the connection chains.
    """
    def setupUi(self, MainWindow: "MainWindow"):
        """
        Sets up the UI window attributes.

        :param MainWindow: Instance of class MainWindow (derived from QMainWindow) that acts as this UI's parent.
                           This class must provide a function thread_function(Callable) to execute costly functions
                           in a separate thread that is connected to the main loop.
        """
        self.main_window = MainWindow
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(544, 797)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.buttonPreviousPage = QPushButton(self.centralwidget)
        self.buttonPreviousPage.setObjectName(u"buttonPreviousPage")

        self.horizontalLayout_2.addWidget(self.buttonPreviousPage)

        self.lineEditCurrentPage = FocusableLineEdit(self.centralwidget)
        self.lineEditCurrentPage.setObjectName(u"lineEditCurrentPage")
        self.lineEditCurrentPage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.lineEditCurrentPage.setSizePolicy(sizePolicy)
        self.lineEditCurrentPage.setEnabled(False)

        self.horizontalLayout_2.addWidget(self.lineEditCurrentPage)

        self.buttonNextPage = QPushButton(self.centralwidget)
        self.buttonNextPage.setObjectName(u"buttonNextPage")

        self.horizontalLayout_2.addWidget(self.buttonNextPage)
        self.gridLayout.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)

        self.checkboxDisplayText = QCheckBox(self.centralwidget)
        self.checkboxDisplayText.setObjectName(u"checkboxDisplayText")

        self.textOptionsLayout = QVBoxLayout()
        self.textOptionsLayout.setObjectName(u"textOptionsLayout")
        self.textOptionsLayout.addWidget(self.checkboxDisplayText)
        self.gridLayout.addLayout(self.textOptionsLayout, 3, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")

        self.buttonNewProject = QPushButton(self.centralwidget)
        self.buttonNewProject.setToolTip(u"Create a new GlossIT project (Ctrl+N)")
        self.buttonNewProject.setObjectName(u"buttonNewProject")
        self.buttonNewProject.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentNew)))
        self.buttonNewProject.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonNewProject.clicked")
        )
        self.horizontalLayout.addWidget(self.buttonNewProject)

        self.buttonOpenProject = QPushButton(self.centralwidget)
        self.buttonOpenProject.setToolTip(u"Open a GlossIT project from a file (Ctrl+O)")
        self.buttonOpenProject.setObjectName(u"buttonOpenProject")
        self.buttonOpenProject.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen)))
        self.buttonOpenProject.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonOpenProject.clicked")
        )
        self.horizontalLayout.addWidget(self.buttonOpenProject)

        self.buttonSaveProject = QPushButton(self.centralwidget)
        self.buttonSaveProject.setToolTip(u"Save the current GlossIT project (Ctrl+S)")
        self.buttonSaveProject.setEnabled(False)
        self.buttonSaveProject.setObjectName(u"buttonSaveProject")
        self.buttonSaveProject.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave)))
        self.buttonSaveProject.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonSaveProject.clicked")
        )
        self.horizontalLayout.addWidget(self.buttonSaveProject)

        self.buttonSaveAsProject = QPushButton(self.centralwidget)
        self.buttonSaveAsProject.setToolTip(u"Save the current GlossIT project to another file (Ctrl+Shift+S)")
        self.buttonSaveAsProject.setEnabled(False)
        self.buttonSaveAsProject.setObjectName(u"buttonSaveAsProject")
        self.buttonSaveAsProject.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSaveAs)))
        self.buttonSaveAsProject.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonSaveAsProject.clicked")
        )
        self.horizontalLayout.addWidget(self.buttonSaveAsProject)

        self.buttonReplacePageXml = QPushButton(self.centralwidget)
        self.buttonReplacePageXml.setToolTip(u"Replace the current PageXML data (Ctrl+R)")
        self.buttonReplacePageXml.setEnabled(False)
        self.buttonReplacePageXml.setObjectName(u"buttonReplacePageXml")
        self.buttonReplacePageXml.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentRevert)))
        self.buttonReplacePageXml.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonReplacePageXml.clicked")
        )
        self.horizontalLayout.addWidget(self.buttonReplacePageXml)

        self.buttonExportTei = QPushButton(self.centralwidget)
        self.buttonExportTei.setToolTip(u"Export the project to a GlossIT TEI XML file (Ctrl+E)")
        self.buttonExportTei.setEnabled(False)
        self.buttonExportTei.setObjectName(u"buttonExportTei")
        self.buttonExportTei.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MailReplySender)))
        self.buttonExportTei.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonExportTei.clicked")
        )
        self.horizontalLayout.addWidget(self.buttonExportTei)

        self.buttonExportMets = QPushButton(self.centralwidget)
        self.buttonExportMets.setToolTip(u"Export the METS, images and PageXML to a folder; "
                                         u"gloss connections are disregarded (Ctrl+M)")
        self.buttonExportMets.setEnabled(False)
        self.buttonExportMets.setObjectName(u"buttonExportMets")
        self.buttonExportMets.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MailReplyAll)))
        self.buttonExportMets.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonExportMets.clicked")
        )
        self.horizontalLayout.addWidget(self.buttonExportMets)

        self.buttonPreviousPage.setToolTip("Go to previous manuscript page (Ctrl+←)")
        self.buttonPreviousPage.setEnabled(False)
        self.buttonPreviousPage.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonPreviousPage.clicked")
        )
        self.buttonNextPage.setToolTip("Go to next manuscript page (Ctrl+→)")
        self.buttonNextPage.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonNextPage.clicked")
        )
        self.buttonNextPage.setEnabled(False)

        self.checkboxDisplayText.setChecked(True)
        self.checkboxDisplayText.setText("Display Text")
        self.checkboxDisplayText.setEnabled(False)

        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.treeDisplayChains = QTreeWidget(self.centralwidget)
        self.treeDisplayChains.setObjectName(u"treeDisplayChains")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeDisplayChains.sizePolicy().hasHeightForWidth())
        self.treeDisplayChains.setSizePolicy(sizePolicy)
        self.treeDisplayChains.setMinimumSize(QSize(0, 150))

        self.verticalLayout.addWidget(self.treeDisplayChains)

        self.buttonRemoveChain = QPushButton(self.centralwidget)
        self.buttonRemoveChain.setToolTip(u"Remove the currently selected connection chain")
        self.buttonRemoveChain.setObjectName(u"buttonRemoveChain")
        self.buttonRemoveChain.setEnabled(False)
        self.buttonRemoveChain.clicked.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("buttonRemoveChain.clicked")
        )
        self.buttonRemoveChain.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditClear)))

        self.verticalLayout.addWidget(self.buttonRemoveChain)

        self.gridLayout.addLayout(self.verticalLayout, 4, 0, 1, 1)

        self.imageGraphicsView = ImageGraphicsView(self)
        self.imageGraphicsView.setObjectName(u"imageGraphicsView")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.imageGraphicsView.sizePolicy().hasHeightForWidth())
        self.imageGraphicsView.setSizePolicy(sizePolicy1)
        self.imageGraphicsView.setMinimumSize(QSize(0, 300))
        self.gridLayout.addWidget(self.imageGraphicsView, 1, 0, 1, 1)

        self.horizontalLayoutUndoRedo = QHBoxLayout()
        self.buttonUndo = QPushButton(self.centralwidget)
        self.buttonUndo.setObjectName(u"buttonUndo")
        self.buttonUndo.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditUndo)))
        self.buttonUndo.setToolTip(u"Undo the last action (Ctrl+Z)")
        self.buttonUndo.setEnabled(False)
        self.horizontalLayoutUndoRedo.addWidget(self.buttonUndo)
        self.buttonRedo = QPushButton(self.centralwidget)
        self.buttonRedo.setObjectName(u"buttonRedo")
        self.buttonRedo.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditRedo)))
        self.buttonRedo.setToolTip(u"Redo the last action (Ctrl+Y or Ctrl+Shift+Z)")
        self.buttonRedo.setEnabled(False)
        self.horizontalLayoutUndoRedo.addWidget(self.buttonRedo)
        self.gridLayout.addLayout(self.horizontalLayoutUndoRedo, 5, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 544, 23))
        MainWindow.setMenuBar(self.menubar)

        # Set up status bar
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        self.labelCurrentSelection = ClickableLabel(self.centralwidget)
        self.labelCurrentLineId = ClickableLabel(self.centralwidget)
        self.labelUnconnectedGlossLines = ClickableLabel(self.centralwidget)
        MainWindow.setStatusBar(self.statusbar)
        self.statusbar.addWidget(self.labelCurrentSelection, 1)  # stretch factor of 1
        self.statusbar.addWidget(self.labelCurrentLineId, 1)  # stretch factor of 1
        self.statusbar.addPermanentWidget(self.labelUnconnectedGlossLines)  # fixed position on the right

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

        # Connect the ProgramState signal to updating of the image widget
        program_state = ProgramStateSingleton().program_state
        def update_image():
            LoggerSingleton().logger.log_info(
                f"update_image"
            )
            self.imageGraphicsView.scene.clear()
            if program_state.draw_image is not None:
                self.imageGraphicsView.load_image_from_pil(
                    program_state.draw_image
                )
            if program_state.draw_word_gloss_objects is not None:
                for object in program_state.draw_word_gloss_objects:
                    for q_object in object.to_objects():
                        self.imageGraphicsView.scene.addItem(q_object)
            if program_state.draw_connection_objects is not None:
                for object in program_state.draw_connection_objects:
                    for q_object in object.to_objects():
                        self.imageGraphicsView.scene.addItem(q_object)
            if program_state.currently_selected_object is not None:
                for q_object in construct_currently_selected_object_graphic(
                        program_state.currently_selected_object
                ).to_objects():
                    self.imageGraphicsView.scene.addItem(q_object)

        program_state.data_changed.connect(update_image)

        # Connect the ProgramState signal to updating of tree widget
        program_state = ProgramStateSingleton().program_state
        def update_tree():
            LoggerSingleton().logger.log_info(
                f"update_tree"
            )
            if (program_state.mets_book is not None
                    and program_state.current_page_index is not None
                    and program_state.gloss_connection_handler is not None
                    and len(program_state.gloss_connection_handler) > 0
            ):
                self._tree_from_chains(
                    program_state.gloss_connection_handler[program_state.current_page_index].connection_chains
                )
        program_state.data_changed.connect(update_tree)

        # Connect the selection of an entry in the tree widget with a toggle of the selection button
        def on_selection_changed():
            curr_item = self.treeDisplayChains.currentItem()
            LoggerSingleton().logger.log_info(
                f"treeDisplayChains.clicked ("
                f"col_0 = '{curr_item.text(0) if curr_item is not None else None}', "
                f"col_1 = '{curr_item.text(1) if curr_item is not None else None}'"
                f")"
            )

            cycle_index = None
            connection_in_cycle_index = None
            if curr_item is not None and curr_item.columnCount() == 1:
                cycle_index = self.treeDisplayChains.indexOfTopLevelItem(curr_item)
                self.buttonRemoveChain.setEnabled(True)
            else:
                if curr_item is not None:
                    connection_in_cycle_index = curr_item.parent().indexOfChild(curr_item)
                    cycle_element = curr_item.parent()
                    cycle_index = self.treeDisplayChains.indexOfTopLevelItem(cycle_element)
                self.buttonRemoveChain.setEnabled(False)

            # Center view to the start element of the selection
            view_obj = None
            if cycle_index is not None:
                if connection_in_cycle_index is not None:
                    view_obj = program_state.gloss_connection_handler[
                        program_state.current_page_index
                    ].connection_chains[cycle_index][connection_in_cycle_index].start
                else:
                    view_obj = program_state.gloss_connection_handler[
                        program_state.current_page_index
                    ].connection_chains[cycle_index][0].start

            if view_obj is not None:  # the start of a connection is always a GlossLine object
                rectangle = view_obj.get_bounding_box()
                rectangle = QRectF(*rectangle_xywh(rectangle))
                self.imageGraphicsView.fitInView(rectangle, Qt.AspectRatioMode.KeepAspectRatio)

        self.treeDisplayChains.clicked.connect(on_selection_changed)

        # Connect clicking the remove connection button with deleting the current connection
        def on_click_remove_connection():
            curr_item = self.treeDisplayChains.currentItem()

            def remove_connection():
                if curr_item is not None:
                    # because the naming convention is 'Child 2' for the 1st tree entry
                    index_to_delete = int(curr_item.text(0).split(" ")[-1]) - 1
                    program_state.remove_connection(index_to_delete)
            self.main_window.thread_function(remove_connection)
        self.buttonRemoveChain.clicked.connect(on_click_remove_connection)

        # Connect clicking the update display text checkbox
        def on_click_checkbox_display_text():
            curr_value = self.checkboxDisplayText.isChecked()
            def update_display_text():
                program_state.update_display_text(curr_value)
            self.main_window.thread_function(update_display_text)
        self.checkboxDisplayText.clicked.connect(on_click_checkbox_display_text)

        # Connect the Previous Page and Next Page buttons to the corresponding actions, and update the label accordingly
        def on_click_previous_page():
            def to_previous_page():
                program_state.go_to_previous_page()
            self.main_window.thread_function(to_previous_page)

        def on_click_next_page():
            def to_next_page():
                program_state.go_to_next_page()
            self.main_window.thread_function(to_next_page)

        # Also connect the page selector accordingly
        def on_current_page_changed():
            """
            This function is called when the current page selection is changed and RETURN or ENTER was pressed.
            We use it to check validity of the user input and go to the selected page.
            """
            suffix = f" / {program_state.number_of_pages}"
            current_text = self.lineEditCurrentPage.text()

            LoggerSingleton().logger.log_user_interaction(f"lineEditCurrentPage returnPressed {current_text}")

            try:
                if current_text.endswith(suffix):
                    number = int(current_text.split("/")[0].strip())
                else:
                    number = int(current_text)
                number -= 1  # user expects the numbering to start from 1!

                if not program_state.page_index_is_valid(number):
                    number = None
            except Exception as e:
                number = None

            def go_to_page():
                try:
                    program_state.go_to_page(number)
                except Exception as e:
                    pass

            if number is None:
                # reset the displayed text to the standard value
                self.lineEditCurrentPage.setText(program_state.page_counter_text)
            else:
                self.main_window.thread_function(go_to_page)

            self.lineEditCurrentPage.clearFocus()

        def on_page_text_gained_focus():
            """
            This function is called when the page text has gained focus.
            We use this to automatically preselect the number that should be changed
            by the user for easy usability.
            """
            LoggerSingleton().logger.log_user_interaction("lineEditCurrentPage gained focus")
            current_text = self.lineEditCurrentPage.text()
            prefix = f"{program_state.current_page_index + 1}"
            suffix = f" / {program_state.number_of_pages}"
            if current_text == f"{prefix}{suffix}":
                # wrap in single shot timer to have enough time that the selection occurs
                QTimer.singleShot(0, lambda: self.lineEditCurrentPage.setSelection(0, len(prefix)))

        self.buttonPreviousPage.clicked.connect(on_click_previous_page)
        self.buttonNextPage.clicked.connect(on_click_next_page)
        program_state.data_changed.connect(
            lambda: (
                self.lineEditCurrentPage.setText(str(program_state.page_counter_text)),
                LoggerSingleton().logger.log_info(f"update_line_edit_current_page")
            )
        )
        self.lineEditCurrentPage.inFocus.connect(on_page_text_gained_focus)
        self.lineEditCurrentPage.returnPressed.connect(on_current_page_changed)

        # Update status bar
        def update_status_bar():
            LoggerSingleton().logger.log_info(
                f"update_status_bar"
            )

            currently_selected_object_text = "Currently selected: "
            if program_state.currently_selected_object is not None:
                currently_selected_object_text += program_state.currently_selected_object.to_minimal_string()
            else:
                currently_selected_object_text += "None"

            current_line_id = "Line ID: "
            if program_state.currently_selected_object is not None:
                if isinstance(program_state.currently_selected_object, GlossLine):
                    current_line_id += program_state.currently_selected_object.id
                elif isinstance(program_state.currently_selected_object, Word):
                    current_line_id += program_state.currently_selected_object.line.id
                else:
                    LoggerSingleton().logger.log_warning("Selected object is neither GlossLine nor Word")
                    current_line_id += "INVALID"
            else:
                current_line_id += "None"

            unconnected_gloss_line_text = "Unconnected Gloss Lines: "
            if program_state.current_page_index is not None and program_state.unconnected_gloss_lines is not None:
                nlines = len(
                    program_state.unconnected_gloss_lines
                )
                unconnected_gloss_line_text += str(nlines)
            else:
                unconnected_gloss_line_text += "None"

            window_title = f"{WINDOW_TITLE} — {program_state.save_file_path}"
            if program_state.has_unsaved_changes:
                window_title += " [Unsaved Changes]"
            MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", window_title, None))

            self.labelCurrentSelection.setText(currently_selected_object_text)
            self.labelCurrentLineId.setText(current_line_id)
            self.labelUnconnectedGlossLines.setText(unconnected_gloss_line_text)

        # Center image view widget to selection when labelCurrentSelection is clicked
        def on_center_view_on_current_selection():
            def center_view_on_current_selection():
                current_object = program_state.currently_selected_object
                if current_object is not None:
                    rectangle = current_object.get_bounding_box()
                    rectangle = QRectF(*rectangle_xywh(rectangle))
                    self.imageGraphicsView.fitInView(rectangle, Qt.AspectRatioMode.KeepAspectRatio)
                else:
                    self.imageGraphicsView.resetTransform()
            self.main_window.thread_function(center_view_on_current_selection)
        self.labelCurrentSelection.clicked.connect(on_center_view_on_current_selection)

        # Copy Line ID into clipboard when labelCurrentLineID is clicked
        def on_copy_line_id_to_clipboard():
            current_line_id = None
            if isinstance(program_state.currently_selected_object, GlossLine):
                current_line_id = program_state.currently_selected_object.id
            elif isinstance(program_state.currently_selected_object, Word):
                current_line_id = program_state.currently_selected_object.line.id
            else:
                LoggerSingleton().logger.log_warning("Selected object is neither GlossLine nor Word")

            toast = Toast(self.centralwidget)
            toast.setDuration(4000)
            if current_line_id is not None:
                QGuiApplication.clipboard().setText(current_line_id)
                toast.setTitle('Success!')
                toast.setText('Copied Line ID to clipboard.')
                toast.applyPreset(ToastPreset.SUCCESS)
            else:
                toast.setTitle('Failure!')
                toast.setText('Could not copy line ID to clipboard.')
                toast.applyPreset(ToastPreset.ERROR)
            toast.setPositionRelativeToWidget(self.centralwidget)
            toast.setPosition(ToastPosition.BOTTOM_RIGHT)
            toast.show()
        self.labelCurrentLineId.clicked.connect(on_copy_line_id_to_clipboard)

        # Center image view widget to unconnected gloss and go to the next one
        def on_center_view_on_unconnected_gloss_line():
            def center_view_on_unconnected_gloss_line():
                if program_state.mets_book is not None and program_state.current_page_index is not None:
                    current_gloss_line = program_state.unconnected_gloss_lines.get_current_element()
                    if current_gloss_line is not None:
                        try:
                            current_object = program_state.mets_book[
                                program_state.current_page_index
                            ].get_object_from_id(current_gloss_line)
                            rectangle = current_object.get_bounding_box()
                            rectangle = QRectF(*rectangle_xywh(rectangle))
                            self.imageGraphicsView.fitInView(rectangle, Qt.AspectRatioMode.KeepAspectRatio)
                            program_state.unconnected_gloss_lines.next_element()
                        except ValueError as e:
                            LoggerSingleton().logger.log_exception(e)

            self.main_window.thread_function(center_view_on_unconnected_gloss_line)

        self.labelUnconnectedGlossLines.clicked.connect(on_center_view_on_unconnected_gloss_line)

        program_state.data_changed.connect(update_status_bar)

        # Connect Undo and Redo
        def update_undo_redo_buttons():
            LoggerSingleton().logger.log_info(
                f"update_undo_redo_buttons"
            )
            self.buttonUndo.setEnabled(program_state.has_undo_actions())
            self.buttonRedo.setEnabled(program_state.has_redo_actions())

        def on_undo():
            LoggerSingleton().logger.log_user_interaction("buttonUndo clicked")
            def undo():
                program_state.undo()
            self.main_window.thread_function(undo)

        def on_redo():
            LoggerSingleton().logger.log_user_interaction("buttonRedo clicked")
            def redo():
                program_state.redo()
            self.main_window.thread_function(redo)

        self.buttonUndo.clicked.connect(on_undo)
        self.buttonRedo.clicked.connect(on_redo)
        program_state.data_changed.connect(update_undo_redo_buttons)
        # setupUi

    def retranslateUi(self, MainWindow: QMainWindow):
        """
        Sets label contents, button displayed names, etc.

        :param MainWindow: QMainWindow instance that acts as this UI's parent.
        """
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", WINDOW_TITLE, None))
        self.buttonPreviousPage.setText(QCoreApplication.translate("MainWindow", u"<< Previous Page", None))
        self.lineEditCurrentPage.setText(QCoreApplication.translate("MainWindow", u"", None))
        self.buttonNextPage.setText(QCoreApplication.translate("MainWindow", u"Next Page >>", None))
        self.buttonNewProject.setText(QCoreApplication.translate("MainWindow", u"New Project", None))
        self.buttonOpenProject.setText(QCoreApplication.translate("MainWindow", u"Load Project", None))
        self.buttonSaveProject.setText(QCoreApplication.translate("MainWindow", u"Save Project", None))
        self.buttonSaveAsProject.setText(QCoreApplication.translate("MainWindow", u"Save Project As", None))
        self.buttonReplacePageXml.setText(QCoreApplication.translate("MainWindow", u"Replace Current PageXML", None))
        self.buttonExportTei.setText(QCoreApplication.translate("MainWindow", u"Export TEI", None))
        self.buttonExportMets.setText(QCoreApplication.translate("MainWindow", u"Export METS", None))

        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Connection Chains:", None))
        ___qtreewidgetitem = self.treeDisplayChains.headerItem()
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Connection", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"Chain", None))
        self.buttonRemoveChain.setText(QCoreApplication.translate("MainWindow", u"Remove Chain", None))
        self.buttonUndo.setText(QCoreApplication.translate("MainWindow", u"Undo", None))
        self.buttonRedo.setText(QCoreApplication.translate("MainWindow", u"Redo", None))
    # retranslateUi

    def _tree_from_chains(self, chains: list[list[ConnectedPair]]):
        """
        Updates the treeDisplayChains widget according to the content of the connection chains.
        :param chains: Connection chains.
        """
        LoggerSingleton().logger.log_info(
            f"_tree_from_chains"
        )
        self.treeDisplayChains.clearSelection()
        self.treeDisplayChains.clear()
        for idx, chain in enumerate(chains):
            item = QTreeWidgetItem(self.treeDisplayChains)
            item.setText(0, f"Chain {idx+1}")
            for connection in chain:
                subitem = QTreeWidgetItem(item)
                subitem.setText(
                    1,
                    f"{connection.start.type} '{connection.start.text}' "
                    f"→ {connection.end.type} '{connection.end.text}'"
                )
        self.treeDisplayChains.expandAll()
