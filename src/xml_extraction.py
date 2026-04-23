from bs4 import BeautifulSoup  # XML manipulation
import difflib  # matching strings
import io
import lxml.etree as ET  # for applying XSLT transformations
import numpy as np  # matrix manipulation
import os  # access to file system etc.
from PIL import Image  # load images
from kraken.containers import BaselineLine
from saxonche import PySaxonProcessor  # xslt transformations
from shapely.geometry import Polygon  # for polygon operations such as area
import tqdm  # print for loop as progress bar

# Kraken OCR
import kraken
from kraken.lib import models, xml
from kraken import rpred

from coordinate_manipulation import polygon_to_rectangle, divide_rectangle_into_equal_parts
from glossit_dataclasses import Region, MainTextLine, LineType, GlossLine, PageObject, MAIN_TEXT_LINE_TYPES


def apply_xslt_transformation(mets_path, xslt_path) -> BeautifulSoup:
    """
    This function takes the path to the METS file and the path to the XSLT transformation
    and returns the BeautifulSoup object that contains the XSLT transformation of the METS.

    :param mets_path: Path to the METS as exported from eScriptorium.
    :param xslt_path: Path to the TEI XSLT transformation.
    :return: BeautifulSoup of the transformed METS.
    """
    previous_path = os.getcwd()
    try:
        os.chdir(os.path.dirname(xslt_path))

        proc = PySaxonProcessor(license=False)

        with open(xslt_path, "r", encoding="utf-8") as file_handle:
            raw_xslt = file_handle.readlines()
            # filter out the xsl:result-document tags, but preserve nodes below it
            filtered_xslt = "".join([line for line in raw_xslt if "xsl:result-document" not in line])

        xsltproc = proc.new_xslt30_processor()
        document = proc.parse_xml(xml_file_name=mets_path)
        executable = xsltproc.compile_stylesheet(stylesheet_text=filtered_xslt)
        output = executable.transform_to_string(xdm_node=document)

        os.chdir(previous_path)  # change to previous CWD
        return BeautifulSoup(output, features="xml")
    except Exception as e:  # in case anything goes wrong, change back to current CWD
        print(e)
        os.chdir(previous_path)


