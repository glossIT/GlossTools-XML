from enum import Enum


class StringConstants(str, Enum):
    """
    Enum for string constants.
    """
    ORGANIZATION = "GlossIT"                    # Organization name
    APPLICATION = "GlossIT Gloss Connector"     # Application name
    DOMAIN = "https://glossit.uni-graz.at"      # Organization domain

    #METS_SCHEMA = "./schemas/mets.xsd"
    #TEI_SCHEMA = None  # TODO "./schemas/tei.xsd"

    PROJECT_FILE_EXTENSION = "glp"              # Project file extension


class IntConstants(int, Enum):
    """
    Enum for int constants.
    """
    MAX_UNDO_REDO_STEPS = 5                     # Maximum number of undo/redo steps
    MAX_LENGTH_RECENTLY_OPENED_FILES = 10       # Maximum number of displayed files in "Open Recent..." menu