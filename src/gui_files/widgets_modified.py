from typing import Callable

from PySide6.QtCore import QEvent, QTimer, Signal, Qt
from PySide6.QtWidgets import QLineEdit, QWidget, QLabel

from gui_files.logger import LoggerSingleton


class FocusableLineEdit(QLineEdit):
    """
    FocusableLineEdit endows a QLineEdit with a signal when the widget gains focus.

    Attributes:
        inFocus (Signal): Signal that is emitted when the widget gains focus.

    Methods:
        focusInEvent (QEvent): Override. Is called when the widget gains focus.
    """
    inFocus = Signal()

    def __init__(self, parent: QWidget = None):
        """
        Initializes the FocusableLineEdit instance.
        :param parent: Parent widget.
        """
        super(FocusableLineEdit, self).__init__(parent)

    def focusInEvent(self, event: QEvent):
        """
        Override. Is called when the widget gains focus.
        :param event: The event that is passed.
        """
        self.inFocus.emit()


class ClickableLabel(QLabel):
    """
    ClickableLabel endows a QLabel with a signal when the widget is clicked.

    Attributes:
        clicked (Signal): Signal that is emitted when the widget is clicked.

    Methods:
        mousePressEvent (QEvent): Override. Is called when the widget is clicked.

    """
    clicked = Signal()

    def __init__(self, parent: QWidget = None):
        """
        Initializes the ClickableLabel instance.
        :param parent: Parent widget.
        """
        super(ClickableLabel, self).__init__(parent)

    def mousePressEvent(self, event: QEvent):
        """
        Override. Is called when the widget is clicked.
        :param event: The event that is passed.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()