class METSBook:
    """
    Class METSBook is an interface that reads in an eScriptorium METS file, possibly containing many pages, and allows
    access to the individual pages (stored as METSPage).

    Attributes:
        mets_path (str): Path to the METS file as exported from eScriptorium.
        tei_path (str): Path to the TEI transformation of the METS file. Needed for connecting glosses.
        number_of_pages (int): The number of pages contained in the METS.
        tei (BeautifulSoup): The BeautifulSoup of the XSLT-transformed METS.
        pages (list[METSPage]): The individual METSPages contained in the METSBook.
        is_double_page (bool): True indicates that the manuscript book contains only double pages,
                               i.e., one image contains two pages. If None is provided, the type is
                               inferred automatically.
        ocr_model_path (str): Path to the Kraken OCR model.

    Methods:
        to_dict (tqdm.tqdm, list[dict]): Stores the class state as a dictionary.
        construct_mets: Constructs a new METSFile where the images and PageXML files follow a numbering like 0001.xml.

    Class Methods:
        from_dict (dict, tqdm.tqdm): Given the serialized output of method `to_dict`, this method restores the contents
                                     of the saved class.

    Private Class Methods:
        _get_number_of_pages (str): This helper method takes the path to the METS file extracts the number of
                                    pages in the METS.
        _determine_if_double_page (list[METSPage]): Helper method that determines if the METSBook contains double pages.
    """
    def __init__(
            self,
            mets_path: str,
            tei_path: str = None,
            is_double_page = None,
            ocr_model_path: str = None,
            verbose: bool = False,
            tqdm_progress: tqdm.tqdm = None
    ):
        """
        Initializes an instance of class METSBook.

        :param mets_path: Path to the METS file as exported from eScriptorium.
        :param tei_path: Path to the TEI transformation of the METS file. Needed for connecting glosses.
        :param is_double_page: True indicates that the manuscript book contains only double pages,
        :param ocr_model_path: Path to the Kraken OCR model.
        :param verbose (bool): If True, print a tqdm progress bar for reading in each page.
                               This is especially useful if you have many pages and have
                               provided an ocr_model_path.
        :param tqdm_progress (tqdm.tqdm): A tqdm progress bar for tracking METSBook construction process.
        """
        self.mets_path = os.path.abspath(mets_path)

        self.tei_path = os.path.abspath(tei_path) if tei_path else None
        self.ocr_model_path = os.path.abspath(ocr_model_path) if ocr_model_path else None
        self.number_of_pages = self._get_number_of_pages(self.mets_path)

        if self.tei_path is not None:  # only set the tei member if a path was provided
            with open(self.tei_path, "r") as file:
                self.tei = BeautifulSoup(file.read(), features="xml")
        else:
            self.tei = None

        self.pages = []
        if tqdm_progress is not None:
            tqdm_progress.iterable = range(self.number_of_pages)
            tqdm_progress.total = self.number_of_pages
            tqdm_progress.reset()
        else:
            tqdm_progress = tqdm.tqdm(range(self.number_of_pages), disable=not verbose)
        if verbose:
            print("\nGetting word coordinates for each page:")
        for page_idx in tqdm_progress:
            self.pages.append(METSPage(
                    mets_path=self.mets_path,
                    tei_path=self.tei_path,
                    page_idx=page_idx,
                    ocr_model_path=self.ocr_model_path,
                    tei=self.tei,
                )
            )

        self.is_double_page = is_double_page if is_double_page else self._determine_if_double_page(self.pages)
        for page in self.pages:
            page.is_double_page = self.is_double_page

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} "
                f"mets_path={self.mets_path}, "
                f"tei_path={self.tei_path}, "
                f"ocr_model_path={self.ocr_model_path}, "
                f"number_of_pages={self.number_of_pages}, "
                f"pages={self.pages}, "
                f"is_double_page={self.is_double_page}>")

    def __len__(self) -> int:
        """
        Returns the number of pages in the METSBook.

        :return: Number of pages in the METSBook.
        """
        return self.number_of_pages

    def __getitem__(self, item: int) -> "METSPage":
        """
        Retrieves the METSPage with index item.
        :param item: page index
        :return: METSPage with index item.
        """
        return self.pages[item]

    def __iter__(self):
        return iter(self.pages)

    def to_dict(self, tqdm_progress: tqdm.tqdm, objects_cache: list[dict] | None = None) -> dict:
        """
        Stores the class state as a dictionary.
        :param tqdm_progress: A tqdm progress bar for tracking METSBook construction process.
        :param objects_cache: A list of to_dict results for each METSPage._objects for faster serialization.
        :return: Dictionary containing the class state.
        """
        pages = []

        if tqdm_progress is not None:
            tqdm_progress.iterable = self.pages
            tqdm_progress.total = self.number_of_pages
            tqdm_progress.reset()
        else:
            tqdm_progress = self.pages

        for page_idx, page in enumerate(tqdm_progress):
            cached = objects_cache[page_idx] if objects_cache is not None else None
            dictionary = page.to_dict(objects_cache=cached)
            dictionary["tei"] = None  # We don't need to store TEI data as it is handled by METSBook in this case
            pages.append(dictionary)

        return {
            "mets_path": self.mets_path,
            "tei_path": self.tei_path,
            "number_of_pages": self.number_of_pages,
            "is_double_page": self.is_double_page,
            "ocr_model_path": self.ocr_model_path,

            "tei": str(self.tei),
            "pages": pages,
        }

    def construct_mets(self) -> BeautifulSoup:
        """
        Constructs a new METSFile where the images and PageXML files follow a numbering like 0001.xml.
        :return: BeautifulSoup of a METS.xml.
        """

        # 1) Construct fileSec
        fileGrp_image = '<fileGrp USE="image">'
        for page_idx, _ in enumerate(self.pages):
            image_id = f"{page_idx:04d}"
            fileGrp_image += f'<file ID="image{page_idx}">'
            fileGrp_image += f'<FLocat xlink:href="{image_id}.jpg"/>'
            fileGrp_image += '</file>'
        fileGrp_image += '</fileGrp>'

        fileGrp_export = '<fileGrp USE="export">'
        for page_idx, _ in enumerate(self.pages):
            xml_id = f"{page_idx:04d}"
            fileGrp_export += f'<file ID="export{page_idx}">'
            fileGrp_export += f'<FLocat xlink:href="{xml_id}.xml"/>'
            fileGrp_export += '</file>'
        fileGrp_export += '</fileGrp>'

        fileSec = f'{fileGrp_image}{fileGrp_export}'

        # 2) Construct structMap
        structMap = '<div TYPE="document">'
        for page_idx, _ in enumerate(self.pages):
            structMap += f'<div TYPE="page">'
            structMap += f'<fptr FILEID="image{page_idx}"/>'
            structMap += f'<fptr FILEID="export{page_idx}"/>'
            structMap += '</div>'
        structMap += '</div>'

        # 3) Merge data
        mets_string = '<mets xmlns="http://www.loc.gov/METS/" xmlns:xlink="http://www.w3.org/1999/xlink">'
        mets_string += f'<fileSec>{fileSec}</fileSec>'
        mets_string += f'<structMap TYPE="physical">{structMap}</structMap>'
        mets_string += '</mets>'

        return BeautifulSoup(mets_string, features="xml")

    @classmethod
    def from_dict(cls, dictionary: dict, tqdm_progress: tqdm.tqdm = None):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :param tqdm_progress: A tqdm progress bar for tracking METSBook construction process.
        :return: A class instance with its state defined by the serialized input data.
        """
        instance = cls.__new__(cls)

        instance.mets_path = dictionary["mets_path"]
        instance.tei_path = dictionary["tei_path"]
        instance.number_of_pages = dictionary["number_of_pages"]
        instance.is_double_page = dictionary["is_double_page"]
        instance.ocr_model_path = dictionary["ocr_model_path"]

        instance.tei = BeautifulSoup(dictionary["tei"], features="xml")

        if tqdm_progress is not None:
            tqdm_progress.iterable = dictionary["pages"]
            tqdm_progress.total = len(dictionary["pages"])
            tqdm_progress.reset()
        else:
            tqdm_progress = dictionary["pages"]

        pages = []
        for page_dict in tqdm_progress:
            page_dict["tei"] = None  # remove TEI data, since it will be provided later
            mets_page = METSPage.from_dict(page_dict)
            mets_page.tei = instance.tei  # here, TEI data is provided
            pages.append(mets_page)
        instance.pages = pages

        return instance

    @classmethod
    def _get_number_of_pages(cls, mets_path: str) -> int:
        """
        This helper method takes the path to the METS file extracts the number of pages in the METS.

        :param mets_path: Path to the METS file as exported from eScriptorium.
        :return: The number of METS pages.
        """
        with open(mets_path, "rb") as f:
            tree = ET.parse(f)
            root = tree.getroot()
            namespaces = {
                'mets': 'http://www.loc.gov/METS/',
                'xlink': 'http://www.w3.org/1999/xlink'
            }

            page_counter = 0
            for structMap in root.findall('mets:structMap', namespaces):
                for div in structMap.findall('mets:div', namespaces):
                    for subDiv in div.findall('mets:div', namespaces):
                        page_counter += 1
        return page_counter

    @classmethod
    def _determine_if_double_page(cls, pages: list["METSPage"]) -> bool:
        """
        Helper method that determines if the METSBook contains double pages.

        :param pages: List of METSPages.
        :return: True if the METSBook contains double pages.
        """
        all_duplicate_regions = []
        for page in pages:
            duplicate_regions = {}
            for region in page.get_regions():
                if region.type not in duplicate_regions:
                    duplicate_regions[region.type] = 0
                duplicate_regions[region.type] += 1
            all_duplicate_regions += list(duplicate_regions.values())

        if np.median(all_duplicate_regions) == 2:  # if most regions appeared twice
            return True
        else:
            return False


class METSPage:
    """
    Class METSPage provides an easy interface to work with eScriptorium METS outputs
    on a page-to-page basis.

    It allows access to PageXML data, image data, and TEI transformations
    of the provided METS file. In this class, the contents of one tag
    enclosed under `<div TYPE="page">`.

    In addition, it allows for the extraction of all regions, main text lines and gloss
    lines. If an additional path to a Kraken OCR model is provided, the main text lines
    and the gloss lines are furthermore returned with ground truth line annotation as
    extracted from the PageXML data, Kraken OCR outputs, and reconstructed character-level
    and word-level bounding boxes.

    Attributes:
        mets_path (str): Path to the METS file as exported from eScriptorium.
        tei_path (str): Path to the TEI transformation of the METS file. Needed for connecting glosses.
        page_idx (int): The page index of the <div TYPE="page"> element that is used
                        for constructing the current page.
        pagexml_path (str): Path to the PageXML extracted from METS.
        pagexml (BeautifulSoup): The contents of the PageXML file.
        image_path (str): Path to the image extracted from METS.
        sorted_pagexml_lines (list[BaselineLineWrapper]): List of all lines found in the PageXML.
        pageimg (PIL.ImageFile.ImageFile): PIL Image as read from image_path.
        tei (BeautifulSoup): BeautifulSoup wrapper around the TEI file.
        is_double_page (bool): True indicates that the manuscript book contains only double pages,
                               i.e., one image contains two pages.
        ocr_model_path (str): Path to the Kraken OCR model.
        ocr_model (models.TorchSeqRecognizer): The loaded OCR model from ocr_model_path.

    Private Attributes:
        _ocr_predictions (OCRPredictionWrapper): The OCR prediction wrapper for the page.
        _objects (dict[str, Region | GlossLine | MainTextLine]): Dictionary to map object keys to objects.

    Class Methods:
        from_dict: Given the serialized output of method `to_dict`, this method restores the
                   contents of the saved class.

    Methods:
        to_dict (dict | None, list[str]): Stores the class state as a dictionary.
        get_object_from_id(str): This method checks if an id corresponds to an object and returns it.
        get_regions: Extracts and returns the regions of the PageXML content.
        get_main_text_lines: Extracts and returns the main text lines of the PageXML content.
        get_gloss_lines: Extracts and returns the gloss lines of the PageXML content.
        replace_pagexml (str, str): Replaces the METSPage OCR data, TEI data, and object data with the contents of
                                    another PageXML, TEI, and OCR model.
                                    Important: The provided PageXML data must refer to the same pageimg as the old
                                               METSPage! Only the OCR data, TEI data, and object data are updated.
                                    Usecase: Errors have been found in the PageXML and have been corrected manually.

    Private Methods:
        _update_pagexml_lines (kraken.lib.xml.XMLPage): Updates the internal region and line data according to the
                                                        contents of the provided PageXML data.
        _update_ocr_predictions (kraken.lib.xml.XMLPage): Updates the internal OCR predictions according to the
                                                          contents of the provided PageXML data.
        _get_properties_from_line(str): Given a line id, get some basic properties of the line.
        _get_ocr_from_line(str): Given a line id, get some OCR properties of the line.

    Private Class Methods:
        _construct_objects(list): Builds a dictionary that maps object ids to the corresponding objects.
        _load_pagexml(str): Given a path to a PageXML file, load it into a Kraken PageXML object and
                            apply necessary preprocessing steps.
        _is_main_text_line(kraken.containers.BaselineLine): Check whether a line is a valid main text line.
        _is_gloss_line(kraken.containers.BaselineLine): Check whether a line is a valid gloss line.
        _get_pagexml_and_image_paths(str): A private helper method for retrieving the
                                           PageXML and image paths from METS.
    """

    def __init__(self,
                 mets_path: str,
                 page_idx: int,
                 tei_path: str = None,
                 ocr_model_path: str = None,
                 tei: BeautifulSoup = None,
                 is_double_page: bool = False):
        """
        Initializes the class METSPage.

        :param mets_path: Path to the METS file as exported from eScriptorium.
        :param page_idx: The page index of the <div TYPE="page"> element that is used
                         for constructing the current page.
        :param tei_path: Path to the TEI transformation of the METS file. Needed for connecting glosses.
        :param ocr_model_path: Path to the Kraken OCR model to use.
        :param tei: BeautifulSoup wrapper around the TEI file.
                    Use this parameter when constructing the METSPage from a METSBook,
                    since in this case, the TEI has already been read in.
        :param is_double_page: True indicates that the manuscript book contains only double pages,
                               i.e., one image contains two pages.
        """
        self.mets_path = os.path.abspath(mets_path)
        self.tei_path = os.path.abspath(tei_path) if tei_path else None
        self.page_idx = page_idx
        self.pagexml_path, self.image_path = self._get_pagexml_and_image_paths(self.mets_path, self.page_idx)

        self.pagexml = None
        with open(self.pagexml_path, 'r') as file:
                self.pagexml = BeautifulSoup(file, 'xml')

        pagexml = self._load_pagexml(self.pagexml_path)  # Kraken PageXML wrapper
        self._update_pagexml_lines(pagexml=pagexml)
        self.pageimg = Image.open(self.image_path)

        if tei_path is not None:  # Only apply a transformation if a path was provided
            if tei is not None:  # if we have a tei provided, use it
                self.tei = tei
            else:  # otherwise, read in the TEI
                with open(self.tei_path, 'r') as file:
                    self.tei = BeautifulSoup(file, 'xml')
        else:
            self.tei = None

        self.is_double_page = is_double_page

        # construct the OCR predictions if a path to a model is provided
        self.ocr_model_path = os.path.abspath(ocr_model_path) if ocr_model_path else None
        self._ocr_predictions = None

        if self.ocr_model_path:
            self._update_ocr_predictions(pagexml=pagexml)

        # Construct index of all objects
        self._objects = self._construct_objects(
            self.get_regions() + self.get_main_text_lines() + self.get_gloss_lines()
        )

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} "
                f"mets_path={self.mets_path} "
                f"tei_path={self.tei_path} "
                f"page_idx={self.page_idx} "
                f"pagexml_path={self.pagexml_path} "
                f"image_path={self.image_path} "
                f"ocr_model_path={self.ocr_model_path} "
                f"is_double_page={self.is_double_page}>")

    def to_dict(self, objects_cache: dict | None = None, ignored_keys: list[str] = ()) -> dict:
        """
        Stores the class state as a dictionary.
        :param objects_cache: The to_dict result of current METSPage._objects for faster serialization.
        :param: ignored_keys: Keys that will be ignored and as such automatically returned as None.
                              Warning! These keys are not propagated to calls of to_dict() on child objects!
        :return: Dictionary containing the class state.
        """

        # remove data that can be inferred later
        objects = None
        if "_objects" not in ignored_keys:
            # remove data that can be inferred later
            if objects_cache is None:
                objects = {}
                for key, value in self._objects.items():
                    # We need to remove this information before serialization to make it run faster (and not exceed
                    #  maximum recursions)
                    dictionary = value.to_dict(ignored_keys=["page"])

                    class_name = dictionary["classname"]
                    if class_name in ("Region", "MainTextLine", "GlossLine"):
                        del dictionary["page"]
                    objects[key] = dictionary
            else:
                objects = objects_cache

        return {
            "mets_path": self.mets_path if "mets_path" not in ignored_keys else None,
            "tei_path": self.tei_path if "tei_path" not in ignored_keys else None,
            "page_idx": self.page_idx if "page_idx" not in ignored_keys else None,
            "pagexml_path": self.pagexml_path if "pagexml_path" not in ignored_keys else None,
            "image_path": self.image_path if "image_path" not in ignored_keys else None,
            "is_double_page": self.is_double_page if "is_double_page" not in ignored_keys else None,
            "ocr_model_path": self.ocr_model_path if "ocr_model_path" not in ignored_keys else None,

            "sorted_pagexml_lines": [line.to_dict() for line in
                                     self.sorted_pagexml_lines] if "sorted_pagexml_lines" not in ignored_keys else None,
            "pageimg": image_to_bytestring(self.pageimg) if "pageimg" not in ignored_keys else None,
            "tei": str(self.tei) if "tei" not in ignored_keys else None,
            "pagexml": str(self.pagexml) if "pagexml" not in ignored_keys else None,
            "_ocr_predictions": self._ocr_predictions.to_dict() if "_ocr_predictions" not in ignored_keys else None,
            "_objects": objects if "_objects" not in ignored_keys else None
        }

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents
                          of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        instance = cls.__new__(cls)
        instance.mets_path = dictionary["mets_path"]
        instance.tei_path = dictionary["tei_path"]
        instance.page_idx = dictionary["page_idx"]
        instance.pagexml_path = dictionary["pagexml_path"]
        instance.image_path = dictionary["image_path"]
        instance.is_double_page = dictionary["is_double_page"]
        instance.ocr_model_path = dictionary["ocr_model_path"]

        instance.sorted_pagexml_lines = [BaselineLineWrapper.from_dict(d) for d in dictionary["sorted_pagexml_lines"]]
        instance.pageimg = bytestring_to_image(dictionary["pageimg"])
        instance.pagexml = BeautifulSoup(dictionary["pagexml"], "xml") if dictionary["pagexml"] else None

        # only create tei object if provided (it won't be provided to save performance when called from METSBook object)
        instance.tei = BeautifulSoup(dictionary["tei"], "xml") if dictionary["tei"] is not None else None
        instance._ocr_predictions = OCRPredictionWrapper.from_dict(dictionary["_ocr_predictions"])

        objects = {}
        for key, value_dict in dictionary["_objects"].items():
            objects[key] = PageObject.factory_from_dict(value_dict)
            if isinstance(objects[key], (Region, MainTextLine, GlossLine)):
                objects[key].page = instance  # link the page info that was removed in the serialization step

        instance._objects = objects

        return instance

    def get_object_from_id(self, id: str):
        """
        This method checks if an id corresponds to an object and returns it.

        :param id: The id of the object to look up.
        :raises ValueError: If an object id is invalid.
        :return: The object corresponding to the id.
        """
        try:
            return self._objects[id]
        except Exception as e:
            raise ValueError(f"Error, no object with id '{id}' was found in the PageXML.")

    def get_regions(self) -> list["Region"]:
        """
        This method returns the individual regions extracted out of the PageXML content of this page.

        :return: Regions extracted from the PageXML content.
        """
        total_area = self.pageimg.height * self.pageimg.width

        # Attention: Do not use
        # 'for region_type, region in BaselineLine(...).regions.items():'
        # since the Kraken XMLPage wrapper discards multiple regions
        # of the same type due to saving it as a dict.
        # For double-page images (such as in Ang477), we need
        # all regions!

        def coord_string_to_list(coord_string: str) -> list[tuple[int, int]]:
            """
            Takes a string of coordinates in the form '1733,387 1705,387 1676,385' and maps it to a list of
            coordinate tuples [(1733, 387), (1705, 387), (1676, 385)].

            :param coord_string: Coordinate string.
            :return: List of coordinate tuples.
            """
            individuals = coord_string.split(" ")
            coord_list = [(int(entry.split(",")[0]), int(entry.split(",")[1])) for entry in individuals]
            return coord_list

        with open(self.pagexml_path, "rb") as f:
            tree = ET.parse(f)

            regions = []
            for r in tree.findall(".//{*}TextRegion"):
                region_id = r.get("id")
                try:
                    region_type = r.get("custom").split(" ")[1][6:-2]  # looks like 'structure {type:MarginTextZone:lower;}'
                except Exception:  # if we can't split the string, or it is too short
                    region_type = None

                try:
                    region_coords = coord_string_to_list(r.find("{*}Coords").get("points"))
                except (AttributeError, IndexError):
                    region_coords = None

                regions.append(
                    Region(
                        page=self,
                        id=region_id,
                        type=region_type,
                        coordinates=Polygon(region_coords),
                        relative_area=Polygon(region_coords).area / total_area,
                        absolute_area=int(Polygon(region_coords).area)
                    )
                )

        return regions

    def get_main_text_lines(self) -> list["MainTextLine"]:
        """
        This method returns the individual main text lines extracted out of the PageXML content of this page.

        :return: Main text lines extracted from the PageXML content.
        """
        line_ids = [entry.id for entry in self.sorted_pagexml_lines if self._is_main_text_line(entry)]

        output = []
        for line_id in line_ids:  # make sure the line has actual contents
            line_properties = self._get_properties_from_line(line_id)

            if self.ocr_model_path:
                ocr = self._get_ocr_from_line(line_id)
                if ocr is not None:
                    output.append(MainTextLine(
                        page=self,
                        id=line_id,
                        type=line_properties["type"],
                        coordinates=Polygon(line_properties["region"]),
                        baseline=line_properties["baseline"],
                        text=line_properties["text"],
                        words=ocr["words"],
                        word_bounding_boxes=ocr["word_bounding_boxes"],
                        characters=ocr["characters"],
                        character_bounding_boxes=ocr["character_bounding_boxes"],
                    ))
            else:
                output.append(MainTextLine(
                    page=self,
                    id=line_id,
                    type=line_properties["type"],
                    coordinates=Polygon(line_properties["region"]),
                    baseline=line_properties["baseline"],
                    text=line_properties["text"]
                ))

        return output

    def get_gloss_lines(self) -> list["GlossLine"]:
        """
        This method returns the individual gloss lines extracted out of the PageXML content of this page.

        :return: Gloss lines extracted from the PageXML content.
        """
        gloss_ids = [entry.id for entry in self.sorted_pagexml_lines if self._is_gloss_line(entry)]

        output = []

        for line_id in gloss_ids:  # make sure the line has actual contents
            line_properties = self._get_properties_from_line(line_id)

            if self.ocr_model_path:
                ocr = self._get_ocr_from_line(line_id)
                if ocr is not None:
                    output.append(GlossLine(
                        page=self,
                        id=line_id,
                        type=line_properties["type"],
                        coordinates=Polygon(line_properties["region"]),
                        baseline=line_properties["baseline"],
                        text=line_properties["text"],
                        words=ocr["words"],
                        word_bounding_boxes=ocr["word_bounding_boxes"],
                        characters=ocr["characters"],
                        character_bounding_boxes=ocr["character_bounding_boxes"],
                    ))
            else:
                output.append(GlossLine(
                    page=self,
                    id=line_id,
                    type=line_properties["type"],
                    coordinates=Polygon(line_properties["region"]),
                    baseline=line_properties["baseline"],
                    text=line_properties["text"]
                ))
        return output

    def replace_pagexml(self, pagexml_path: str, tei_path: str, ocr_model_path: str):
        """
        Replaces the METSPage OCR data, TEI data, and object data with the contents of another PageXML, TEI, and OCR
        model.
        Important: The provided PageXML data must refer to the same pageimg as the old METSPage!
                   Only the OCR data, TEI data, and object data are updated.
        Usecase: Errors have been found in the PageXML and have been corrected manually.

        :param pagexml_path: Path to the new PageXML.
        :param tei_path: Path to the new TEI. It must be congruent to the whole METSBook if the page is part of a
                         METSBook.
        :param ocr_model_path: Path to the new OCR model.
        :return:
        """
        with open(tei_path, "r") as file_handle:
            tei = BeautifulSoup(file_handle.read(), features="xml")
        with open(pagexml_path, "r") as file_handle:
            pagexml = BeautifulSoup(file_handle.read(), features="xml")

        self.tei_path = tei_path
        self.tei = tei
        self.pagexml_path = pagexml_path
        self.pagexml = pagexml
        self.ocr_model_path = ocr_model_path

        self._update_pagexml_lines()
        self._update_ocr_predictions()
        self._objects = self._construct_objects(
            self.get_regions() + self.get_main_text_lines() + self.get_gloss_lines()
        )

    def _update_pagexml_lines(self, pagexml: kraken.lib.xml.XMLPage = None):
        """
        Updates the internal region and line data according to the contents of the provided PageXML data.
        :param pagexml: PageXML data.
        :return:
        """
        if pagexml is None:
            pagexml = self._load_pagexml(self.pagexml_path)  # Kraken PageXML wrapper
        self.sorted_pagexml_lines = [
            BaselineLineWrapper(line) for line in pagexml.get_sorted_lines()
        ]

    def _update_ocr_predictions(self, pagexml: kraken.lib.xml.XMLPage = None):
        """
        Updates the internal OCR predictions according to the contents of the provided PageXML data.
        :param pagexml: PageXML data.
        """
        if pagexml is None:
            pagexml = self._load_pagexml(self.pagexml_path)  # Kraken PageXML wrapper
        ocr_model = models.load_any(self.ocr_model_path)
        self._ocr_predictions = OCRPredictionWrapper(ocr_model, self.pageimg, pagexml)

    def _get_properties_from_line(self, line_id: str) -> dict:
        """
        This helper function takes the (unique) line id as exported by eScriptorium and returns some
        line properties such as the line type, the contained text annotation, the baseline contour,
        and the region area defined by a polygon.

        :param line_id: The (unique) line identifier.
        :raises KeyError: in case the line_id could not be found in the pagexml data.
        :return: A dictionary of properties for the requested line.
        """
        all_lines = self.sorted_pagexml_lines
        for line in all_lines:
            if line.id == line_id:
                line_type = line.tags["type"][0]["type"]

                return {
                    "type": line_type,
                    "text": line.text,
                    "baseline": line.baseline,
                    "region": line.boundary
                }
        raise KeyError(f"No TextLine with id='{line_id}' found in pagexml")

    def _get_ocr_from_line(self, line_id: str) -> dict | None:
        """
        Given a unique line identifier and a Kraken OCR model, calculate the bounding boxes of the
        individual words in the ground truth text extracted from the line. If there are no points in
        the line region, None is returned.

        The type of the line, the ground truth words of the line and their bounding boxes are then returned
        as a dictionary.

        :param line_id: The unique line identifier.
        :return: A dict containing the ground truth words and bounding boxes.
        """
        def brute_approximate(gt_string: str, ocr_r: list[tuple[int, int]]):
            # We get the whole line region polygon and approximate it by a rectangle!
            rectangle = polygon_to_rectangle(ocr_r)
            # Now, divide the rectangle into as many equal-width pieces as we have characters in the ground truth
            # string
            chars = list(gt_string)
            length = len(chars)
            if length < 1:
                length = 1
            character_bbs = divide_rectangle_into_equal_parts(
                rectangle,
                num_parts=length
            )
            return chars, character_bbs

        def group_by_words(gt_words: list[str], character_bbs: list(list[tuple[int, int]])):
            ground_truth_coords_grouped = []
            char_idx = 0
            for word in gt_words:
                word_length = len(word)
                ground_truth_coords_grouped.append(character_bbs[char_idx:(char_idx + word_length)])
                char_idx += word_length
            return ground_truth_coords_grouped

        line_properties = self._get_properties_from_line(line_id)

        # 0) Check if there is a valid polygon, otherwise return None
        if line_properties["region"] is None:
            return None

        # i) Ground truth data extraction and preprocessing.
        ground_truth_text = line_properties["text"]
        # remove leading and trailing spaces, and compress consecutive spaces to one space before splitting
        ground_truth_words = ground_truth_text.strip().replace("  ", " ").split(" ")
        ground_truth_string = "".join(
            ground_truth_words).lower()  # remove spaces and all lowercase for matching with OCR output

        # ii) Get Kraken prediction.
        ocr_prediction = self._ocr_predictions.get_line_prediction(line_id)
        ocr_prediction = remove_spaces_from_ocr_prediction(ocr_prediction)

        # also make text all lowercase
        ocr_string, ocr_coords = ocr_prediction["text"].lower(), ocr_prediction["coords"]

        matcher = difflib.SequenceMatcher(None, ocr_string, ground_truth_string)
        prediction_fit = matcher.quick_ratio()
        alignment = matcher.get_opcodes()

        if len(ground_truth_string) == 1:  # some line with only one ground truth character must be a single word
            # we get the whole line region polygon and approximate it by a rectangle
            ocr_region = line_properties["region"]
            word_bounding_boxes = [polygon_to_rectangle(ocr_region)]
            characters = ground_truth_words  # since we only have one character in one word
            character_bounding_boxes = word_bounding_boxes  # since we only have one word
        else:
            # iii) Match Kraken output with ground truth annotation.
            # iii) a) First, calculate the coordinates from matching each character in the ground truth string with the
            # ocr string
            if len(ocr_string) and prediction_fit > 0.8:  # We have some good kraken output, so let's match!
                character_bounding_boxes_temp = [None] * len(ground_truth_string)
                for action in alignment:
                    action_type, ocr1, ocr2, gt1, gt2 = action
                    if action_type in ("equal", "replace"):
                        for gt_idx, ocr_idx in zip(range(gt1, gt2), range(ocr1, ocr2)):
                            character_bounding_boxes_temp[gt_idx] = ocr_coords[ocr_idx]

                # in case some characters could not be matched, remove those
                characters = []
                character_bounding_boxes = []
                for char, bb in zip(ground_truth_string, character_bounding_boxes_temp):
                    characters.append(char)
                    character_bounding_boxes.append(bb)
            else:  # oh no, Kraken has not found anything of value... so let's approximate the letter positions
                ocr_region = line_properties["region"]
                characters, character_bounding_boxes = brute_approximate(ground_truth_string, ocr_region)

            # iii) b) Second, group the ground truth coordinates according to the words
            ground_truth_coords_grouped = group_by_words(ground_truth_words, character_bounding_boxes)
            # If we find a whole word without any coordinates, this is bad,
            # so we make the brute approximation instead.
            for group in ground_truth_coords_grouped:
                if group == [None] * len(group):
                    ocr_region = line_properties["region"]
                    characters, character_bounding_boxes = brute_approximate(ground_truth_string, ocr_region)
                    ground_truth_coords_grouped = group_by_words(ground_truth_words, character_bounding_boxes)
                    break

            # iv) Then, combine the character bounding boxes for each word.
            word_bounding_boxes = []
            for points in ground_truth_coords_grouped:
                points = [point for point in points if point]  # exclude characters without bounding box
                word_min_x = np.inf
                word_max_x = 0
                word_top_y = 0
                word_bottom_y = 0
                for point in points:
                    top_left, top_right, bottom_right, bottom_left = point
                    word_min_x = min(top_left[0], word_min_x)
                    word_max_x = max(top_right[0], word_max_x)
                    word_top_y += top_left[1] / len(points)
                    word_bottom_y += bottom_left[1] / len(points)

                word_bounding_boxes.append([
                    (word_min_x, word_top_y),
                    (word_max_x, word_top_y),
                    (word_max_x, word_bottom_y),
                    (word_min_x, word_bottom_y)
                ])

        # only append the characters for which a bounding box could be identified
        return_characters = []
        return_bounding_boxes = []
        for char, bb in zip(characters, character_bounding_boxes):
            if bb is not None:
                return_characters.append(char)
                return_bounding_boxes.append(bb)
        characters = return_characters
        character_bounding_boxes = return_bounding_boxes

        return {
            "words": ground_truth_words,
            "word_bounding_boxes": word_bounding_boxes,
            "characters": characters,
            "character_bounding_boxes": character_bounding_boxes,
        }

    @classmethod
    def _construct_objects(
            self,
            l: list[Region | MainTextLine | GlossLine]
    ) -> dict[str, Region | MainTextLine | GlossLine]:
        """
        Builds a dictionary that maps object ids to the corresponding objects.

        :param l: list of Region, MainTextLine, GlossLine objects that should be indexed
        :return: A dictionary.
        """
        dictionary = {}
        for object in l:
            dictionary[object.id] = object

        return dictionary

    @classmethod
    def _load_pagexml(cls, pagexml_path: str) -> kraken.lib.xml.XMLPage:
        """
        Given a path to a PageXML file, load it into a Kraken PageXML object and
        apply necessary preprocessing steps.

        :param pagexml_path: The path to a PageXML file.
        :return: The Kraken XMLPage object.
        """
        xml_object = xml.XMLPage(pagexml_path)

        # IMPORTANT
        # Let's traverse all lines and check if they are assigned a type.
        # If not, assign them the default type. This step is very important,
        # because otherwise, Kraken OCR will raise an exception and cannot
        # perform the OCR.
        all_lines = xml_object.get_sorted_lines()
        for line in all_lines:
            try:
                line_type = line.tags["type"][0]["type"]
            except KeyError:  # in this case the line type was not assigned or assigned incorrectly
                line_type = LineType.DEFAULT
                line.tags = {"type": [{"type": line_type}], "structure": [{"type": line_type}]}

        return xml_object

    @classmethod
    def _is_main_text_line(cls, entry: kraken.containers.BaselineLine):
        """
        For a Kraken BaselineLine entry (from XMLPage object), check if it is a valid main text line.

        :param entry: A Kraken BaselineLine entry
        :return: True if the line is a valid text line and a main text line.
        """
        if entry.text is not None:  # lines must contain some text
            if "structure" in entry.tags:  # lines with structure tag must have the correct type
                # text lines only have these two possibilities
                return entry.tags["structure"][0]["type"] in MAIN_TEXT_LINE_TYPES
            else:  # some text lines come without structure tag
                return True
        else:
            return False

    @classmethod
    def _is_gloss_line(cls, entry: kraken.containers.BaselineLine):
        """
        For a Kraken BaselineLine entry (from XMLPage object), check if it is a valid gloss line.

        :param entry: A Kraken BaselineLine entry
        :return: True if the line is a valid text line and a gloss line.
        """
        if entry.text is not None:  # lines must contain some text
            if "structure" in entry.tags:  # lines with structure tag must have the correct type
                # text lines only have these two possibilities
                return entry.tags["structure"][0]["type"] not in MAIN_TEXT_LINE_TYPES
            else:  # lines without structure tag cannot be glosses
                return False
        else:
            return False

    @classmethod
    def _get_pagexml_and_image_paths(cls, mets_path: str, page_idx: int) -> tuple[str, str]:
        """
        This helper method takes the path to the METS file and extracts the PageXML and image paths.

        :param mets_path: Path to the METS file as exported from eScriptorium.
        :return: The path to the PageXML and the image as a tuple
        """
        with open(mets_path, "rb") as f:
            tree = ET.parse(f)
            root = tree.getroot()
            namespaces = {
                'mets': 'http://www.loc.gov/METS/',
                'xlink': 'http://www.w3.org/1999/xlink'
            }

            file_dict = {}
            for fileSec in root.findall('mets:fileSec', namespaces):
                for fileGrp in fileSec.findall('mets:fileGrp', namespaces):
                    for file in fileGrp.findall('mets:file', namespaces):
                        flocat = file.find('mets:FLocat', namespaces)
                        if flocat is not None:
                            file_dict[file.get('ID')] = flocat.get('{http://www.w3.org/1999/xlink}href')

            pages = []
            for structMap in root.findall('mets:structMap', namespaces):
                for div in structMap.findall('mets:div', namespaces):
                    for subDiv in div.findall('mets:div', namespaces):
                        page_contents = {}
                        for fptr in subDiv.findall('mets:fptr', namespaces):
                            current_content = file_dict[fptr.get('FILEID')]
                            if current_content.split(".")[-1].lower() == "xml":
                                page_contents["pagexml_path"] = current_content
                            elif current_content.split(".")[-1].lower() in ["jpg", "jpeg"]:
                                page_contents["image_path"] = current_content
                        pages.append(page_contents)

        try:
            return (
                os.path.abspath(os.path.join(os.path.dirname(mets_path), pages[page_idx]["pagexml_path"])),
                os.path.abspath(os.path.join(os.path.dirname(mets_path), pages[page_idx]["image_path"]))
            )
        except IndexError as e:
            print(e)
            print(f"Page index {page_idx} out of range. The METS file you provided has less entries.")


class BaselineLineWrapper:
    """
    BaselineLineWrapper wraps the contents of kraken.containers.BaselineLine in a way that is serializable.

    Class Methods:
        from_dict: Given the serialized output of method `to_dict`, this method restores the
                   contents of the saved class.

    Methods:
        to_dict: Stores the class state as a dictionary.
    """

    def __init__(self, line: BaselineLine):
        """
        Initialize the BaselineLineWrapper class.
        :param line: The baseline line to be contained in the class.
        """
        self.id = line.id
        self.baseline = line.baseline
        self.boundary = line.boundary
        self.text = line.text
        self.type = line.type
        self.base_dir = line.base_dir
        self.imagename = line.imagename
        self.tags = line.tags
        self.split = line.split
        self.regions = line.regions

    def to_dict(self):
        """
        Stores the class state as a dictionary.
        :return: Dictionary containing the class state.
        """
        return {
            "id": self.id,
            "baseline": self.baseline,
            "boundary": self.boundary,
            "text": self.text,
            "type": self.type,
            "base_dir": self.base_dir,
            "imagename": self.imagename,
            "tags": self.tags,
            "split": self.split,
            "regions": self.regions,
        }

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        line = kraken.containers.BaselineLine(
            id = dictionary["id"],
            baseline = dictionary["baseline"],
            boundary = dictionary["boundary"],
            text = dictionary["text"],
            type = dictionary["type"],
            base_dir = dictionary["base_dir"],
            imagename = dictionary["imagename"],
            tags = dictionary["tags"],
            split = dictionary["split"],
            regions = dictionary["regions"]
        )
        return cls(line)


class OCRPredictionWrapper:
    """
    OCRPredictionWrapper is a class that stores the Kraken OCR predictions for a whole page.

    Attributes:
        prediction (dict): Dictionary storing the prediction results.

    Class Methods:
        from_dict: Given the serialized output of method `to_dict`, this method restores the
                   contents of the saved class.

    Methods:
        to_dict: Stores the class state as a dictionary.
        get_line_prediction(line_id):
            Given a unique line identifier line_id, this method returns the ocr_prediction
            associated with it.
    """
    def __init__(self, ocr_model: models.TorchSeqRecognizer, pageimg: Image.Image, pagexml: kraken.lib.xml.XMLPage):
        """
        Initializes the OCRPredictionWrapper class with the Kraken OCR model and the
        manuscript page to be processed.

        :param ocr_model: The OCR model to use.
        :param pageimg: The manuscript page image.
        :param pagexml: The manuscript page xml data as exported by eScriptorium.
        """

        # we need to make a list out of the generator so the states persist and are not lost during iteration
        raw_prediction = rpred.rpred(ocr_model, im=pageimg, bounds=pagexml.to_container())

        self.prediction = {
            record.id: {
                "text": record.prediction,
                "coords": cuts_to_bounding_boxes(record)
            }
            for record in raw_prediction
        }

    def to_dict(self) -> dict:
        """
        Stores the class state as a dictionary.
        :return: Dictionary containing the class state.
        """
        return {"prediction": self.prediction}

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        instance = cls.__new__(cls)
        instance.prediction = dictionary["prediction"]
        return instance

    def get_line_prediction(self, line_id: str) -> dict:
        """
        This method takes a Kraken OCR prediction model and returns the predicted text and
        the character bounding boxes of a single line, identified by the line_id.

        :param line_id: The unique line identifier.
        :raises KeyError: in case the line_id could not be found in the pagexml data.
        :return: The predicted text and bounding boxes for all OCR prediction characters
                 in this line.
        """
        if line_id in self.prediction:
            return self.prediction[line_id]
        raise KeyError(f"No TextLine with id='{line_id}' found in xmlpage")


def cuts_to_bounding_boxes(record: kraken.containers.ocr_record) -> list:
    """
    This function takes the Kraken OCR records and calculates bounding boxes for individual
    characters from them.

    Kraken OCR does not return character bounding boxes for the predicted text, but instead
    cuts, or in other words, separators between the individual characters. However, when a
    prediction consisting of n characters is returned, the number of cuts is also n instead
    of the full number of cuts n+1. This is due to the fact that the cut after the last
    character is not returned.

    Each individual cut is an axis-aligned rectangle [p1, p2, p3, p4] of zero width.

    :param record: Kraken OCR record output for a single line.
    :return: The bounding boxes for all OCR prediction characters.
    """
    cuts = record.cuts + tuple([[record.baseline[-1]] * 4])
    bounding_boxes = []
    for idx in range(len(cuts) - 1):
        # Top, left, and bottom coordinates are taken from the left cut.
        # Therefore, additionally supplying the rightmost baseline
        # coordinate extended to a 4-tuple is feasible.
        top = cuts[idx][0][1]
        bottom = cuts[idx][1][1]
        left = cuts[idx][1][0]
        right = cuts[idx + 1][1][0]
        bounding_boxes.append((
            [left, top],
            [right, top],
            [right, bottom],
            [left, bottom]
        ))
    return bounding_boxes


def remove_spaces_from_ocr_prediction(ocr_prediction: dict) -> dict:
    """
    This function removes spaces and corresponding bounding boxes from the Kraken
    OCR output.

    :param ocr_prediction: OCR prediction as yielded by the function get_ocr_prediction.
    :return: OCR prediction in the same format but without spaces.
    """
    ocr_text, ocr_coords = ocr_prediction["text"], ocr_prediction["coords"]

    new_text = ""
    new_coords = []

    for char, coord in zip(ocr_text, ocr_coords):
        if char != " ":
            new_text += char
            new_coords.append(coord)

    return {"text": new_text, "coords": new_coords}


def image_to_bytestring(image: Image.Image) -> bytes:
    """
    Given a PIL Image object, returns a bytestring of its compressed JPEG contents.
    :param image: PIL Image to store as bytes.
    :return: Bytestring of compressed JPEG.
    """
    byte_io = io.BytesIO()
    image.save(byte_io, format='JPEG', quality=60)
    byte_io.seek(0)
    return byte_io.read()


def bytestring_to_image(bytestring: bytes) -> Image.Image:
    """
    Given a bytestring of an image file, returns a PIL Image object.
    :param bytestring: Bytestring of an image file.
    :return: PIL Image object.
    """
    byte_io = io.BytesIO(bytestring)
    byte_io.seek(0)
    image = Image.open(byte_io)
    image.load()
    return image