from enum import Enum

import qdarkstyle
from PyQt5.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor


class SettingsKey(str, Enum):
    """
    Enum for application settings keys.
    """
    GEOMETRY = "geometry"                               # Main window geometry (QByteArray)
    WINDOW_STATE = "windowState"                        # Main window state (QByteArray)

    DARK_THEME_ENABLED = "darkThemeEnabled"             # True if the dark visual theme is enabled (boolean)

    ### Colors and Display Options ###
    FILL_TRANSPARENCY = "fillTransparency"              # The alpha value (between 0 and 255) of the box filling (int)
    TEXT_TRANSPARENCY = "textTransparency"              # The alpha value (between 0 and 255) of the text color (int)
    SELECTION_TRANSPARENCY = "selectionTransparency"    # The alpha value (between 0 and 255) of the current
                                                        #   selection (int)
    ARROW_FILL = "arrowFill"                            # Arrows are drawn with this color (QColor)
    MAIN_WORD_FILL = "mainWordFill"                     # Main text word boxes are filled with this color (QColor)
    MAIN_WORD_TEXT = "mainWordFont"                     # Main text word texts are drawn with this color (QColor)
    REFERENCE_SIGN_FILL = "referenceSignFill"           # Reference signs boxes are filled with this color (QColor)
    REFERENCE_SIGN_TEXT = "referenceSignFont"           # Reference signs texts are drawn with this color (QColor)
    GLOSS_FILL = "glossFill"                            # Gloss boxes are filled with this color (QColor)
    GLOSS_TEXT = "glossFont"                            # Gloss texts are drawn with this color (QColor)


def _get_settings() -> QSettings:
    """
    Returns the applications current user-specific settings (as opposed to project-specific
    properties that are saved in the project files). This includes window positioning, font colors, etc.
    Do not use this function directly, it is recommended to use settings_get and settings_set instead!

    :return: QSettings instance.
    """
    return QSettings("GlossIT", "GlossIT Gloss Connector")


def settings_get(key: SettingsKey) -> object:
    """
    Returns the settings value for the given key.
    :param key: Settings key.
    :return: The settings value for the given key.
    """
    return _get_settings().value(key)


def settings_set(key: SettingsKey, value: object) -> None:
    """
    Sets the settings value for the given key.
    :param key: Settings key.
    :param value: Settings value to set.
    """
    _get_settings().setValue(key, value)


def settings_revert_to_default_values():
    """
    Reverts all settings values to their default values.
    :return:
    """
    settings_set(SettingsKey.DARK_THEME_ENABLED, True)

    settings_set(SettingsKey.FILL_TRANSPARENCY, 48)
    settings_set(SettingsKey.TEXT_TRANSPARENCY, 100)
    settings_set(SettingsKey.SELECTION_TRANSPARENCY, 80)

    settings_set(SettingsKey.ARROW_FILL, QColor(0, 0, 0, 255))
    settings_set(SettingsKey.MAIN_WORD_FILL, QColor(255, 0, 0, 255))
    settings_set(SettingsKey.MAIN_WORD_TEXT, QColor(255, 255, 255, 255))
    settings_set(SettingsKey.REFERENCE_SIGN_FILL, QColor(0, 0, 128, 255))
    settings_set(SettingsKey.REFERENCE_SIGN_TEXT, QColor(20, 20, 255, 255))
    settings_set(SettingsKey.GLOSS_FILL, QColor(0, 128, 0, 255))
    settings_set(SettingsKey.GLOSS_TEXT, QColor(20, 255, 20, 255))


def settings_apply_theme(app: QApplication):
    """
    Applies the app theme.

    :param app: QApplication instance.
    """
    if settings_get(SettingsKey.DARK_THEME_ENABLED):
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
    else:
        app.setStyleSheet("")

