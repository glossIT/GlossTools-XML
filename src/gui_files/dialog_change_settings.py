from PySide6.QtGui import QColor, QIcon, Qt
from PySide6.QtWidgets import QDialog, QCheckBox, QHBoxLayout, QVBoxLayout, QPushButton, \
    QLabel, QSlider, QColorDialog, QApplication, QWidget

from gui_files.logger import LoggerSingleton
from gui_files.settings import SettingsKey, settings_get, settings_get_default_values


class ColorButton(QWidget):
    def __init__(self, label, initial_color=QColor(255, 255, 255), *args, **kwargs):
        super().__init__()

        self._label = label
        self._color = initial_color

        self.button = QPushButton(self, *args, **kwargs)
        self.color_label = QLabel(self)
        self.update_style()
        self.button.clicked.connect(self.choose_color)

        # Layouts
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.button)
        main_layout.addWidget(self.color_label)

        self.setLayout(main_layout)

    def color(self):
        return self._color

    def set_color(self, value):
        if isinstance(value, QColor):
            self._color = value
        else:
            self._color = QColor(value)
        self.update_style()

    def choose_color(self):
        color = QColorDialog.getColor(self._color, self, f"Pick color for {self._label}")
        if color.isValid():
            self.set_color(color)

    def update_style(self):
        color_name = self._color.name(QColor.NameFormat.HexRgb)
        self.button.setStyleSheet(f"background-color: {color_name};")
        self.color_label.setText(color_name)


class FloatSlider(QSlider):
    def __init__(self, parent=None, resolution=100, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.resolution = resolution

    def minimum(self) -> float:
        return super().minimum()/self.resolution

    def setMinimum(self, minimum: float):
        super().setMinimum(int(minimum*self.resolution))

    def maximum(self) -> float:
        return super().maximum()/self.resolution

    def setMaximum(self, maximum: float):
        super().setMaximum(int(maximum*self.resolution))

    def value(self) -> float:
        return float(super().value()/self.resolution)

    def setValue(self, value: float):
        super().setValue(int(value*self.resolution))

    def setTickInterval(self, interval: float):
        super().setTickInterval(int(interval*self.resolution))


class LabeledSlider(QWidget):
    def __init__(self, is_float=False, *args, **kwargs):
        super().__init__()

        if is_float:
            self.slider = FloatSlider(Qt.Orientation.Horizontal, *args, **kwargs)
        else:
            self.slider = QSlider(Qt.Orientation.Horizontal, *args, **kwargs)

        # Labels
        self.label_min = QLabel()
        self.label_max = QLabel()
        self.label_value = QLabel()
        self.label_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Layouts
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.label_min)
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.label_max)

        main_layout = QVBoxLayout()
        main_layout.addLayout(slider_layout)
        main_layout.addWidget(self.label_value)

        self.setLayout(main_layout)

        # Connect signals
        self.slider.valueChanged.connect(self.update_labels)

        # Initialize labels
        self.update_labels()

    def update_labels(self):
        min_val = self.slider.minimum()
        max_val = self.slider.maximum()
        cur_val = self.slider.value()
        self.label_min.setText(f"{min_val}")
        self.label_max.setText(f"{max_val}")
        self.label_value.setText(f"{cur_val}")

    # Proxy methods for convenience
    def setMinimum(self, value):
        self.slider.setMinimum(value)
        self.update_labels()

    def setMaximum(self, value):
        self.slider.setMaximum(value)
        self.update_labels()

    def setValue(self, value):
        self.slider.setValue(value)
        self.update_labels()

    def setTickInterval(self, value):
        self.slider.setTickInterval(value)

    def setTickPosition(self, position):
        self.slider.setTickPosition(position)

    def value(self):
        return self.slider.value()


