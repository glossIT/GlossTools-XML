from bs4 import BeautifulSoup  # XML manipulation
import copy
import numpy as np
import shapely

from glossit_dataclasses import LineType, MainTextLine, GlossLine, Word, get_line_word_id, gloss_line_id_to_tei_id, \
    PageObject, gloss_tei_id_to_id
from xml_extraction import METSPage


class ConnectedPair:
    """
    Class ConnectedPair represents a directed connection between two objects.
    It can be visualized as an arrow from the start object to the end object.

    Attributes:
        start: The start of the connection (the base of the arrow starts here).
        end: The end of the connection (the head of the arrow points there).

    Class Methods:
        from_dict: Given the serialized output of method `to_dict`,
                   this method restores the contents of the saved class.

    Methods:
        to_dict (list[str]): Stores the class state as a dictionary.
    """
    def __init__(self, start: PageObject, end: PageObject):
        """
        Initializes an instance of the ConnectedPair class.

        :param start: The start of the connection (the base of the arrow starts here).
        :param end: The end of the connection (the head of the arrow points there).
        """
        self.start = start
        self.end = end

    def __eq__(self, other):
        if not isinstance(other, ConnectedPair):
            return False
        return self.start == other.start and self.end == other.end

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        return cls(
            start = PageObject.factory_from_dict(dictionary["start"]),
            end = PageObject.factory_from_dict(dictionary["end"])
        )

    def to_dict(self, ignored_keys: list[str] = ()) -> dict:
        """
        Stores the class state as a dictionary.
        :return: Dictionary containing the class state.
        """
        return {
            "start": self.start.to_dict(ignored_keys=ignored_keys),
            "end": self.end.to_dict(ignored_keys=ignored_keys)
        }


def add_ids_to_page(page: METSPage, tei: BeautifulSoup) -> BeautifulSoup:
    """
    Given a METSPage and a TEI XML of it, all gloss lines and main text words are assigned unique IDs.
    The TEI with added results is then returned, the original TEI is not modified.

    :param page: METSPage to which the TEI belongs.
    :param tei: TEI to which the IDs should be added.
    :return: TEI with gloss line and main text word IDs added.
    """
    def add_ids_to_main_text_line(page: METSPage, tei):
        for main_text_line in page.get_main_text_lines():
            line_tag = tei.find("ab", type="textline", facs=f"#{main_text_line.id}")

            # in this case, we have a numbering zone, so don't need to do anything
            if line_tag is None and tei.find("fw", facs=f"{main_text_line.id}") is not None:
                continue
            line_tag.clear()

            for word_idx, word in enumerate(main_text_line.words):
                word_tag = tei.new_tag("w")
                word_tag["xml:id"] = get_line_word_id(line=main_text_line, word_idx=word_idx)
                word_tag.string = word
                line_tag.append(word_tag)

        return tei

    def add_gloss_ids_to_page(page: METSPage, tei: BeautifulSoup):
        for gloss in page.get_gloss_lines():
            ab_tag = tei.find(
                lambda tag: tag.name == "ab" and tag.get("facs") == f"#{gloss.id}" and tag.find_parent("gloss")
            )
            ab_tag.parent["xml:id"] = gloss_line_id_to_tei_id(gloss)

        return tei

    tei = copy.deepcopy(tei)

    # add gloss IDs
    tei = add_gloss_ids_to_page(page, tei)

    # add word IDs
    tei = add_ids_to_main_text_line(page, tei)

    return tei


def get_surrounding_main_text_line(gloss: GlossLine) -> MainTextLine | None:
    """
    Checks if the bounding box of a gloss line lies inside a main text line. If so, the main text
    line is returned.

    :param gloss: Gloss line to be checked.
    :return: Main text line that contains the gloss line, otherwise None.
    """
    # return a line if its mask is a superset of the gloss mask
    # TODO: is this reliable? Test with other manuscript pages
    for main_text_line in gloss.page.get_main_text_lines():
        if shapely.contains(main_text_line.coordinates, gloss.coordinates):
            return main_text_line
    return None


