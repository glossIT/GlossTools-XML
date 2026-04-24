from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog

from gui_files.dialog_new_project import Ui_NewProjectDialog


class OpenProjectFileSelectDialog(QDialog):
    """
    Class OpenProjectFileSelectDialog represents a dialog in which the user is asked to provide three file paths:
        1. Path to the METS file that should be opened. (Alternatively, path to a PageXML file).
        2. Path to the corresponding GlossIT TEI file to be opened.
        3. Path to the Kraken OCR MLModel that is used for automatically determining word bounding boxes.

    Private Attributes:
        _ask_for_pagexml (bool): Default value is False. If True, the user is asked to provide a PageXML file instead
                                 of a METS XML file. (This is used for the replacement of PageXML data in a METSPage.)
    Attributes:
        ui (Ui_NewProjectDialog): The user interface associate with the dialog.
        path_to_xml (str | None): Path to the XML file as indicated by the user interaction.
        path_to_tei (str | None): Path to the TEI file as indicated by the user interaction.
        path_to_model (str | None): Path to the Kraken OCR MLModel file as indicated by the user interaction.

    Methods:
        exec: Overrides QDialog.exec. Executes the dialog in the main loop.

    Private Methods:
        _check_if_ok_button_should_be_enabled: Returns a bool indicating whether the OK button should be enabled.
        _configure_ok_button: Applies the value of _check_if_ok_button_should_be_enabled to the OK button of the dialog.
        _open_xml_file_dialog: Opens a file dialog for choosing the XML file.
        _open_tei_file_dialog: Opens a file dialog for choosing the TEI file.
        _open_model_file_dialog: Opens a file dialog for choosing the Kraken OCR MLModel file.
    """
    def __init__(self, ask_for_pagexml: bool = False):
        """
        Initializes an instance of class OpenProjectFileSelectDialog.
        """
        super().__init__()

        window_title = "Replace PageXML Data" if ask_for_pagexml else "Create New Project"

        self.ui = Ui_NewProjectDialog(window_title=window_title)
        self.ui.setupUi(self)

        self.path_to_xml = None
        self.path_to_tei = None
        self.path_to_model = None

        self._ask_for_pagexml = ask_for_pagexml

        self.ui.buttonOpenMets.clicked.connect(
            self._open_xml_file_dialog()
        )
        self.ui.buttonOpenTei.clicked.connect(
            self._open_tei_file_dialog()
        )
        self.ui.buttonOpenModel.clicked.connect(
            self._open_model_file_dialog()
        )
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def exec(self):
        """
        Overrides QDialog.exec. Executes the dialog in the main loop.
        """
        result = super().exec()
        if result:  # accepted
            return self.path_to_xml, self.path_to_tei, self.path_to_model
        else:
            return None, None, None

    def _check_if_ok_button_should_be_enabled(self) -> bool:
        """
        Returns a bool indicating whether the OK button should be enabled.
        :return: True if the OK button should be enabled.
        """
        return self.path_to_xml is not None and self.path_to_tei is not None and self.path_to_model is not None

    def _configure_ok_button(self):
        """
        Applies the value of _check_if_ok_button_should_be_enabled to the OK button of the dialog.
        """
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self._check_if_ok_button_should_be_enabled()
        )

    def _open_xml_file_dialog(self):
        """
        Opens a file dialog for choosing the METS file.
        """
        def open_xml_file_dialog():
            if self._ask_for_pagexml:
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    caption="Open PageXML File",
                    filter="PageXML File (*.xml);;All Files (*.*)"
                )
            else:
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    caption="Open METS File",
                    filter="METS XML File (*METS.xml);;XML File (*.xml);;All Files (*.*)"
                )
            #mets_schema = xmlschema.XMLSchema(Constants.METS_SCHEMA)
            proceed = True
            #if not mets_schema.is_valid(path):
            #    proceed = show_warning_yesno_dialog(
            #        informative_text="The file you selected does not match the METS schema. Proceed?"
            #    ) == QMessageBox.Yes
            if proceed:
                self.path_to_xml = path
                self.ui.labelMetsFileDisplay.setText(self.path_to_xml)  # update correct label for display
            self._configure_ok_button()

        return open_xml_file_dialog

    def _open_tei_file_dialog(self):
        """
        Opens a file dialog for choosing the TEI file.
        """
        def open_tei_file_dialog():
            path, _ = QFileDialog.getOpenFileName(
                self,
                caption="Open TEI XML File",
                filter="XML File (*.xml);;All Files (*.*)"
            )
            proceed = True
            #if Constants.TEI_SCHEMA:
            #    tei_schema = xmlschema.XMLSchema(Constants.TEI_SCHEMA)
            #    if not tei_schema.is_valid(path):
            #        proceed = show_warning_yesno_dialog(
            #            informative_text="The file you selected does not match the GlossIT TEI schema. Proceed?"
            #        ) == QMessageBox.Yes
            if proceed:
                self.path_to_tei = path
                self.ui.labelTeiFileDisplay.setText(self.path_to_tei)  # update correct label for display
            self._configure_ok_button()

        return open_tei_file_dialog

    def _open_model_file_dialog(self):
        """
        Opens a file dialog for choosing the Kraken OCR MLModel file.
        :return:
        """
        def open_model_file_dialog():
            path, _ = QFileDialog.getOpenFileName(
                self,
                caption="Open Kraken OCR Model File",
                filter="Kraken OCR MLModel File (*.mlmodel);;All Files (*.*)"
            )
            self.path_to_model = path
            self.ui.labelModelFileDisplay.setText(self.path_to_model)  # update correct label for display
            self._configure_ok_button()

        return open_model_file_dialog