class ChangeSettingsDialog(QDialog):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.setWindowTitle("Change Settings")

        self.widgets = {}

        self._updated_settings = None
        self._setupUi()
        self._load_settings()

    def _setupUi(self):
        layout = QVBoxLayout(self)

        # Image display sliders
        self.widgets[SettingsKey.IMAGE_BRIGHTNESS] = self._create_slider("Image Brightness", layout, is_normed=True)
        self.widgets[SettingsKey.IMAGE_CONTRAST] = self._create_slider("Image Contrast", layout, is_normed=True)
        self.widgets[SettingsKey.IMAGE_SATURATION] = self._create_slider("Image Saturation", layout, is_normed=True)

        # Transparency sliders
        self.widgets[SettingsKey.FILL_TRANSPARENCY] = self._create_slider("Fill Opacity", layout)
        self.widgets[SettingsKey.TEXT_TRANSPARENCY] = self._create_slider("Text Opacity", layout)
        self.widgets[SettingsKey.SELECTION_TRANSPARENCY] = self._create_slider("Selection Opacity", layout)

        # Color pickers
        self.widgets[SettingsKey.ARROW_FILL] = self._create_color_button("Arrow Fill", layout)
        self.widgets[SettingsKey.MAIN_WORD_FILL] = self._create_color_button("Main Word Fill", layout)
        self.widgets[SettingsKey.MAIN_WORD_TEXT] = self._create_color_button("Main Word Text", layout)
        self.widgets[SettingsKey.REFERENCE_SIGN_FILL] = self._create_color_button("Reference Sign Fill", layout)
        self.widgets[SettingsKey.REFERENCE_SIGN_TEXT] = self._create_color_button("Reference Sign Text", layout)
        self.widgets[SettingsKey.GLOSS_FILL] = self._create_color_button("Gloss Fill", layout)
        self.widgets[SettingsKey.GLOSS_TEXT] = self._create_color_button("Gloss Text", layout)


        # Save and Cancel buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave)))
        self.default_btn = QPushButton("Revert to Default")
        self.default_btn.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditUndo)))
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditDelete)))
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.default_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Connect signals
        self.save_btn.clicked.connect(self._save_settings)
        self.default_btn.clicked.connect(self._restore_default)
        self.cancel_btn.clicked.connect(self.reject)

    @classmethod
    def _create_slider(cls, label_text, parent_layout, is_normed=False):
        label = QLabel(label_text)

        if is_normed:
            slider = LabeledSlider(is_float=True)
            slider.setMinimum(0.)
            slider.setMaximum(2.)
            slider.setTickInterval(0.1)
        else:
            slider = LabeledSlider()
            slider.setMinimum(0)
            slider.setMaximum(200)
            slider.setTickInterval(5)

        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        parent_layout.addWidget(label)
        parent_layout.addWidget(slider)
        return slider

    @classmethod
    def _create_color_button(cls, label_text, parent_layout):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        color_button = ColorButton(label=label_text)
        layout.addWidget(label)
        layout.addWidget(color_button)
        parent_layout.addLayout(layout)
        return color_button

    def _widget_get_value(self, key):
        if isinstance(self.widgets[key], QCheckBox):  # checkboxes
            return self.widgets[key].isChecked()
        elif isinstance(self.widgets[key], (QSlider, FloatSlider, LabeledSlider)):  # sliders
            return self.widgets[key].value()
        elif isinstance(self.widgets[key], ColorButton):
            return self.widgets[key].color()
        else:
            LoggerSingleton().logger.log_warning(f"Cannot set value for undefined widget type "
                                                 f"{self.widgets[key].__class__.__name__}")
        return

    def _widget_set_value(self, key, value):
        if isinstance(self.widgets[key], QCheckBox):  # checkboxes
            self.widgets[key].setChecked(bool(value))
        elif isinstance(self.widgets[key], (QSlider, FloatSlider, LabeledSlider)):  # sliders
            self.widgets[key].setValue(value)
        elif isinstance(self.widgets[key], ColorButton):
            self.widgets[key].set_color(value)
        else:
            LoggerSingleton().logger.log_warning(f"Cannot set value for undefined widget type "
                                                 f"{self.widgets[key].__class__.__name__}")

    def _load_settings(self, settings_dict: dict = None):
        if settings_dict is None:  # take values from the global application settings
            for key in self.widgets.keys():
                self._widget_set_value(key, settings_get(key))
        else:
            for key, value in settings_dict.items():
                self._widget_set_value(key, value)

    def _save_settings(self):
        # Collect all settings in a dict
        updated_settings = {}

        for key in self.widgets.keys():
            updated_settings[key] = self._widget_get_value(key)

        self._updated_settings = updated_settings
        self.accept()

    def _restore_default(self):
        self._load_settings(settings_get_default_values())

    def reject(self):
        self._result = None
        super().reject()

    def exec(self) -> dict | None:
        super().exec()
        return self._updated_settings
