import copy

from .cyclic_access import CyclicCounter

from glossit_connect_glosses import ConnectedPair, Word
from glossit_dataclasses import GlossLine


class UndoRedoState:
    """
    Class UndoRedoState encapsulates the state that should be changed when performing undo or redo.

    Properties:
        connections (list[list[ConnectedPair]]): The list of connection chains.
        selection (GlossLine | Word | None): The currently selected object.

    Methods:
        copy: Returns a copy of the object suitable for the Undo/Redo mechanics.
    """
    def __init__(self, connections: list[list[ConnectedPair]] = None, selection: GlossLine | Word | None = None):
        """
        Initialize the class.
        :param connections: The list of connection chains.
        :param selection: The currently selected object.
        """
        self.connections = copy.copy(connections) if connections is not None else []
        self.selection = selection

    def copy(self) -> "UndoRedoState":
        """
        Returns a copy of the object suitable for the Undo/Redo mechanics.
        :return: A shallow copy of the object.
        """
        return UndoRedoState(copy.copy(self.connections), self.selection)


class UndoRedoList:
    """
    Class UndoRedoList provides a representation of past and current actions.

    Private Attributes:
        _elements (list[UndoRedoState]): The list of elements that is to be traversed.
        _counter (CyclicCounter): The cyclic counter for determining the index.
        _max_size (int). The maximum number of actions to keep in the list.

    Methods:
        get_current_element: Returns the currently selected element.
        previous_element: Goes to the previous element and returns it.
        next_element: Goes to the next element and returns it.
        has_elements: Returns True if the list of stored actions contains at least two actions.
        has_elements_before: Returns True if the there are elements before the current selection.
        has_elements_after: Returns True if the there are elements after the current selection.
        reset: Clears the stored actions.
    """
    def __init__(self, max_size: int = 5):
        """
        Initializes a CyclicList instance.
        :param max_size: The maximum number of actions to keep in the list.
        """
        self._elements = []
        self._counter = CyclicCounter(len(self._elements), is_cyclic=False)
        self._max_size = max_size
        assert self._max_size >= 2

    def __len__(self):
        return len(self._counter)

    def get_current_element(self) -> UndoRedoState | None:
        """
        Returns the currently selected element.
        :return: The currently selected element.
        """
        if len(self._elements):
            return self._elements[self._counter.current_index]
        else:
            return None

    def previous_element(self) -> UndoRedoState:
        """
        Goes to the previous element and returns it.
        :return: The previous element.
        """
        # Return a shallow copy: callers install the returned list as the live connections
        # list, and appending to it must not rewrite the stored history element.
        return self._elements[self._counter.previous_index()].copy()

    def next_element(self) -> UndoRedoState:
        """
        Goes to the next element and returns it.
        :return: The next element.
        """
        # Return a shallow copy: callers install the returned list as the live connections
        # list, and appending to it must not rewrite the stored history element.
        return self._elements[self._counter.next_index()].copy()

    def has_elements(self) -> bool:
        """
        Returns True if the list of stored actions contains at least two actions.
        :return: True if there are at least two elements.
        """
        return len(self._elements) >= 2

    def has_elements_before(self) -> bool:
        """
        Returns True if the there are elements before the current selection.
        :return: True if there are elements before.
        """
        return self._counter.current_index > 0

    def has_elements_after(self) -> bool:
        """
        Returns True if the there are elements after the current selection.
        :return: True if there are elements after.
        """
        return self._counter.current_index < len(self._elements)-1

    def add_element(self, element):
        """
        Adds an action to the list and discards old and future actions if needed.
        :param element: The action to be added.
        """

        # discard future actions
        current_index = self._counter.current_index
        self._elements = self._elements[:current_index+1]

        # Add the new action:
        # We need to copy the element,
        # otherwise, the elements will not persist.
        self._elements.append(copy.copy(element))

        # discard old actions if needed
        if len(self._elements) > self._max_size:
            del self._elements[0]

        # if we add a new action, we always have the new action as the current one
        self._counter = CyclicCounter(len(self._elements), is_cyclic=False)
        self._counter.go_to_index(len(self._elements) - 1)

    def reset(self):
        """
        Clears the stored actions.
        """
        self._elements = []
        self._counter = CyclicCounter(len(self._elements), is_cyclic=False)
