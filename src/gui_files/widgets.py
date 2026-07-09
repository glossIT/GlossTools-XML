from typing import Callable

from PySide6.QtCore import QEvent, QTimer, Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLineEdit, QWidget, QLabel, QMenu, QToolTip, QColorDialog, QSlider, QVBoxLayout, \
    QPushButton, QHBoxLayout

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


class FloatSlider(QSlider):
    """
    FloatSlider endows a QSlider with float value functionality.

    Methods:
        minimum: Override. Returns the slider's minimum value.
        setMinimum (float): Override. Sets the slider's minimum value.
        maximum: Override. Returns the slider's maximum value.
        setMaximum (float): Override. Sets the slider's maximum value.
        value: Override. Returns the slider's current value.
        setValue (float): Override. Sets the slider's current value.
        setTickInverval (float): Override. Sets the slider's tick interval.
    """
    def __init__(self, parent=None, resolution=100, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._resolution = resolution

    def minimum(self) -> float:
        """
        Override. Returns the slider's minimum value.
        :return: The slider's minimum value.
        """
        return super().minimum() / self._resolution

    def setMinimum(self, minimum: float):
        """
        Override. Sets the slider's minimum value.
        :param minimum: New minimum value.
        """
        super().setMinimum(int(minimum * self._resolution))

    def maximum(self) -> float:
        """
        Override. Returns the slider's maximum value.
        :return: The slider's maximum value.
        """
        return super().maximum() / self._resolution

    def setMaximum(self, maximum: float):
        """
        Override. Sets the slider's maximum value.
        :param maximum: New maximum value.
        """
        super().setMaximum(int(maximum * self._resolution))

    def value(self) -> float:
        """
        Override. Returns the slider's current value.
        :return: The slider's current value.
        """
        return float(super().value() / self._resolution)

    def setValue(self, value: float):
        """
        Override. Sets the slider's current value.
        :param value: New current value.
        """
        super().setValue(int(value * self._resolution))

    def setTickInterval(self, interval: float):
        """
        Override. Sets the slider's tick interval.
        :param interval: New tick interval.
        """
        super().setTickInterval(int(interval * self._resolution))


class ColorButton(QWidget):
    """
    ColorButton is a widget for displaying and selecting a color value.
    It consists of a button displaying a color and a text label to its right indicating the
    color's hex value. When clicking the button, a QColorDialog is opened and the color value
    held by the widget can be changed by the user.

    Methods:
        color: Returns the currently selected color.
        set_color (QColor): Sets the color the widget holds.
        choose_color: Opens a dialog that lets the user choose the color the widget holds.

    Private Methods:
        _update_style: Updates the button color and the color label text.
    """

    def __init__(self, label, initial_color=QColor(255, 255, 255), *args, **kwargs):
        """
        Initializes the ColorButton instance.

        :param label: Label that is displayed in the QColorDialog: f"Pick color for {label}"
        :param initial_color: Initial color value.
        :param args: Arguments.
        :param kwargs: Keyword arguments.
        """
        super().__init__()

        self._label = label
        self._color = initial_color

        self._button = QPushButton(self, *args, **kwargs)
        self._color_label = QLabel(self)
        self._update_style()
        self._button.clicked.connect(self.choose_color)

        # Layouts
        main_layout = QHBoxLayout()
        main_layout.addWidget(self._button)
        main_layout.addWidget(self._color_label)

        self.setLayout(main_layout)

    def color(self) -> QColor:
        """
        Returns the currently selected color.
        :return: The color that is held by the widget.
        """
        return self._color

    def set_color(self, color: QColor):
        """
        Sets the color the widget holds.
        :param color: New color value.
        """
        self._color = color
        self._update_style()

    def choose_color(self):
        """
        Opens a dialog that lets the user choose the color the widget holds.
        """
        color = QColorDialog.getColor(self._color, self, f"Pick color for {self._label}")
        if color.isValid():
            self.set_color(color)

    def _update_style(self):
        """
        Updates the button color and the color label text.
        """
        color_name = self._color.name(QColor.NameFormat.HexRgb)
        self._button.setStyleSheet(f"background-color: {color_name};")
        self._color_label.setText(color_name)


class LabeledSlider(QWidget):
    """
    LabeledSlider bundles a QSlider (or FloatSlider) together with labels indicating
    its minimum, maximum, and current values.

    Methods:
        minimum: Returns the slider's minimum value.
        setMinimum (int | float): Sets the slider's minimum value.
        maximum: Returns the slider's maximum value.
        setMaximum (int | float): Sets the slider's maximum value.
        value: Returns the slider's current value.
        setValue (int | float): Sets the slider's current value.
        tickInterval: Returns the slider's tick interval.
        setTickInterval (int | float): Sets the slider's tick interval.
        tickPosition: Returns the slider's tick position.
        setTickPosition (QSlider.TickPosition): Sets the slider's tick position.

    Private Methods:
        _update_labels: Updates the labels for minimum, maximum, and current values.

    """
    def __init__(self, is_float=False, *args, **kwargs):
        """
        Initializes the LabeledSlider instance.

        :param is_float: If True, a FloatSlider instance is used, otherwise a QSlider instance.
        :param args: Arguments.
        :param kwargs: Keyword arguments.
        """
        super().__init__()

        if is_float:
            self._slider = FloatSlider(Qt.Orientation.Horizontal, *args, **kwargs)
        else:
            self._slider = QSlider(Qt.Orientation.Horizontal, *args, **kwargs)

        # Labels
        self._label_min = QLabel()
        self._label_max = QLabel()
        self._label_value = QLabel()
        self._label_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Layouts
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self._label_min)
        slider_layout.addWidget(self._slider)
        slider_layout.addWidget(self._label_max)

        main_layout = QVBoxLayout()
        main_layout.addLayout(slider_layout)
        main_layout.addWidget(self._label_value)

        self.setLayout(main_layout)

        # Connect signals
        self._slider.valueChanged.connect(self._update_labels)

        # Initialize labels
        self._update_labels()

    def minimum(self) -> int | float:
        """
        Returns the slider's minimum value.
        :return: The slider's minimum value.
        """
        return self._slider.minimum()

    def setMinimum(self, minimum: int | float):
        """
        Sets the slider's minimum value.
        :param minimum: New minimum value.
        """
        self._slider.setMinimum(minimum)
        self._update_labels()

    def maximum(self) -> int | float:
        """
        Returns the slider's maximum value.
        :return: The slider's maximum value.
        """
        return self._slider.maximum()

    def setMaximum(self, maximum: int | float):
        """
        Sets the slider's maximum value.
        :param maximum: New maximum value.
        """
        self._slider.setMaximum(maximum)
        self._update_labels()

    def value(self) -> int | float:
        """
        Returns the slider's current value.
        :return: The slider's current value.
        """
        return self._slider.value()

    def setValue(self, value: int | float):
        """
        Sets the slider's current value.
        :param value: New current value.
        """
        self._slider.setValue(value)
        self._update_labels()

    def tickInterval(self) -> int | float:
        """
        Returns the slider's tick interval.
        :return: The slider's tick interval.
        """
        return self._slider.tickInterval()

    def setTickInterval(self, tick_interval: int | float):
        """
        Sets the slider's tick interval.
        :param tick_interval: New tick interval.
        """
        self._slider.setTickInterval(tick_interval)

    def tickPosition(self) -> QSlider.TickPosition:
        """
        Returns the slider's tick position.
        :return: The slider's tick position.
        """
        return self._slider.tickPosition()

    def setTickPosition(self, tick_position: QSlider.TickPosition):
        """
        Sets the slider's tick position.
        :param tick_position: New tick position.
        """
        self._slider.setTickPosition(tick_position)

    def _update_labels(self):
        """
        Updates the labels for minimum, maximum, and current values.
        """
        self._label_min.setText(f"{self._slider.minimum()}")
        self._label_max.setText(f"{self._slider.maximum()}")
        self._label_value.setText(f"{self._slider.value()}")
