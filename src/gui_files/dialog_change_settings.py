from PySide6.QtGui import QIcon, Qt, QColor
from PySide6.QtWidgets import QDialog, QCheckBox, QHBoxLayout, QVBoxLayout, QPushButton, \
    QLabel, QSlider, QApplication, QLayout, QTabWidget, QWidget

from gui_files.logger import LoggerSingleton
from gui_files.settings import (Settings, settings_get, settings_get_default_values, group_settings_by_menu,
                                uint8_t, constrained_float)

from gui_files.widgets import ColorButton, FloatSlider, LabeledSlider


class ChangeSettingsDialog(QDialog):
    """
    This dialog is for modifying the application settings.
    
    Methods:
        exec: Override. Executes the dialog in the main loop and returns the settings dict on accept, else None.
        reject: Override.

    Private Methods:
        _setupUI: Setups the dialog UI widgets.

    Private Class Methods:
        _create_slider (str, QLayout, bool): Create a LabeledSlider widget with a label indicating its purpose.
        _create_color_button (str, QLayout): Create a ColorButton widget with a label indicating its purpose.
        _widget_get_value (Settings): Extracts the value of the widget that is registered with a Settings.
        _widget_set_value (Settings, object): Sets a new value for the widget that is registered with a Settings.
        _load_settings (dict[Settings, object] | None): Loads the settings from a dictionary or from the global
                                                           application settings.
        _save_settings: Collects the settings from the dialog in a dictionary and accepts the dialog.
        _restore_defaults: Loads the default application settings and applies them to the widgets.
    """
    def __init__(self):
        """
        Initialize the class instance.
        """
        super().__init__()

        self.setWindowTitle("Change Settings")

        self._widgets = {}

        self._updated_settings = None
        self._setupUi()
        self._load_settings()

    def _setupUi(self):
        """
        Setup the dialog UI widgets.
        """
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        for menu_str, settings in group_settings_by_menu().items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)

            for setting in settings:
                if issubclass(setting.type, uint8_t):
                    self._widgets[setting] = self._create_slider(setting.display_name, tab_layout, is_normed=False)
                elif issubclass(setting.type, constrained_float):
                    self._widgets[setting] = self._create_slider(setting.display_name, tab_layout, is_normed=True)
                elif issubclass(setting.type, QColor):
                    self._widgets[setting] = self._create_color_button(setting.display_name, tab_layout)
                elif issubclass(setting.type, bool):
                    self._widgets[setting] = QCheckBox(setting.display_name)
                    tab_layout.addWidget(self._widgets[setting])

            self.tabs.addTab(tab, menu_str)

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
    def _create_slider(cls, label_text: str, parent_layout: QLayout, is_normed: bool = False) -> LabeledSlider:
        """
        Create a LabeledSlider widget with a label indicating its purpose.
        :param label_text: Text label indicating the slider's purpose.
        :param parent_layout: Parent layout.
        :param is_normed: True if the slider is normed, i.e., taking float values between 0.0 and 2.0.
                          If False, the slider takes integer values from 0 to 255.
        :return: QSlider or FloatSlider instance.
        """
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
    def _create_color_button(cls, label_text: str, parent_layout: QLayout) -> ColorButton:
        """
        Create a ColorButton widget with a label indicating its purpose.
        :param label_text: Label indicating the color button's purpose.
        :param parent_layout: Parent layout.
        :return: ColorButton instance.
        """
        layout = QHBoxLayout()
        label = QLabel(label_text)
        color_button = ColorButton(label=label_text)
        layout.addWidget(label)
        layout.addWidget(color_button)
        parent_layout.addLayout(layout)
        return color_button

    def _widget_get_value(self, key: Settings) -> object:
        """
        Extracts the value of the widget that is registered with a Settings.
        :param key: Settings key.
        :return: Value of the widget registered with the given settings key.
        """
        if isinstance(self._widgets[key], QCheckBox):  # checkboxes
            return self._widgets[key].isChecked()
        elif isinstance(self._widgets[key], (QSlider, FloatSlider, LabeledSlider)):  # sliders
            return self._widgets[key].value()
        elif isinstance(self._widgets[key], ColorButton):
            return self._widgets[key].color()
        else:
            LoggerSingleton().logger.log_warning(f"Cannot set value for undefined widget type "
                                                 f"{self._widgets[key].__class__.__name__}")
        return

    def _widget_set_value(self, key: Settings, value: object):
        """
        Sets a new value for the widget that is registered with a Settings.
        :param key: Settings key.
        :param value: New value for the widget.
        """
        if isinstance(self._widgets[key], QCheckBox):  # checkboxes
            self._widgets[key].setChecked(bool(value))
        elif isinstance(self._widgets[key], (QSlider, FloatSlider, LabeledSlider)):  # sliders
            self._widgets[key].setValue(value)
        elif isinstance(self._widgets[key], ColorButton):
            self._widgets[key].set_color(value)
        else:
            LoggerSingleton().logger.log_warning(f"Cannot set value for undefined widget type "
                                                 f"{self._widgets[key].__class__.__name__}")

    def _load_settings(self, settings_dict: dict[Settings, object] = None):
        """
        Loads the settings from a dictionary or from the global application settings.
        :param settings_dict: Dictionary of settings key-value pairs.
        """
        if settings_dict is None:  # take values from the global application settings
            for key in self._widgets.keys():
                self._widget_set_value(key, settings_get(key))
        else:
            for key, value in settings_dict.items():
                self._widget_set_value(key, value)

    def _save_settings(self):
        """
        Collects the settings from the dialog in a dictionary and accepts the dialog.
        """
        # Collect all settings in a dict
        updated_settings = {}

        for key in self._widgets.keys():
            updated_settings[key] = self._widget_get_value(key)

        self._updated_settings = updated_settings
        self.accept()

    def _restore_default(self):
        """
        Loads the default application settings and applies them to the widgets.
        """
        self._load_settings(settings_get_default_values())

    def exec(self) -> dict | None:
        """
        Executes the dialog in the main loop and returns the settings dict on accept, else None.
        :return: Settings dictionary if the dialog was accepted, else None.
        """
        super().exec()
        return self._updated_settings

    def reject(self):
        """
        Rejects the dialog, i.e., the internal settings dictionary is set to None.
        """
        self._updated_settings = None
        super().reject()
