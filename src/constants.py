from enum import Enum

class Constants(str, Enum):
    """
    Enum for constants.
    """
    ORGANIZATION = "GlossIT"
    APPLICATION = "GlossIT Gloss Connector"
    DOMAIN = "https://glossit.uni-graz.at"

    #METS_SCHEMA = "./schemas/mets.xsd"
    #TEI_SCHEMA = None  # TODO "./schemas/tei.xsd"

    PROJECT_FILE_EXTENSION = "glp"