def get_line_below(gloss: GlossLine) -> MainTextLine | None:
    """
    Given a gloss line, return the closest main text line below it.

    :param gloss: Gloss line to be checked.
    :return: Closest main text line below it, otherwise None.
    """
    # we consider the closest line whose average baseline point is below the gloss average baseline point
    gloss_lowest_point = np.max([coordinate[1] for coordinate in gloss.baseline])
    smallest_distance = np.inf
    line_below = None
    for line in gloss.page.get_main_text_lines():
        line_lowest_point = np.max([coordinate[1] for coordinate in line.baseline])
        if gloss_lowest_point < line_lowest_point:  # gloss is above the line
            current_distance = shapely.distance(gloss.coordinates, line.coordinates)
            if current_distance < smallest_distance:
                smallest_distance = current_distance
                line_below = line
    return line_below


def get_closest_word_to_the_right(text_line: MainTextLine, gloss: GlossLine) -> Word | None:
    """
    Given a main text line and a gloss line, the closest word in the main text line that is right to the gloss is
    returned.

    :param text_line: Text line to be checked.
    :param gloss: Gloss to be checked.
    :return: Rightmost word in the main text line in relation to the gloss, otherwise None.
    """
    # take the first word to the right of the gloss center
    for word_idx, (word, word_bb) in enumerate(zip(text_line.words, text_line.word_bounding_boxes)):
        _, top_right, _, _ = word_bb
        word_right_border = top_right[0]
        gloss_center = np.mean([baseline_point[0] for baseline_point in gloss.baseline])
        if gloss_center < word_right_border:
            return Word(text_line, word_idx)


def get_closest_word(text_line: MainTextLine, gloss: GlossLine) -> Word | None:
    """
    Given a main text line and a gloss line, the closest word in the main text line to the gloss is
    returned.

    :param text_line: Text line to be checked.
    :param gloss: Gloss to be checked.
    :return: Closest word in the main text line in relation to the gloss, otherwise None.
    """
    smallest_distance = np.inf
    closest_word = None
    for word_idx, (word, word_bb) in enumerate(zip(text_line.words, text_line.word_bounding_boxes)):
        current_distance = shapely.distance(shapely.Polygon(word_bb), shapely.Polygon(gloss.word_bounding_boxes[0]))
        if current_distance < smallest_distance:
            smallest_distance = current_distance
            closest_word = Word(text_line, word_idx)
    return closest_word


