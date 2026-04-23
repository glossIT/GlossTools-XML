import os
import pickle

from glossit_connect_glosses import ConnectedPair, GlossOnPageConnector
from glossit_dataclasses import Word
from xml_extraction import METSBook, METSPage


def quick_build_pair(page: METSPage, line_id_start: str, line_id_end: str) -> ConnectedPair:
    """
    Given two line IDs (one corresponding to the start and one to the end of the connected pair),
    this function returns a ConnectedPair with the correct start and end objects. This works on
    gloss lines only, it does not work on words.

    :param page: METSPage on which the objects to be connected are found.
    :param line_id_start: Line ID of the start object.
    :param line_id_end: Line ID of the end object.
    :return: ConnectedPair with corresponding start and end objects.
    """
    return ConnectedPair(page.get_object_from_id(line_id_start), page.get_object_from_id(line_id_end))


def quick_build_chain(page: METSPage, id_list: list[str]) -> list[ConnectedPair]:
    """
    Given a list of GlossLine IDs (id_1, id_2, ..., id_n), this function constructs a list of ConnectedPair that looks
    like
    [
        ConnectedPair(start=id_1, end=id_2),
        ConnectedPair(start=id_2, end=id_3),
        ...,
        ConnectedPair(start=id_n-1, end=id_n)
    ],
    where each ConnectedPair is constructed with the correct objects as corresponding to their line ID.

    :param page: METSPage on which the objects to be connected are found.
    :param id_list: List of GlossLine IDs.
    :return: A list of ConnectedPair constructed to reflect the ordering found in the id_list.
    """
    cycle = []
    for idx in range(len(id_list) - 1):
        cycle.append(quick_build_pair(page, id_list[idx], id_list[idx + 1]))
    return cycle


if __name__ == "__main__":
    if not os.path.exists("temp.pkl"):
        book = METSBook(
            mets_path=os.path.join(os.path.dirname(__file__), "tests", "test_data", "clean_xml", "METS.xml"),
            tei_path=os.path.join(os.path.dirname(__file__), "tests", "test_data", "clean_xml", "first.xml"),
            ocr_model_path=os.path.join(os.path.dirname(__file__), "tests", "test_data", "model.mlmodel")
        )
        with open("temp.pkl", "wb") as f:
            pickle.dump(book, f)
    else:
        with open("temp.pkl", "rb") as f:
            book = pickle.load(f)

    page = book[0]

    # build connection cycle
    connections = quick_build_chain(page, [
        "eSc_line_da20b4de",
        "eSc_line_1c990ac5",  # ref
        "eSc_line_ae063059",
        "eSc_line_d90e3870",
        "eSc_line_338f6933",
        "eSc_line_3dc3ee51",
        "eSc_line_b9413214",
    ])
    chain = [connections]

    # apply connections to page -> TEI
    connector = GlossOnPageConnector(page)
    tei = connector.apply_connections(chain)
    print("\n\n\n")
    print(str(tei.find_all("gloss")))