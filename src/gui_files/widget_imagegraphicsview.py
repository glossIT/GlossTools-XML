from PIL import Image, ImageQt
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem

from glossit_connect_glosses import ConnectedPair
from glossit_dataclasses import GlossLine

from .cyclic_access import CyclicList
from .graphics import construct_connection_graphics_from_connector
from .logger import LoggerSingleton
from .program_state import ProgramStateSingleton


class ImageGraphicsView(QGraphicsView):
    """
    ImageGraphicsView is a widget with which the manuscript page is displayed including additional information
    such as word bounding boxes, gloss/reference sign/word connection data. It provides features such as scrolling
    using the mouse wheel, dragging the image using the left mouse button, and creating new connection cycles by
    selecting glosses/references/words with the right mouse button.

    Attributes:
        scene (QGraphicsScene): The scene containing the objects that are displayed in the QGraphicsView.

    Methods:
        wheelEvent (QEvent): Overrides QGraphicsView.wheelEvent. Adds scaling of the view using the mouse wheel.
        keyPressEvent (QEvent): Overrides QGraphicsView.keyPressEvent. We don't need key responsiveness here.
        load_image_from_pil (Image.Image): Loads a PIL Image into the scene causing it to be displayed.
    """
    def __init__(self, parent: "MainWindow" =None):
        super().__init__(parent.centralwidget)
        self.main_window = parent.main_window
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self.scene = QGraphicsScene(self)

        self.setScene(self.scene)
        self.setEnabled(False)  # we want it to be disabled first

    def mousePressEvent(self, event):
        """
        Overrides QGraphicsView.mousePressEvent to handle user inputs via right click.

        :param event: Passed mouse press event.
        """
        scene_coordinates = self.mapToScene(event.pos())
        scene_x, scene_y = int(scene_coordinates.x()), int(scene_coordinates.y())

        LoggerSingleton().logger.log_user_interaction(
            f"imageGraphicsView.mousePressEvent ("
            f"button = {event.button()}, "
            f"pos = {event.pos().x(), event.pos().y()}, "
            f"scene_coordinates = {(scene_x, scene_y)}"
            f")"
        )

        if event.button() == Qt.MouseButton.RightButton:
            def on_select_object(x, y):
                def select_object():
                    ProgramStateSingleton().program_state.select_or_connect_on_coordinate(x, y)
                return select_object
            self.main_window.thread_function(on_select_object(scene_x, scene_y))
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event):
        """
        Overrides QGraphicsView.wheelEvent. Adds scaling of the view using the mouse wheel.
        :param event: Passed wheel event.
        """
        LoggerSingleton().logger.log_user_interaction(
            f"imageGraphicsView.wheelEvent (angleDelta = {event.angleDelta()})"
        )
        factor = 1.2  # scaling factor. Larger values mean more scaling per wheel.
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        """
        Overrides QGraphicsView.keyPressEvent. We don't need key responsiveness here.
        :param event: Passed event.
        """
        event.ignore()

    def load_image_from_pil(self, image: Image.Image):
        """
        Loads a PIL Image into the scene causing it to be displayed.
        :param image: PIL Image.
        """
        pixmap = QPixmap.fromImage(ImageQt.ImageQt(image))
        image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(image_item)
        self.setSceneRect(QRectF(pixmap.rect()))
        self.setEnabled(True)
