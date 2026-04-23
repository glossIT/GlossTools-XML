from abc import ABC, abstractmethod
import math

from PySide6.QtCore import (Qt, QPointF)
from PySide6.QtGui import (QBrush, QColor, QPolygonF, QPen, QFont)
from PySide6.QtWidgets import (QGraphicsPolygonItem, QGraphicsLineItem, QGraphicsTextItem, QGraphicsItem)


class GraphicsItem(ABC):
    """
    Abstract base class GraphicsItem provides an interface for storing Qt QGraphicsItems (which are mostly
    the result of costly calculations and thus cannot be performed in the main loop; and they also can't
    themselves be stored in the program state since they are GUI widgets). It enables on-the-fly
    conversion to actual QGraphicsItems.

    Abstract Methods:
        to_objects: Returns a list of QGraphicsItems constructed from the object.
    """
    @abstractmethod
    def to_objects(self) -> list[QGraphicsItem]:
        """
        Returns a list of QGraphicsItems constructed from the object.
        :return: A list of QGraphicsItems.
        """
        raise NotImplementedError


class PolygonItem(GraphicsItem):
    """
    PolygonItem is a wrapper class for QGraphicsPolygonItem. It enables the construction and storing of such
    objects in the program state without actually having to construct the GUI widgets.

    Attributes:
        polygon_points (tuple[tuple[int, int]]): Polygon points.
        color (QColor): Polygon color.
        filled (bool): If True, the polygon is rendered as filled.

    Methods:
        to_objects: Overrides. Returns a list of QGraphicsItems constructed from the object.
    """
    def __init__(self, polygon_points: list[tuple[int, int]], color: QColor, filled: bool = True):
        """
        Initializes a new PolygonItem object.

        :param polygon_points: Polygon points.
        :param color: Polygon color.
        :param filled: If True, the polygon is rendered as filled.
        """
        self.polygon_points = polygon_points
        self.color = color
        self.filled = filled

    def to_objects(self) -> list[QGraphicsPolygonItem]:
        """
        Overrides. Returns a list of QGraphicsItems constructed from the object.
        :return: A list of QGraphicsItems.
        """
        polygon = QPolygonF([QPointF(x, y) for x, y in self.polygon_points])
        polygon_item = QGraphicsPolygonItem(polygon)
        polygon_item.setPen(QPen(self.color, 1))
        if self.filled:
            polygon_item.setBrush(QBrush(self.color, Qt.SolidPattern))
        return [polygon_item]


class TextItem(GraphicsItem):
    """
    PolygonItem is a wrapper class for QGraphicsTextItem. It enables the construction and storing of such
    objects in the program state without actually having to construct the GUI widgets.

    Attributes:
        text (str): Text string.
        position (tuple[int, int]): Text position.
        color (QColor): Text color.
        fontsize (int): Font size.

    Methods:
        to_objects: Overrides. Returns a list of QGraphicsItems constructed from the object.
    """
    def __init__(self, text: str, position: tuple[int, int], color: QColor, fontsize: int = 20):
        """
        Initializes a new TextItem object.

        :param text: Text string.
        :param position: Text position.
        :param color: Text color.
        :param fontsize: Font size.
        """
        self.text = text
        self.position = position
        self.color = color
        self.fontsize = fontsize

    def to_objects(self) -> list[QGraphicsTextItem]:
        """
        Overrides. Returns a list of QGraphicsItems constructed from the object.
        :return: List of QGraphicsTextItem.
        """
        text_item = QGraphicsTextItem(self.text)
        text_item.setFont(QFont("Junicode", self.fontsize))
        text_item.setDefaultTextColor(self.color)
        width = text_item.boundingRect().width()
        height = text_item.boundingRect().height()
        text_item.setPos(self.position[0]-width//2, self.position[1]-height//2)
        return [text_item]


class ArrowItem(GraphicsItem):
    """
    PolygonItem is a wrapper class for arrows (that consist of a QGraphicsLineItem and a QGraphicsPolygonItem).
    It enables the construction and storing of such objects in the program state without actually having to
    construct the GUI widgets.

    Attributes:
        start (tuple[int, int]): Start coordinates (base of the arrow).
        end (tuple[int, int]): End coordinates (head of the arrow).
        color (QColor): Arrow color.

    Methods:
        to_objects: Overrides. Returns a list of QGraphicsItems constructed from the object.
    """
    def __init__(self, start: tuple[int, int], end: tuple[int, int], color: QColor):
        """
        Initializes a new ArrowItem object.

        :param start: Start coordinates (base of the arrow).
        :param end: End coordinates (head of the arrow).
        :param color: Arrow color.
        """
        self.start = start
        self.end = end
        self.color = color

    def to_objects(self) -> list[QGraphicsItem]:
        """
        Overrides. Returns a list of QGraphicsItems constructed from the object.
        :return: List of QGraphicsItems.
        """
        # draw arrow
        line_item = QGraphicsLineItem(*self.start, *self.end)
        line_item.setPen(QPen(self.color, 5))

        # Add arrowhead
        arrow_size = 30
        angle = math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0])
        arrow_p1 = QPointF(
            self.end[0] - arrow_size * math.cos(angle - math.pi / 6),
            self.end[1] - arrow_size * math.sin(angle - math.pi / 6)
        )

        arrow_p2 = QPointF(
            self.end[0] - arrow_size * math.cos(angle + math.pi / 6),
            self.end[1] - arrow_size * math.sin(angle + math.pi / 6)

        )
        arrow_head = QGraphicsPolygonItem(QPolygonF([QPointF(self.end[0], self.end[1]), arrow_p1, arrow_p2]))
        arrow_head.setBrush(QBrush(self.color))

        return [line_item, arrow_head]
