from abc import ABC, abstractclassmethod, abstractmethod
import dataclasses  # for efficient access to classes containing mainly data
from shapely.geometry import Polygon  # for polygon operations such as area

from coordinate_manipulation import polygon_to_rectangle


@dataclasses.dataclass
class LineType:
    """
    This class collects all line types in the same format as found in the PageXML file.

    Attributes:
        DEPRECATED_DEFAULT_LINE (str): Not a standard type, but occurs in manuscript Pen450!

        DEFAULT (str): For main text lines.
        TITLE (str): For lines that contain chapter titles (though not necessarily exclusively).

        INTERLINEAR_LINE_GLOSS (str): For interlinear glosses.
        INTERCOLUMNAR_LINE_GLOSS (str): For intercolumnar glosses.
        MARGINAL_LINE_GLOSS (str): For marginal glosses.

        INTERLINEAR_LINE_CORRECTION (str): For interlinear glosses that are corrections.
        INTERLINEAR_LINE_ADDITION (str): For interlinear glosses that are additions.
        INTERLINEAR_LINE_SIGNE_DE_RENVOI (str): For interlinear glosses that are Signes de Renvoi.
        INTERLINEAR_LINE_NUMBER (str): For glosses above (ordinal) numbers that indicate the
                                       grammatical case.

        REFERENCE_SIGN (str): For glosses that are reference signs. Can occur both in the margin,
                              in interlinear spaces and even between words in the line.
    """
    DEPRECATED_DEFAULT_LINE: str = "DefaultLine"

    DEFAULT: str = "default"
    TITLE: str = "HeadingLine:title"

    INTERLINEAR_LINE_GLOSS: str = "InterlinearLine:gloss"
    INTERCOLUMNAR_LINE_GLOSS: str = "IntercolumnarLine:gloss"
    MARGINAL_LINE_GLOSS: str = "MarginalLine:gloss"

    INTERLINEAR_LINE_CORRECTION: str = "InterlinearLine:correction"
    INTERLINEAR_LINE_ADDITION: str = "InterlinearLine:addition"
    INTERLINEAR_LINE_SIGNE_DE_RENVOI: str = "InterlinearLine:signe_de_renvoi"
    INTERLINEAR_LINE_NUMBER: str = "InterlinearLine:number"

    REFERENCE_SIGN: str = "Reference_sign"


MAIN_TEXT_LINE_TYPES = [LineType.DEFAULT, LineType.DEPRECATED_DEFAULT_LINE, LineType.TITLE]


@dataclasses.dataclass
class RegionType:
    """
    In this class, all region zones are contained as denoted in the PageXML file.

    Attributes:
        MAIN_ZONE (str): For the main text zones.
        MAIN_ZONE_COLUMN_LEFT (str): In case of columnar writing, the left column zone.
        MAIN_ZONE_COLUMN_RIGHT (str): In case of columnar writing, the right column zone.
        MAIN_ZONE_INTERCOLUMNAR (str): In case of columnar_writing, the zone between columns.

        MARGIN_TEXT_ZONE_OUTER (str): The marginal space on the side opposite to the spine.
        MARGIN_TEXT_ZONE_INNER (str): The marginal space on the same side as the spine.
        MARGIN_TEXT_ZONE_UPPER (str): The marginal space on the upper side of the page.
        MARGIN_TEXT_ZONE_LOWER (str): The marginal space on the lower side of the page.

        NUMBERING_ZONE_PAGE (str): The space used for page numbering.
        NUMBERING_ZONE_FOLIO (str): The space used for folio numbering.
    """
    MAIN_ZONE: str = "MainZone"
    MAIN_ZONE_COLUMN_LEFT: str = "MainZone:column_left"
    MAIN_ZONE_COLUMN_RIGHT: str = "MainZone:column_right"
    MAIN_ZONE_INTERCOLUMNAR: str = "MainZone:intercolumnar"

    MARGIN_TEXT_ZONE_OUTER: str = "MarginTextZone:outer"
    MARGIN_TEXT_ZONE_INNER: str = "MarginTextZone:inner"
    MARGIN_TEXT_ZONE_UPPER: str = "MarginTextZone:upper"
    MARGIN_TEXT_ZONE_LOWER: str = "MarginTextZone:lower"

    NUMBERING_ZONE_PAGE: str = "NumberingZone:page"
    NUMBERING_ZONE_FOLIO: str = "NumberingZone:folio"


