from enum import Enum

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor


class SettingsKey(str, Enum):
    """
    Enum for application settings keys.
    """
    GEOMETRY = "geometry"                               # Main window geometry (QByteArray)
    WINDOW_STATE = "windowState"                        # Main window state (QByteArray)

    DEBUG_ENABLED = "debugEnabled"                      # True if detailed debug logging is activated (bool)

    ### Image Options ###
    IMAGE_BRIGHTNESS = "imageBrightness"                # Displayed manuscript image brightness, value between 0 and 2
    IMAGE_CONTRAST = "imageContrast"                    # Displayed manuscript image contrast, value between 0 and 2
    IMAGE_SATURATION = "imageSaturation"                # Displayed manuscript image saturation, value between 0 and 2

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


def settings_set(key: SettingsKey, value: object) -> None:
    """
    Sets the settings value for the given key.
    :param key: Settings key.
    :param value: Settings value to set.
    """
    if isinstance(value, QColor):
        value = value.name(QColor.NameFormat.HexArgb)
    _get_settings().setValue(key, value)


def settings_get(key: SettingsKey) -> object:
    """
    Returns the settings value for the given key.
    :param key: Settings key.
    :return: The settings value for the given key.
    """
    value = _get_settings().value(key)
    if key in {
        SettingsKey.ARROW_FILL,
        SettingsKey.MAIN_WORD_FILL,
        SettingsKey.MAIN_WORD_TEXT,
        SettingsKey.REFERENCE_SIGN_FILL,
        SettingsKey.REFERENCE_SIGN_TEXT,
        SettingsKey.GLOSS_FILL,
        SettingsKey.GLOSS_TEXT,
    }:
        if value is not None:
            return QColor(value)
        else:
            return QColor(255, 255, 255, 255)
    if key == SettingsKey.DEBUG_ENABLED:
        return value in [True, 'true', 'True', 1, '1']
    if key in {
        SettingsKey.FILL_TRANSPARENCY,
        SettingsKey.TEXT_TRANSPARENCY,
        SettingsKey.SELECTION_TRANSPARENCY,
    }:
        try:
            return int(value)
        except Exception:
            return 255
    if key in {
        SettingsKey.IMAGE_BRIGHTNESS,
        SettingsKey.IMAGE_CONTRAST,
        SettingsKey.IMAGE_SATURATION,
    }:
        try:
            return float(value)
        except Exception:
            return 1.
    return value


def settings_get_default_values() -> dict:
    """
    Returns a dict of default values for settings keys.
    :return: Dict of default settings.
    """
    return {
        SettingsKey.DEBUG_ENABLED: False,

        SettingsKey.IMAGE_BRIGHTNESS: 0.6,
        SettingsKey.IMAGE_CONTRAST: 1.0,
        SettingsKey.IMAGE_SATURATION: 1.0,

        SettingsKey.FILL_TRANSPARENCY: 48,
        SettingsKey.TEXT_TRANSPARENCY: 100,
        SettingsKey.SELECTION_TRANSPARENCY: 80,

        SettingsKey.ARROW_FILL: QColor(0, 0, 0),
        SettingsKey.MAIN_WORD_FILL: QColor(153, 153, 153),
        SettingsKey.MAIN_WORD_TEXT: QColor(255, 255, 255),
        SettingsKey.REFERENCE_SIGN_FILL: QColor(0, 114, 178),
        SettingsKey.REFERENCE_SIGN_TEXT: QColor(255, 255, 255),
        SettingsKey.GLOSS_FILL: QColor(230, 159, 0),
        SettingsKey.GLOSS_TEXT: QColor(255, 255, 255),
    }

def settings_revert_to_default_values():
    """
    Reverts all settings values to their default values.
    :return:
    """
    for key, default_value in settings_get_default_values().items():
        settings_set(key, default_value)
