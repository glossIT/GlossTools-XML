import os
import pytest

from ..xml_extraction import METSBook


CACHE = {}


@pytest.fixture
def clean_mets_book():
    """
    This returns a METSBook of a dataset entry that does not contain any connection information in the TEI
    :return: The clean METSBook
    """
    if "clean_mets_book" in CACHE:
        return CACHE["clean_mets_book"]

    CACHE["clean_mets_book"] = METSBook(
        mets_path=os.path.join(os.path.dirname(__file__), "test_data", "clean_xml", "METS.xml"),
        tei_path=os.path.join(os.path.dirname(__file__), "test_data", "clean_xml", "first.xml"),
        ocr_model_path=os.path.join(os.path.dirname(__file__), "test_data", "model.mlmodel")
    )
    return CACHE["clean_mets_book"]