class PageObject(ABC):
    """
    Abstract base class PageObject defines objects that are on a manuscript page.
    This includes regions, gloss lines, main text lines, and main text words. This class provides an
    interface such that the connection data can be serialized and deserialized easily.

    When inheriting from PageObject, make sure to register the child class into the method `factory_from_dict`.

    Class Methods:
        factory_from_dict (dict):

    Abstract Methods:
        to_dict (list[str]): Stores the class state as a dictionary.
        to_minimal_string: Returns the minimal string representation of the class state.
        get_bounding_box: Returns the bounding box containing the object.

    Abstract Class Methods:
        from_dict (dict): Given the serialized output of method `to_dict`, this method restores the contents
                          of the saved class and returns the correct object.
    """

    @classmethod
    def factory_from_dict(cls, dictionary: dict):
        type_map = {
            "Region": Region,
            "MainTextLine": MainTextLine,
            "GlossLine": GlossLine,
            "Word": Word
        }
        if "classname" in dictionary:
            return type_map[dictionary["classname"]].from_dict(dictionary)
        raise ValueError("Restoring the class from the dictionary failed.")

    @abstractmethod
    def to_dict(self, ignored_keys: list[str] = ()) -> dict:
        """
        Stores the class state as a dictionary.
        When implementing this method, make sure that the returned dictionary has a key `"classname"`
        that agrees with the name of the child class.
        :param: ignored_keys: Keys that will be ignored and as such automatically returned as None.
        :raise: ValueError if restoring the class from the dictionary failed.
        :return: Dictionary containing the class state.
        """
        pass

    @abstractmethod
    def to_minimal_string(self) -> str:
        """
        Returns the minimal string representation of the class state.
        :return: Minimal string representation of the class state.
        """
        pass

    @abstractmethod
    def get_bounding_box(self) -> list[tuple[int, int]]:
        """
        Returns the bounding box containing the object.
        :return: Bounding box.
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        raise NotImplementedError("Use PageObject.factory_from_dict instead.")


@dataclasses.dataclass
class Region(PageObject):
    """
    This class serves as a wrapper for PageXML region properties and enables string representation.

    Attributes:
        page (METSPage): The METSPage instance containing the line.
        id (str): The id of the region.
        type (str): The type of the region.
        coordinates (Polygon): The polygon encircling the region.
        relative_area (float): The region's relative area (region area divided by page area).
        absolute_area (int): The regions absolute area in pixel.

    Class Methods:
        from_dict: Given the serialized output of method `to_dict`, this method restores the contents
                   of the saved class.

    Methods:
        to_dict (list[str]): Override. Stores the class state as a dictionary.
        to_minimal_string: Override. Returns a minimal string representation of the region.
        get_bounding_box: Override. Returns the bounding box containing the object.
    """
    def __init__(
            self,
            page: "METSPage",
            id: str,
            type: str,
            coordinates: Polygon,
            relative_area: float,
            absolute_area: int
    ):
        """
        Initializes the class Region.

        :param page: The METSPage instance containing the line.
        :param id: The id of the region.
        :param type: The type of the region.
        :param coordinates: The polygon encircling the region.
        :param relative_area: The region's relative area (region area divided by page area).
        :param absolute_area: The regions absolute area in pixel.
        """

        self.page = page
        self.id = id
        self.type = type
        self.coordinates = coordinates
        self.relative_area = relative_area
        self.absolute_area = absolute_area

    def __eq__(self, other):
        if not isinstance(other, Region):
            return False
        return self.page.pagexml_path == other.page.pagexml_path and self.id == other.id

    def __repr__(self) -> str:
        """
        The class's string representation.

        :return: String representation of the class.
        """
        return f"Region(id='{self.id}', type='{self.type}', coordinates='{self.coordinates}', relative_area={self.relative_area}, absolute_area={self.absolute_area})"

    def __str__(self) -> str:
        """
        The class's short string representation.

        :return: Short string representation of the class.
        """
        return f"Region(id='{self.id}', type='{self.type}')"

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        from xml_extraction import METSPage
        return cls(
            # account for the case when page data is removed for faster serialization in METSPage.to_dict
            page=METSPage.from_dict(
                dictionary["page"]
            ) if "page" in dictionary and dictionary["page"] is not None else None,
            id=dictionary["id"],
            type=dictionary["type"],
            coordinates=Polygon(dictionary["coordinates"]),
            relative_area=dictionary["relative_area"],
            absolute_area=dictionary["absolute_area"]
        )

    def to_dict(self, ignored_keys: list[str] = ()) -> dict:
        """
        Stores the class state as a dictionary.
        :param: ignored_keys: Keys that will be ignored and as such automatically returned as None.
        :return: Dictionary containing the class state.
        """
        return {
            "classname": "Region",
            "page": self.page.to_dict() if "page" not in ignored_keys else None,
            "id": self.id if "id" not in ignored_keys else None,
            "type": self.type if "type" not in ignored_keys else None,
            "coordinates": list(self.coordinates.exterior.coords) if "coordinates" not in ignored_keys else None,
            "relative_area": self.relative_area if "relative_area" not in ignored_keys else None,
            "absolute_area": self.absolute_area if "absolute_area" not in ignored_keys else None
        }

    def to_minimal_string(self) -> str:
        """
        Override. Returns a minimal string representation of the region.
        :return: Minimal string representation of the region.
        """
        return f"{self.type}"

    def get_bounding_box(self) -> list[tuple[int, int]]:
        """
        Override. Returns the bounding box containing the object.
        :return: Bounding box.
        """
        return polygon_to_rectangle(self.coordinates.exterior.coords)


@dataclasses.dataclass
class PageLine:
    """
    This class serves as a wrapper for PageXML line properties and enables string representation.

    Attributes:
        page (METSPage): The METSPage instance containing the line.
        id (str): The id of the text line.
        type (str): The type of the text line.
        coordinates (Polygon): The polygon encircling the text line.
        baseline (list): A list of points (w, h) determining the line's baseline.
        text (str): The text contained in the text line.
        words (list): The list of words contained in the text line.
        word_bounding_boxes (lines): The list of bounding boxes, each corresponding to a word in words.
        characters (list): The list of characters contained in the text line.
        character_bounding_boxes (lines): The list of bounding boxes, each corresponding to a character in characters.

    Class Methods:
        from_dict: Given the serialized output of method `to_dict`, this method restores the contents
                   of the saved class.

    Methods:
        to_dict (list[str]): Stores the class state as a dictionary.
        to_minimal_string(): Returns a minimal string representation of the main text line.
    """
    def __init__(
            self,
            page: "METSPage",
            id: str,
            type: str,
            coordinates: Polygon,
            baseline: list,
            text: str,
            words: list = None,
            word_bounding_boxes: list = None,
            characters: list = None,
            character_bounding_boxes: list = None
    ):
        """
        Initializes the class MainTextLine.

        :param page: The METSPage instance containing the line.
        :param id: The id of the main text line.
        :param type: The type of the main text line.
        :param coordinates: The polygon encircling the text line.
        :param baseline: The list of points (w, h) determining the line's baseline.
        :param text: The text contained in the text line.
        :param words: The list of words contained in the text line.
        :param word_bounding_boxes: The list of bounding boxes, each corresponding to a word in words.
        :param characters: The list of characters contained in the text line.
        :param character_bounding_boxes: The list of bounding boxes, each corresponding to a character in characters.
        """
        self.page = page
        self.id = id
        self.type = type
        self.coordinates = coordinates
        self.baseline = baseline
        self.text = text
        self.words = words
        self.word_bounding_boxes = word_bounding_boxes
        self.characters = characters
        self.character_bounding_boxes = character_bounding_boxes

    def __eq__(self, other):
        if not isinstance(other, PageLine):
            return False
        return self.page.pagexml_path == other.page.pagexml_path and self.id == other.id

    def __repr__(self) -> str:
        """
        The class's string representation.

        :return: String representation of the class.
        """
        return (f"TextLine(id='{self.id}',"
                f"type='{self.type}',"
                f"coordinates='{self.coordinates}',"
                f"baseline={self.baseline},"
                f"text={self.text},"
                f"words={self.words},"
                f"word_bounding_boxes={self.word_bounding_boxes}"
                f"characters={self.characters},"
                f"character_bounding_boxes={self.character_bounding_boxes})")

    def __str__(self) -> str:
        """
        The class's short string representation.

        :return: Short string representation of the class.
        """
        return f"PageLine(id='{self.id}', type='{self.type}, text='{self.text}')"

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        from xml_extraction import METSPage
        return cls(
            # account for the case when page data is removed for faster serialization in METSPage.to_dict
            page=METSPage.from_dict(
                dictionary["page"]
            ) if "page" in dictionary and dictionary["page"] is not None else None,
            id=dictionary["id"],
            type=dictionary["type"],
            coordinates=Polygon(dictionary["coordinates"]),
            baseline=dictionary["baseline"],
            text=dictionary["text"],
            words=dictionary["words"],
            word_bounding_boxes=dictionary["word_bounding_boxes"],
            characters=dictionary["characters"],
            character_bounding_boxes=dictionary["character_bounding_boxes"]
        )

    def to_dict(self, ignored_keys: list[str] = ()) -> dict:
        """
        Stores the class state as a dictionary.
        :param: ignored_keys: Keys that will be ignored and as such automatically returned as None.
        :return: Dictionary containing the class state.
        """
        return {
            "page": self.page.to_dict() if "page" not in ignored_keys else None,
            "id": self.id if "id" not in ignored_keys else None,
            "type": self.type if "type" not in ignored_keys else None,
            "coordinates": list(self.coordinates.exterior.coords) if "coordinates" not in ignored_keys else None,
            "baseline": self.baseline if "baseline" not in ignored_keys else None,
            "text": self.text if "text" not in ignored_keys else None,
            "words": self.words if "words" not in ignored_keys else None,
            "word_bounding_boxes": self.word_bounding_boxes if "word_bounding_boxes" not in ignored_keys else None,
            "characters": self.characters if "characters" not in ignored_keys else None,
            "character_bounding_boxes": self.character_bounding_boxes if "character_bounding_boxes" not in ignored_keys else None,
        }

    def to_minimal_string(self) -> str:
        return f"PageLine({self.type}, '{self.text}')"


class MainTextLine(PageLine):
    """
    This class serves as a wrapper for PageXML main text line properties and enables string representation.

    Class Methods:
        from_dict: Override. Given the serialized output of method `to_dict`, this method restores the contents
                   of the saved class.

    Methods:
        to_dict: Override. Stores the class state as a dictionary.
        to_minimal_string(): Override. Returns a minimal string representation of the main text line.
    """
    def __repr__(self) -> str:
        """
        The class's string representation.

        :return: String representation of the class.
        """
        return (f"MainTextLine(id='{self.id}',"
                f"type='{self.type}',"
                f"coordinates='{self.coordinates}',"
                f"baseline={self.baseline},"
                f"text={self.text},"
                f"words={self.words},"
                f"word_bounding_boxes={self.word_bounding_boxes}"
                f"characters={self.characters},"
                f"character_bounding_boxes={self.character_bounding_boxes})")

    def __str__(self) -> str:
        """
        The class's short string representation.

        :return: Short string representation of the class.
        """
        return f"MainTextLine(id='{self.id}', type='{self.type}, text='{self.text}')"

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        return super().from_dict(dictionary)

    def to_dict(self, ignored_keys: list[str] = ()) -> dict:
        """
        Stores the class state as a dictionary.
        :param: ignored_keys: Keys that will be ignored and as such automatically returned as None.
        :return: Dictionary containing the class state.
        """
        dictionary = super().to_dict(ignored_keys=ignored_keys)
        dictionary["classname"] = "MainTextLine"
        return dictionary

    def to_minimal_string(self) -> str:
        return f"MainTextLine({self.type}, '{self.text}')"


class GlossLine(PageLine, PageObject):
    """
    This class serves as a wrapper for PageXML gloss text line properties and enables string representation.

    Class Methods:
        from_dict: Override. Given the serialized output of method `to_dict`, this method restores the contents
                   of the saved class.

    Methods:
        to_dict: Override. Stores the class state as a dictionary.
        to_minimal_string: Override. Returns a minimal string representation of the gloss line.
        get_bounding_box: Override. Returns the bounding box containing the object.
    """
    def __repr__(self) -> str:
        """
        The class's string representation.

        :return: String representation of the class.
        """
        return (f"GlossLine(id='{self.id}',"
                f"type='{self.type}',"
                f"coordinates='{self.coordinates}',"
                f"baseline={self.baseline},"
                f"text={self.text},"
                f"words={self.words},"
                f"word_bounding_boxes={self.word_bounding_boxes}"
                f"characters={self.characters},"
                f"character_bounding_boxes={self.character_bounding_boxes})")

    def __str__(self) -> str:
        """
        The class's short string representation.

        :return: Short string representation of the class.
        """
        return f"GlossLine(id='{self.id}', type='{self.type}, text='{self.text}')"

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        return super().from_dict(dictionary)

    def to_dict(self, ignored_keys: list[str] = ()) -> dict:
        """
        Stores the class state as a dictionary.
        :param: ignored_keys: Keys that will be ignored and as such automatically returned as None.
        :return: Dictionary containing the class state.
        """
        dictionary = super().to_dict(ignored_keys=ignored_keys)
        dictionary["classname"] = "GlossLine"
        return dictionary

    def to_minimal_string(self) -> str:
        """
        Override. Returns a minimal string representation of the gloss line.
        :return: Minimal string representation.
        """
        return f"Gloss({self.type}, '{self.text}')"

    def get_bounding_box(self) -> list[tuple[int, int]]:
        """
        Override. Returns the bounding box containing the object.
        :return: Bounding box.
        """
        return polygon_to_rectangle(self.coordinates.exterior.coords)


@dataclasses.dataclass
class Word(PageObject):
    """
    Class Word encapsulates a single main text word, which is identified by a MainTextLine and the
    index of the word inside the line.

    Attributes:
        line (MainTextLine): The main text line to which the word belongs.
        word_idx (int): The index of the word inside the line.

    Properties:
        id (str): The TEI ID of the word.
        bounding_box (list[tuple[int, int]]): The bounding box of the word.
        type (str): Always returns "Word".
        text (str): Returns the text contained in the word.

    Class Methods:
        from_dict: Override. Given the serialized output of method `to_dict`, this method restores the contents
                   of the saved class.

    Methods:
        to_dict: Override. Stores the class state as a dictionary.
        to_minimal_string: Override. Returns a minimal string representation of the gloss line.
        get_bounding_box: Override. Returns the bounding box containing the object.
    """
    def __init__(self, line: MainTextLine, word_idx: int):
        """
        Initializes an instance of the Word class.

        :param line: The main text line to which the word belongs.
        :param word_idx: The index of the word inside the line.
        """
        self.line = line
        self.word_idx = word_idx

    def __str__(self):
        return f"Word(text={self.line.words[self.word_idx]})"

    def __eq__(self, other):
        return self.line.id == other.line.id and self.word_idx == other.word_idx

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        return Word(
            # Account for the case when the _ProgramState deserializes with removing redundant data
            line=MainTextLine.from_dict(
                dictionary["line"]
            ) if "line" in dictionary and dictionary["line"] is not None else None,
            word_idx=dictionary["word_idx"]
        )

    def to_dict(self, ignored_keys: list[str] = ()) -> dict:
        """
        Stores the class state as a dictionary.
        :param: ignored_keys: Keys that will be ignored and as such automatically returned as None.
        :return: Dictionary containing the class state.
        """
        return {
            "classname": "Word",
            "line": self.line.to_dict() if "line" not in ignored_keys else None,
            "word_idx": self.word_idx if "word_idx" not in ignored_keys else None,
        }

    def to_minimal_string(self):
        """
        Override. Returns a minimal string representation of the word.
        :return: Minimal string representation.
        """
        return f"Word('{self.text}')"

    def get_bounding_box(self) -> list[tuple[int, int]]:
        """
        Override. Returns the bounding box containing the object.
        :return: Bounding box.
        """
        return self.bounding_box

    @property
    def id(self) -> str:
        return get_line_word_id(self.line, self.word_idx)

    @property
    def bounding_box(self) -> list[tuple[int, int]]:
        return self.line.word_bounding_boxes[self.word_idx]

    @property
    def type(self) -> str:
        return "Word"

    @property
    def text(self) -> str:
        return self.line.words[self.word_idx]


def get_line_word_id(line: MainTextLine, word_idx: int) -> str:
    """
    Given a MainTextLine and a word index, returns the TEI ID of the word.

    :param line: MainTextLine to which the word belongs.
    :param word_idx: Word index inside the main text line.
    :return: TEI ID of the word.
    """
    return f"{line.id}_word_{word_idx}"


def gloss_line_id_to_tei_id(gloss: GlossLine):
    """
    Given a GlossLine, returns the TEI ID of it.

    :param gloss: GlossLine whose index should be returned.
    :return: TEI ID of the gloss line.
    """
    return f"{gloss.id}_gloss"


def gloss_tei_id_to_id(tei_id: str):
    """
    Given a gloss TEI ID, returns the line ID.

    :param tei_id: Gloss TEI ID.
    :return: Gloss line id.
    """
    return tei_id.replace("_gloss", "")