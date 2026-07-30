import builtins
from enum import Enum

from PySide6.QtCore import QSettings, QByteArray
from PySide6.QtGui import QColor

from constants import Constants


class Setting:
    """
    Class Setting stores setting properties.

    Attributes:
        key (str): The key under which the setting is stored.
        type (builtins.type): The type of the setting.
        default_value (object): The default value of the setting.
        menu_name (str | None): Name of the menu tab the setting should appear in.
        display_name (str | None): The name under which the setting should be displayed.
    """
    def __init__(
            self,
            key: str, t: builtins.type, default_value: object = None, menu_name: str = None, display_name: str = None
    ):
        self.key: str = key
        self.type: builtins.type = t
        self.default_value: object = default_value
        self.menu_name: str | None = menu_name
        self.display_name: str = display_name if display_name is not None else key


class Settings(Setting, Enum):
    """
    Enum for application settings keys.
    """
    GEOMETRY = ("geometry", QByteArray)                 # Main window geometry (QByteArray)
    WINDOW_STATE = ("windowState", QByteArray)          # Main window state (QByteArray)

    ### Image Options ###
    IMAGE_BRIGHTNESS = (                                # Displayed image brightness, value between 0 and 2
        "imageBrightness", float, 0.6, "Image", "Image Brightness"
    )
    IMAGE_CONTRAST = (                                  # Displayed image contrast, value between 0 and 2
        "imageContrast", float, 1.0, "Image", "Image Contrast"
    )
    IMAGE_SATURATION = (                                # Displayed image saturation, value between 0 and 2
        "imageSaturation", float, 1.0, "Image", "Image Saturation"
    )

    FILL_TRANSPARENCY = (                               # The alpha value (between 0 and 255) of the box filling (int)
        "fillTransparency", int, 48, "Image", "Fill Opacity"
    )
    TEXT_TRANSPARENCY = (                               # The alpha value (between 0 and 255) of the text color (int)
        "textTransparency", int, 100, "Text Opacity"
    )
    SELECTION_TRANSPARENCY = (                          # The alpha value (between 0 and 255) of current selection (int)
        "selectionTransparency", int, 80, "Selection Opacity"
    )

    ### Color Scheme ###
    ARROW_FILL = (                                      # Arrows are drawn with this color (QColor)
        "arrowFill", QColor, QColor(0, 0, 0), "Color", "Arrow Fill"
    )
    MAIN_WORD_FILL = (                                  # Main text word boxes are filled with this color (QColor)
        "mainWordFill", QColor, QColor(153, 153, 153), "Color", "Main Word Fill"
    )
    MAIN_WORD_TEXT = (                                  # Main text word texts are drawn with this color (QColor)
        "mainWordFont", QColor, QColor(255, 255, 255), "Color", "Main Word Text"
    )
    REFERENCE_SIGN_FILL = (                             # Reference signs boxes are filled with this color (QColor)
        "referenceSignFill", QColor, QColor(0, 114, 178), "Color", "Reference Sign Fill"
    )
    REFERENCE_SIGN_TEXT = (                             # Reference signs texts are drawn with this color (QColor)
        "referenceSignFont", QColor, QColor(255, 255, 255), "Color", "Reference Sign Text"
    )
    GLOSS_FILL = (                                      # Gloss boxes are filled with this color (QColor)
        "glossFill", QColor, QColor(230, 159, 0), "Color", "Gloss Fill"
    )
    GLOSS_TEXT = (                                      # Gloss texts are drawn with this color (QColor)
        "glossFont", QColor, QColor(255, 255, 255), "Color", "Gloss Text"
    )

    ### Advanced Options ###
    DEBUG_ENABLED = (                                   # True if detailed debug logging is activated (bool)
        "debugEnabled", bool, False, "Advanced", "Enable debug logging"
    )


def _get_settings() -> QSettings:
    """
    Returns the applications current user-specific settings (as opposed to project-specific
    properties that are saved in the project files). This includes window positioning, font colors, etc.
    Do not use this function directly, it is recommended to use settings_get and settings_set instead!

    :return: QSettings instance.
    """
    return QSettings(Constants.ORGANIZATION, Constants.APPLICATION)


def settings_set(setting: Settings, value: object) -> None:
    """
    Sets the settings value.
    :param setting: Setting to modify.
    :param value: Settings value to set.
    """
    if isinstance(value, QColor):
        value = value.name(QColor.NameFormat.HexArgb)
    _get_settings().setValue(setting.key, value)


def settings_get(setting: Settings) -> object:
    """
    Returns the settings value.
    :param setting: Setting to return.
    :return: The settings value.
    """
    value = _get_settings().value(setting.key)

    if issubclass(setting.type, QColor):
        if value is not None:
            return QColor(value)
        else:
            return QColor(255, 255, 255, 255)
    elif issubclass(setting.type, bool):
        return value in [True, 'true', 'True', 1, '1']
    elif issubclass(setting.type, int):
        try:
            return int(value)
        except ValueError:
            return 255
    elif issubclass(setting.type, float):
        try:
            return float(value)
        except ValueError:
            return 1.
    else:
        return value


def settings_revert_to_default_values():
    """
    Reverts all settings values to their default values.
    """
    for setting in Settings:
        settings_set(setting, setting.default_value)


def settings_get_default_values():
    """
    Returns a dict of all settings default values.
    :return: Settings default values.
    """
    return {
        setting: setting.default_value for setting in Settings if setting.default_value is not None
    }