from typing import Callable

import tqdm

from glossit_connect_glosses import ConnectedPair, GlossOnPageConnector
from glossit_dataclasses import Word, GlossLine
from xml_extraction import METSBook


class ObservableGlossOnPageConnector(GlossOnPageConnector):
    """
    Class ObservableGlossOnPageConnector endows GlossConnector with callback functionality
    for all methods that change the internal state.

    Attributes:
        callback (Callable): Callback to be executed when the state is changed.
        has_unsaved_changes (bool): True if the object has some unsaved changes.
    """
    def __init__(self, *args, callback: Callable = None, **kwargs,):
        """
        Initializes an instance.
        :param callback: Callback to be executed when the state is changed.
        """
        super().__init__(*args, **kwargs)
        self.callback = callback
        self.has_unsaved_changes = False

    @property
    def connections(self):
        return super().connections

    @connections.setter
    def connections(self, other):
        GlossOnPageConnector.connections.fset(self, other)
        self.has_unsaved_changes = True
        if self.callback is not None:
            self.callback()

    @property
    def clean_tei(self):
        return super().clean_tei

    @clean_tei.setter
    def clean_tei(self, other):
        GlossOnPageConnector.clean_tei.fset(self, other)
        self.has_unsaved_changes = True
        if self.callback is not None:
            self.callback()