class GlossOnPageConnector:
    """
    Class GlossOnPageConnector handles gloss/reference/word connections inside a METSPage.

    Properties:
        connections (list[ConnectedPair]): The list of individual connections on the page.
        clean_tei (BeautifulSoup): The page TEI, but all connection info and IDs are stripped away.
        page (METSPage): Read-only. METSPage with (or soon to have) gloss/reference/word connections.
        connection_chains (list[list[ConnectedPair]]): Read-only. The connections which are grouped into chains.

    Methods:
        get_unconnected_gloss_line_ids: Gets all gloss lines on the page that are not featured in a connection.
        apply_connections (list[list[ConnectedPair]]): Applies the connections from the provided chain
                                                       to the provided input TEI data.

    Class Methods:
        remove_connections (BeautifulSoup): Given TEI data, remove all connection data and IDs from it and return it.
        extract_connections (METSPage): Given a METSPage, extract all connection data and return it.
        auto_connect (METSPage): Given a METSPage, attempts an automatic connection of all glosses/references and
                                 possibly words.

    Private Class Methods:
        _chain_connections_together (list[ConnectedPair]): Takes a list of connections and groups them into chains.
        _auto_connect_sign_de_renvoi (list[GlossLine]): Given a list of glosses, find and connect Signes de Renvoi.
                                                        The connections and untreated glosses are returned.
        _auto_connect_reference_sign_in_line (list[GlossLine]): Given a list of glosses, find and connect reference
                                                                signs within a main text line (relating to the word
                                                                directly next to the gloss). The connections and
                                                                untreated glosses are returned.
        _auto_connect_reference_sign_outside_line (list[GlossLine]): Given a list of glosses, find and connect reference
                                                                     signs that are outside main text lines, e.g., above
                                                                     a main text line or in the marginal region.
                                                                     The connections and untreated glosses are returned.
        _auto_connect_rest (list[GlossLine]): Given a list of glosses, find and connect glosses that have not been
                                              connected in the previous steps. The connections and untreated glosses
                                              are returned.


    """
    def __init__(self, page: METSPage):
        """
        Initializes a GlossOnPageConnector instance.

        :param page:  METSPage with (or soon to have) gloss/reference/word connections.
        """
        self._page = page
        self._connections = self.extract_connections(self._page)
        self._clean_tei = self.remove_connections(self._page.tei)

    @property
    def connections(self):
        return self._connections

    @connections.setter
    def connections(self, other):
        self._connections = other

    @property
    def page(self):
        return self._page

    @property
    def clean_tei(self):
        return self._clean_tei

    @clean_tei.setter
    def clean_tei(self, other):
        self._clean_tei = other

    @property
    def connection_chains(self):
        return self._chain_connections_together(self._connections)

    def get_unconnected_gloss_line_ids(self) -> list[str]:
        """
        Gets all gloss lines on the page that are not featured in a connection.
        :return: Unconnected gloss lines.
        """
        all_gloss_lines = set([line.id for line in self._page.get_gloss_lines()])

        connected_objects = set()
        for connection in self._connections:
            connected_objects.add(connection.start.id)
            connected_objects.add(connection.end.id)

        unconnected_gloss_lines = all_gloss_lines - connected_objects
        return list(unconnected_gloss_lines)

    def apply_connections(self, chains: list[list[ConnectedPair]], input_tei: BeautifulSoup = None) -> BeautifulSoup:
        """
        Applies the connections from the provided chain to the input_tei data.
        If no input_tei data is given,

        :param chains: Chains to be applied.
        :param input_tei: The TEI data to which the connections are applied. If None, the instance's clean_tei is taken.
        :return: TEI data including connection chains.
        """
        if input_tei is None:
            input_tei = self._clean_tei

        # no chains at all means nothing left to do
        if len(chains) == 0:
            return input_tei

        tei = add_ids_to_page(chains[0][0].start.page, input_tei)

        def chain_to_list(chain) -> list[GlossLine | Word]:
            return_list = []
            for connection in chain:
                return_list.append(connection.start)
            return_list.append(chain[-1].end)
            return return_list

        def connect_multiline_glosses(chain):
            individual_connection_start = 0
            while individual_connection_start < len(chain):

                object_list = chain_to_list(chain)

                # find groups of multiline glosses
                multiline_groups = [[]]
                for object in object_list:
                    if (len(multiline_groups[-1]) == 0 or
                            (
                             isinstance(object, GlossLine)
                             and object.type != LineType.REFERENCE_SIGN
                             and multiline_groups[-1][-1].type != LineType.REFERENCE_SIGN
                            )
                        ):
                        multiline_groups[-1].append(object)
                    else:
                        multiline_groups.append([object])

                new_chained_objects = []
                for group in multiline_groups:
                    if len(group) > 1:
                        ab_tags = [
                            tei.find(
                                lambda tag: tag.name == "ab" and
                                            tag.get("facs") == f"#{object.id}" and
                                            tag.find_parent("gloss")
                            ) for object in group[::-1]
                        ]

                        gloss = ab_tags[0]

                        # insert the other ab tags after the first tag (that is already there)
                        # be careful, we reverse the order, since we always insert the element
                        # after the first position! Only by reversing again we ensure the correct
                        # order.
                        for ab_tag in ab_tags[1:][::-1]:
                            gloss.insert_after(copy.deepcopy(ab_tag))

                        # now, delete the old gloss tags
                        for gloss_line in ab_tags[1:]:
                            gloss_line.parent.decompose()

                        gloss_id = gloss.parent["xml:id"]

                        new_chained_objects.append(
                            GlossLine(
                                page=None,
                                id=gloss_tei_id_to_id(gloss_id),
                                type=None,
                                coordinates=None,
                                baseline=None,
                                text=None
                            )
                        )
                    else:
                        new_chained_objects.append(group[0])

                return new_chained_objects


        for chain in chains:
            # empty chain means nothing left to do
            if len(chain) == 0:
                return

            # convert the multiline glosses in the chain to simple objects
            chained_objects = connect_multiline_glosses(chain)

            # if there are things left to connect that are outside the multiline gloss, do so
            for start, end in zip(chained_objects[:-1], chained_objects[1:]):
                gloss_tag = tei.find("gloss", attrs={"xml:id": gloss_line_id_to_tei_id(start)})
                gloss_tag["target"] = f"#{end.id}"

        return tei

    @classmethod
    def remove_connections(cls, tei: BeautifulSoup) -> BeautifulSoup:
        """
        Given TEI data, remove all connection data and IDs from it and return it.

        :param tei: TEI data from which the connections should be removed.
        :return: TEI data without connections.
        """
        tei_copy = copy.deepcopy(tei)

        # First, find all words and remove the <w> tags around them
        all_lines = tei_copy.find_all(lambda tag: tag.name == "ab")

        for line in all_lines:
            words = line.find_all(lambda tag: tag.name == "w")
            text = ""
            for word in words:
                children = list(word.children)
                if len(children) > 0:
                    text += children[0] + " "
                word.decompose()
            if text != "":
                text = text[:-1]  # remove last added space
            line.append(text)

        # Second, find all xml:id of words and glosses and remove them
        all_ids = tei_copy.find_all(lambda tag: tag.get("xml:id") is not None and tag.name == "gloss")
        for tag in all_ids:
            # when we're already removing tags, also remove target tags
            tag.attrs = {key: value for key, value in tag.attrs.items() if key not in ("xml:id", "target")}

        # Third, split up multiline glosses
        all_glosses = tei_copy.find_all(lambda tag: tag.name == "gloss")
        for gloss in all_glosses:
            children = copy.deepcopy(list(gloss.children))
            if len(children) > 1:  # this is a multiline gloss
                gloss_type = gloss["rendition"]
                for glossline in children[
                    ::-1]:  # reverse order due to insert_after, so the original order is preserved
                    gloss_tag = tei_copy.new_tag("gloss", rendition=gloss_type)
                    gloss_tag.append(glossline)
                    gloss.insert_after(gloss_tag)
                gloss.decompose()

        return tei_copy

    @classmethod
    def extract_connections(cls, page) -> list[ConnectedPair]:
        """
        Given a METSPage, extract all connection data and return it.

        :param page: METSPage from which to extract connections.
        :return: List of all connections found on the page.
        """
        # build a dictionary of all words
        word_dictionary = {}
        word_tags = page.tei.find_all(
            lambda tag: tag.get("xml:id") is not None and tag.parent.name in ("div", "ab") and tag.name == "w")
        for word_tag in word_tags:
            word = Word(line=page.get_object_from_id(word_tag.parent.get("facs")[1:]),
                        word_idx=int(word_tag.get("xml:id").split("_")[-1]))
            word_dictionary[word_tag.get("xml:id")] = word

        connections = []

        def get_target_from_id(identifier):
            try:
                return page.get_object_from_id(gloss_tei_id_to_id(identifier))
            except Exception:  # if we can't find an ID in the main text lines or gloss lines, we must refer to a word
                return word_dictionary[identifier]

        # build all gloss connections
        all_ids = page.tei.find_all(
            lambda tag: tag.get("xml:id") is not None and tag.parent.name in ("div", "ab") and tag.name == "gloss")
        for tag_id in all_ids:
            if tag_id.name == "gloss":  # gloss connections start from last line of gloss to first line of gloss
                subglosses = tag_id.find_all("ab")
                if len(subglosses) > 1:
                    for idx in range(len(subglosses) - 1):
                        connections.append(ConnectedPair(start=page.get_object_from_id(subglosses[idx + 1]["facs"][1:]),
                                                         end=page.get_object_from_id(subglosses[idx]["facs"][1:])))
                if tag_id.get("target") is not None:
                    target_id = tag_id.get("target")[1:]
                    target_object = get_target_from_id(target_id)
                    connections.append(
                        ConnectedPair(start=page.get_object_from_id(subglosses[0]["facs"][1:]), end=target_object))

        return connections


    @classmethod
    def auto_connect(cls, page: METSPage) -> list[list[ConnectedPair]]:
        """
        Given a METSPage, attempts an automatic connection of all glosses/references and possibly words.

        :param page: METSPage on which the connections should be automatically detected.
        :return: List of connection cycles found on the page.
        """
        all_glosses = page.get_gloss_lines()
        # ORDER IS IMPORTANT
        page_connections = []
        curr_conns, all_glosses = cls._auto_connect_sign_de_renvoi(all_glosses)
        page_connections += curr_conns
        curr_conns, all_glosses = cls._auto_connect_reference_sign_in_line(all_glosses)
        page_connections += curr_conns
        curr_conns, all_glosses = cls._auto_connect_reference_sign_outside_line(all_glosses)
        page_connections += curr_conns
        curr_conns, all_glosses = cls._auto_connect_rest(all_glosses)
        page_connections += curr_conns

        return cls._chain_connections_together(page_connections)

    @classmethod
    def _chain_connections_together(cls, page_connections: list[ConnectedPair]) -> list[list[ConnectedPair]]:
        """
        Takes a list of connections and groups them into chains.

        :param page_connections: Connections that should be grouped into chains.
        :return: List of chained connections.
        """

        temp_connections = copy.deepcopy(page_connections)
        connection_cycles = []
        for idx in range(len(temp_connections) - 1, -1, -1):
            connection = temp_connections[idx]
            # always start the chain with a connection where connection.start does not occur as an
            # end point of a different connection.
            if connection.start.id not in [other_connection.end.id for other_connection in page_connections]:
                connection_cycles.append([connection])
                del temp_connections[idx]
            else:
                # if for some reason we have a circular reference of the form a -> b and b -> a
                # we add the connection nevertheless
                for other_connection in page_connections:
                    if connection.start.id == other_connection.end.id and other_connection.start.id == connection.end.id:
                        connection_cycles.append([connection])
                        del temp_connections[idx]
                        break

        while len(temp_connections) > 0:  # fetch and connect elements until all connections are in a chain
            def traverse():
                for idx in range(len(temp_connections)):
                    connection = temp_connections[idx]
                    for cycle in connection_cycles:
                        if cycle[
                            -1].end.id == connection.start.id:  # if we can add the current connection to a chain
                            cycle.append(connection)
                            del temp_connections[idx]
                            return

            traverse()

        # now sort the chains according to the y coordinate of the first element's first baseline point
        connection_cycles = sorted(connection_cycles, key=lambda cycle: cycle[0].start.baseline[0][1])
        return connection_cycles

    @classmethod
    def _auto_connect_sign_de_renvoi(cls, all_glosses: list[GlossLine]) -> tuple[list[ConnectedPair], list[GlossLine]]:
        """
        Given a list of glosses, find and connect Signes de Renvoi. The connections and untreated glosses are returned.

        :param all_glosses: Glosses to inspect and connect.
        :return: Found connections and untreated glosses.
        """
        connections = []
        excluded_glosses = []

        for gloss in all_glosses:  # signes de renvoi
            if gloss.type == LineType.INTERLINEAR_LINE_SIGNE_DE_RENVOI:
                # get line below gloss, for this we consider all lines where the
                # lowest line baseline point is lower than the lowest gloss baseline point
                # from these, we take the line with the smallest distance to the gloss
                gloss_lowest_point = max([coordinate[1] for coordinate in gloss.baseline])

                smallest_distance = np.inf
                line_below = None
                for line in gloss.page.get_main_text_lines():
                    line_lowest_point = max([coordinate[1] for coordinate in line.baseline])
                    if gloss_lowest_point < line_lowest_point:  # gloss is above the line
                        current_distance = shapely.distance(gloss.coordinates, line.coordinates)
                        if current_distance < smallest_distance:
                            smallest_distance = current_distance
                            line_below = line

                word = get_closest_word(line_below, gloss)
                connection = ConnectedPair(gloss, word)
                connections.append(connection)

                # the glosses that are connected in this case can never be connected to anything else
                excluded_glosses.append(gloss)

        remaining_glosses = [gloss for gloss in all_glosses if gloss not in excluded_glosses]
        return connections, remaining_glosses

    @classmethod
    def _auto_connect_reference_sign_in_line(cls, all_glosses: list[GlossLine])\
            -> tuple[list[ConnectedPair], list[GlossLine]]:
        """
        Given a list of glosses, find and connect reference signs within a main text line (relating to the word
        directly next to the gloss). The connections and untreated glosses are returned.

        :param all_glosses: Glosses to inspect and connect.
        :return: Found connections and untreated glosses.
        """
        connections = []
        excluded_glosses = []

        reference_signs = []
        glosses_that_are_not_reference_signs = []
        for gloss in all_glosses:
            if gloss.type == LineType.REFERENCE_SIGN:
                reference_signs.append(gloss)
            else:
                glosses_that_are_not_reference_signs.append(gloss)

        reference_signs_not_in_text_line = []
        for gloss in reference_signs:  # check all reference signs
            main_line = get_surrounding_main_text_line(gloss)
            if main_line is not None:  # if so, this gloss is in the middle of a line and refers to the word right to it
                word = get_closest_word_to_the_right(main_line, gloss)
                connection = ConnectedPair(gloss, word)
                connections.append(connection)

                # this also means that there must be some other reference sign connecting to it
                # we get the closest of such reference signs
                closest_same_symbol = None
                smallest_distance = np.inf
                for other_gloss in reference_signs:
                    if gloss.id != other_gloss.id and gloss.text == other_gloss.text:
                        distance = shapely.distance(other_gloss.coordinates, gloss.coordinates)
                        if distance < smallest_distance:
                            smallest_distance = distance
                            closest_same_symbol = other_gloss

                connection = ConnectedPair(closest_same_symbol, gloss)
                connections.append(connection)

                # again, this closest_same_symbol (as a reference sign), must in turn also connect to some gloss
                # so, let's get the rightmost gloss
                # This can only be an interlinear correction or addition!
                # 1) first filter all glosses that are right to the gloss, find the one that is closest
                final_gloss = None
                smallest_distance = np.inf
                for gloss_to_the_right in glosses_that_are_not_reference_signs:
                    # to minimize the risk of overlapping and excluding the closest gloss to the right,
                    # lets compare the leftmost points of the individual glosses
                    # (reference signs have small width anyway)
                    if gloss_to_the_right.type in (LineType.INTERLINEAR_LINE_CORRECTION,
                                                   LineType.INTERLINEAR_LINE_ADDITION) and gloss_to_the_right.baseline[0][
                        0] > closest_same_symbol.baseline[0][0]:
                        distance = np.linalg.norm(
                            np.array(gloss_to_the_right.baseline[0]) - np.array(closest_same_symbol.baseline[0]))
                        if distance < smallest_distance:
                            final_gloss = gloss_to_the_right
                            smallest_distance = distance
                # 2) register the connection
                connection = ConnectedPair(final_gloss, closest_same_symbol)
                connections.append(connection)

                # the glosses that are connected in this case can never be connected to anything else
                excluded_glosses += [gloss, closest_same_symbol, final_gloss]

        remaining_glosses = [gloss for gloss in all_glosses if gloss not in excluded_glosses]
        return connections, remaining_glosses

    @classmethod
    def _auto_connect_reference_sign_outside_line(cls, all_glosses: list[GlossLine])\
            -> tuple[list[ConnectedPair], list[GlossLine]]:
        """
        Given a list of glosses, find and connect reference signs that are outside main text lines, e.g., above
        a main text line or in the marginal region. The connections and untreated glosses are returned.

        :param all_glosses: Glosses to inspect and connect.
        :return: Found connections and untreated glosses.
        """
        # they must be connected to some marginal or intercolumnar gloss
        connections = []
        excluded_glosses = []

        # collect reference signs
        reference_signs = []
        for gloss in all_glosses:
            if gloss.type == LineType.REFERENCE_SIGN:
                reference_signs.append(gloss)

        # if we don't have any reference signs, there's nothing to do here
        if len(reference_signs) == 0:
            return [], all_glosses

        for gloss in all_glosses:  # marginal and intercolumnar glosses
            if gloss.type in (LineType.MARGINAL_LINE_GLOSS, LineType.INTERCOLUMNAR_LINE_GLOSS):
                # find reference signs that are in the same line
                gloss_top = min([coordinate[1] for coordinate in gloss.coordinates.exterior.coords])
                gloss_bottom = max([coordinate[1] for coordinate in gloss.coordinates.exterior.coords])

                # take the closest of these reference signs and connect them
                smallest_distance = np.inf
                closest_reference = None
                for reference_sign in reference_signs:
                    reference_sign_height = np.mean([coordinate[1] for coordinate in reference_sign.baseline])
                    # reference sign is in the same line as the gloss
                    if gloss_top < reference_sign_height and reference_sign_height < gloss_bottom:
                        current_distance = shapely.distance(gloss.coordinates, reference_sign.coordinates)
                        if current_distance < smallest_distance:
                            smallest_distance = current_distance
                            closest_reference = reference_sign
                connection = ConnectedPair(gloss, closest_reference)
                connections.append(connection)

                # now connect the reference sign with the closest other reference sign bearing the same sign
                closest_same_reference = None
                smallest_distance = np.inf
                for other_reference in reference_signs:
                    if closest_reference.id != other_reference.id and closest_reference.text == other_reference.text:
                        distance = shapely.distance(closest_reference.coordinates, other_reference.coordinates)
                        if distance < smallest_distance:
                            smallest_distance = distance
                            closest_same_reference = other_reference
                connection = ConnectedPair(closest_reference, closest_same_reference)
                connections.append(connection)

                # now we connect the reference sign to the closest word below
                line_below = get_line_below(closest_same_reference)
                word = get_closest_word(line_below, closest_same_reference)
                connection = ConnectedPair(closest_same_reference, word)
                connections.append(connection)

                # the glosses that are connected in this case can never be connected to anything else
                excluded_glosses.append(gloss)

        remaining_glosses = [gloss for gloss in all_glosses if gloss not in excluded_glosses]
        return connections, remaining_glosses

    @classmethod
    def _auto_connect_rest(cls, all_glosses: list[GlossLine]) -> tuple[list[ConnectedPair], list[GlossLine]]:
        """
        Given a list of glosses, find and connect glosses that have not been connected in the previous steps.
        The connections and untreated glosses are returned.

        :param all_glosses: Glosses to inspect and connect.
        :return: Found connections and untreated glosses.
        """
        connections = []
        excluded_glosses = []

        for gloss in all_glosses:  # check all corrections
            if gloss.type in (
                    LineType.INTERLINEAR_LINE_CORRECTION,
                    LineType.INTERLINEAR_LINE_ADDITION,
                    LineType.INTERLINEAR_LINE_NUMBER,
                    LineType.INTERLINEAR_LINE_GLOSS
            ):
                line_below = get_line_below(gloss)
                word = get_closest_word(line_below, gloss)
                connection = ConnectedPair(gloss, word)
                connections.append(connection)

                # the glosses that are connected in this case can never be connected to anything else
                excluded_glosses.append(gloss)

        remaining_glosses = [gloss for gloss in all_glosses if gloss not in excluded_glosses]
        return connections, remaining_glosses

