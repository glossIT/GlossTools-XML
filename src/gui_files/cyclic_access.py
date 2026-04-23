
class CyclicCounter:
    """
    Class CyclicCounter enables going through values like turning a book with wrapping the pages.
    This means, when going to the previous index while currently on the
    first index, the last index is selected, and vice versa.

    Note that the numbering conventions start from 0 as usual in Python,
    but when calling __str__, it will yield a string such as '1 / 2' for the
    first of two indices, and '2 / 2' for the last of two indices.

    Properties:
        number_of_indices (int): The number of indices in the class.
        current_index (int): The index of the currently selected index.

    Class Methods:
        from_dict: Given the serialized output of method `to_dict`, this method restores the contents
                   of the saved class.

    Methods:
        to_dict: Stores the class state as a dictionary.
        index_is_valid (int): Check if the given index is valid.
        reset: Goes straight to the first index.
        next_index: Goes to the next index and returns the new index.
        previous_index: Goes to the previous index and returns the new index.
        go_to_index (int): Goes to the passed index.
    """
    def __init__(self, number_of_indices: int, current_index: int = 0, is_cyclic: bool = True):
        """
        Initializes a CyclicCounter class instance.

        :param number_of_indices: The number of elements in the book.
        :param current_index: The index of the currently selected element.
        :param is_cyclic: Default is True. If False, the page-wrapping feature is disabled, which means
                          that going to the previous index when already at the first returns the first,
                          and vice versa for the last index when going to the next index.
        :raises ValueError: If the values are invalid.
        """
        self._number_of_indices = number_of_indices
        self._current_index = current_index
        self._is_cyclic = is_cyclic

        if number_of_indices < 0:
            raise ValueError("Number of elements cannot be negative")
        if current_index > number_of_indices:
            raise ValueError("Current page cannot be greater than number of elements")

    def __str__(self):
        return f"{self._current_index + 1} / {self.number_of_indices}"

    def __len__(self):
        return self._number_of_indices

    def to_dict(self):
        """
        Stores the class state as a dictionary.
        :return: Dictionary containing the class state.
        """
        return {
            "number_of_pages": self._number_of_indices,
            "current_page_index": self._current_index,
        }

    @classmethod
    def from_dict(cls, dictionary: dict):
        """
        Given the serialized output of method `to_dict`, this method restores the contents of the saved class.
        :param dictionary: The dictionary containing serialized class data.
        :return: A class instance with its state defined by the serialized input data.
        """
        instance = cls(
            number_of_indices=dictionary["number_of_pages"],
            current_index=dictionary["current_page_index"]
        )
        return instance

    @property
    def number_of_indices(self) -> int:
        return self._number_of_indices

    @property
    def current_index(self) -> int:
        return self._current_index

    def index_is_valid(self, element_idx: int) -> bool:
        """
        Check if the given element index is valid.
        :param element_idx: Element index to check.
        :return: True if the index is valid.
        """
        return 0 <= element_idx < self._number_of_indices

    def reset(self):
        """
        Goes straight to the first element.
        """
        self._current_index = 0

    def next_index(self):
        """
        Goes to the next element and returns the new index.
        :return: Index of the next element.
        """
        self._current_index += 1
        if self._current_index >= self.number_of_indices:
            if self._is_cyclic:
                self._current_index = 0
            else:
                self._current_index -= 1
        return self._current_index

    def previous_index(self):
        """
        Goes to the previous element and returns the new index.
        :return: Index of the previous element.
        """
        self._current_index -= 1
        if self._current_index < 0:
            if self._is_cyclic:
                self._current_index = self.number_of_indices - 1
            else:
                self._current_index = 0
        return self._current_index

    def go_to_index(self, idx: int):
        """
        Goes to the passed index.
        :param idx: Index to be selected.
               Must be between 0 and _number_of_indices-1.
        :raises ValueError: If the index is of invalid value.
        """
        if self.index_is_valid(idx):
            self._current_index = idx
        else:
            raise ValueError("Index must be between 0 and _number_of_indices-1.")


class CyclicList:
    """
    Class CyclicList provides a list that can be traversed in a circular fashion.

    Private Attributes:
        _elements (list): The list of elements that is to be traversed.
        _counter (CyclicCounter): The cyclic counter for determining the index.

    Methods:
        get_current_element: Returns the currently selected element.
        previous_element: Goes to the previous element and returns it.
        next_element: Goes to the next element and returns it.
    """
    def __init__(self, elements: list):
        """
        Initializes a CyclicList instance.
        :param elements: The list of elements to traverse.
        """
        self._elements = elements
        self._counter = CyclicCounter(len(elements))

    def __len__(self):
        return len(self._counter)

    def get_current_element(self):
        """
        Returns the currently selected element.
        :return: The currently selected element.
        """
        if len(self._elements):
            return self._elements[self._counter.current_index]
        else:
            return None

    def previous_element(self):
        """
        Goes to the previous element and returns it.
        :return: The previous element.
        """
        return self._elements[self._counter.previous_index()]

    def next_element(self):
        """
        Goes to the next element and returns it.
        :return: The next element.
        """
        return self._elements[self._counter.next_index()]