class GlossConnectionHandler:
    """
    Class GlossConnectionHandler handles a list of gloss connections. It provides an interface
    for callback when the individual GlossOnPageConnectors are changed and keeps track of
    unsaved changes.

    Attributes:
        callback (Callable): Callback to be executed when the state is changed.

    Properties:
        connector_list (list[ObservableGlossOnPageConnector]): The list of gloss connectors.
        has_unsaved_changes (bool): True if the connections have been changed and not saved yet.

    Methods:
        to_dict: Returns a list of dictionaries containing the class state.
        from_dict (list[dict], METSBook, tqdm.tqdm): Resets the class state with the values loaded from a save file
                                  dictionary and additional information.
        append (ObservableGlossOnPageConnector): Appends an ObservableGlossOnPageConnector to _connector_list.
        append_connection_to_connector (int, ConnectedPair): Appends a connection to the connector with index
                                                 `connector_idx`.
                                                 IMPORTANT: Use this function only, DO NOT use
                                                 `gloss_connection_handler[connector_idx].connection.append(connection)`
                                                 as it will not trigger the callback!
        reset: Clears the list of stored connectors.

    Private Methods:
        _execute_callback: Executes the callback and sets the flag for unsaved changes.
    """
    def __init__(self, callback: Callable, connector_list: list[ObservableGlossOnPageConnector] = []):
        """
        Initializes an instance.
        :param callback: Callback to be executed when the state is changed.
        """
        self.callback = callback
        self._connector_list = connector_list

        self._buffered_serialization = None

    def __len__(self):
        return len(self._connector_list)

    def __getitem__(self, index: int) -> ObservableGlossOnPageConnector:
        return self._connector_list[index]

    def __setitem__(self, index: int, value: ObservableGlossOnPageConnector):
        self._connector_list[index] = value
        self._connector_list[index].has_unsaved_changes = True
        self._execute_callback()

    def __iter__(self):
        return iter(self._connector_list)

    def to_dict(self) -> list[dict]:
        """
        Returns a list of dictionaries containing the class state.
        :return: List of dictionaries representing the state of each stored connector.
        """

        # We do not need to construct everything everytime.
        # If there were no changes, we can just return the buffer.
        # If the buffer is old and some connectors have changed,
        # use the buffered values for the others and only construct
        # the connector serializations for those needed.

        connectors_to_construct = range(len(self._connector_list))
        page_connections = [None] * len(self)

        if self._buffered_serialization is not None:
            if not self.has_unsaved_changes:
                return self._buffered_serialization
            else:
                connectors_to_construct = [idx for idx, connector in enumerate(self._connector_list) if
                                           connector.has_unsaved_changes]

        for connector_idx in range(len(self._connector_list)):
            connector = self._connector_list[connector_idx]

            if connector_idx in connectors_to_construct:  # construct the connector serializations that are needed
                current_page_connections = []
                for connection in connector.connections:
                    # For GlossLine, remove the page and line data, since we can infer it later
                    dictionary = connection.to_dict(ignored_keys=["page", "line"])

                    if isinstance(connection.end, Word):
                        dictionary["end"]["line_id"] = connection.end.line.id

                    current_page_connections.append(dictionary)
                page_connections[connector_idx] = current_page_connections
            else:  # for pages that have not changed, take the buffer
                page_connections[connector_idx] = self._buffered_serialization[connector_idx]

        self._buffered_serialization = page_connections  # update the buffer
        return page_connections

    def from_dict(self, dict_list: list[dict], mets_book: METSBook, tqdm_progress: tqdm.tqdm = None):
        """
        Resets the class state with the values loaded from a save file dictionary and additional information.
        :param dict_list: List of dictionaries (output of this class' `to_dict` method).
        :param mets_book: METSBook belonging to the connectors.
        :param tqdm_progress: A tqdm progress bar for tracking the deserialization progress.
        :return: 
        """
        if tqdm_progress is not None:
            tqdm_progress.iterable = dict_list
            tqdm_progress.total = len(dict_list)
            tqdm_progress.reset()
        else:
            tqdm_progress = dict_list

        self.reset()

        self._buffered_serialization = dict_list
        
        connectors = []
        for page_idx, connection_list in enumerate(tqdm_progress):
            current_page = mets_book[page_idx]
            current_page_connections = []
            for connection in connection_list:
                constructed_object = ConnectedPair.from_dict(connection)

                if isinstance(constructed_object.start, GlossLine):  # restore page data
                    constructed_object.start.page = current_page

                if isinstance(constructed_object.end, Word):  # restore line data
                    constructed_object.end.line = current_page.get_object_from_id(
                        connection["end"]["line_id"]
                    )
                elif isinstance(constructed_object.end, GlossLine):  # restore page data
                    constructed_object.end.page = current_page
                current_page_connections.append(constructed_object)
            connector = ObservableGlossOnPageConnector(current_page, callback=self._execute_callback)
            connector.connections = current_page_connections
            connectors.append(connector)
            
        self._connector_list = connectors

    def _execute_callback(self):
        if self.callback is not None:
            self.callback()

    def append(self, connector: ObservableGlossOnPageConnector):
        """
        Appends an ObservableGlossOnPageConnector to the stored connectors.
        :param connector: The connector to append.
        """
        connector.callback = self._execute_callback
        connector.has_unsaved_changes = True
        self._connector_list.append(connector)
        self._execute_callback()

    def append_connection_to_connector(self, connector_idx: int, connection: ConnectedPair):
        """
        Appends a connection to the connector with index `connector_idx`.

        IMPORTANT: Use this function to force execution of the callback, DO NOT
        use gloss_connection_handler[connector_idx].connection.append(connection)
        as it will not trigger the callback!

        :param connector_idx:
        :param connection:
        :return:
        """
        self._connector_list[connector_idx].connections.append(connection)
        self._connector_list[connector_idx].has_unsaved_changes = True
        self._execute_callback()

    def reset(self):
        """
        Clears the list of stored connectors.
        """
        self._connector_list = []
        self._buffered_serialization = None

    @property
    def connector_list(self):
        return self._connector_list

    @connector_list.setter
    def connector_list(self, other):
        self._connector_list = other
        for connector in self._connector_list:
            connector.callback = self._execute_callback
            connector.has_unsaved_changes = True
        self._execute_callback()

    @property
    def has_unsaved_changes(self):
        has_changes = False
        for connector in self._connector_list:
            has_changes = has_changes or connector.has_unsaved_changes
        return has_changes

    @has_unsaved_changes.setter
    def has_unsaved_changes(self, value: bool):
        for connector in self._connector_list:
            connector.has_unsaved_changes = value
