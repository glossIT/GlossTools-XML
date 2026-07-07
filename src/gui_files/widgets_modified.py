from typing import Callable

from PySide6.QtCore import QEvent, Signal, Qt, QTimer
from PySide6.QtWidgets import QLineEdit, QWidget, QLabel, QMenu, QToolTip

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


class ToolTipMenu(QMenu):
    """
    ToolTipMenu endows a QMenu with tooltip support.

    Methods:
        mouseMoveEvent (QEvent): Override. Is called when the mouse is moved.
        leaveEvent (QEvent): Override. Is called when the widget leaves.

    Private Methods:
         _show_tooltip: Displays the tooltip.
    """
    def __init__(self, title: str, parent=None, tooltip_delay=1000):
        """
        Initializes the ToolTipMenu instance.
        :param title: Menu title.
        :param parent: Parent widget.
        :param tooltip_delay: Time in milliseconds between hovering over the action and the tooltip display.
        """
        super().__init__(title, parent)
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._show_tooltip)
        self._current_action = None
        self._current_pos = None
        self._tooltip_delay = tooltip_delay

    def mouseMoveEvent(self, event):
        """
        Override. Is called when the mouse is moved.
        :param event: The event that is passed.
        """
        action = self.actionAt(event.pos())
        if action != self._current_action:
            self._tooltip_timer.stop()
            QToolTip.hideText()
            self._current_action = action
            self._current_pos = event.globalPos()
            if action and action.toolTip():
                self._tooltip_timer.start(self._tooltip_delay)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """
        Override. Is called when the widget leaves.
        :param event: The event that is passed.
        """
        self._tooltip_timer.stop()
        QToolTip.hideText()
        self._current_action = None
        self._current_pos = None
        super().leaveEvent(event)

    def _show_tooltip(self):
        """
        Displays the tooltip.
        """
        if self._current_action and self._current_action.toolTip():
            QToolTip.showText(self._current_pos, self._current_action.toolTip(), self)