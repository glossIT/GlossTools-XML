from PySide6.QtGui import QIcon, QPixmap, Qt, QPainter
from PySide6.QtWidgets import QWidget, QSizePolicy, QPushButton, QTreeWidget, QVBoxLayout, QStyleOptionButton, QStyle, \
    QApplication


def get_checkbox_icon(checked: Qt.CheckState):
    """
    Gets the checkbox icon for a given state.
    :param checked: Qt.CheckState of the checkbox.
    :return: QIcon of the checkbox.
    """
    # Create a style option for the checkbox
    option = QStyleOptionButton()
    option.state = QStyle.StateFlag.State_Enabled
    if checked == Qt.CheckState.Checked:
        option.state |= QStyle.StateFlag.State_On
    elif checked == Qt.CheckState.PartiallyChecked:
        option.state |= QStyle.StateFlag.State_NoChange
    else:
        option.state |= QStyle.StateFlag.State_Off

    style = QApplication.style()

    # Get the size of the checkbox indicator
    rect = style.subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option)
    pixmap = QPixmap(rect.size())
    pixmap.fill(Qt.GlobalColor.transparent)

    # Draw the checkbox indicator onto the pixmap
    painter = QPainter(pixmap)
    option.rect = pixmap.rect()
    style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, option, painter)
    painter.end()

    return QIcon(pixmap)


class ChainManipulation(QWidget):
    """
    ChainManipulation is a widget that sets up a treeview and button for chain manipulation.

    Attributes:
        treeDisplayChains (QTreeWidget): Tree displaying individual chains.
        buttonRemoveChain (QPushButton): Button to remove chain.

    Methods:
        visibility_header_checkbox_set_checkstate (Qt.Checkstate): Sets the "Visible" column checkbox to the
                                                                   correct icon.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        verticalLayout = QVBoxLayout(parent)
        verticalLayout.setObjectName(u"verticalLayout")

        self.treeDisplayChains = QTreeWidget(parent)
        self.buttonRemoveChain = QPushButton(parent)
        verticalLayout.addWidget(self.treeDisplayChains)
        verticalLayout.addWidget(self.buttonRemoveChain)

        self.buttonRemoveChain.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditClear)))

        self.buttonRemoveChain.setObjectName(u"buttonRemoveChain")
        self.buttonRemoveChain.setEnabled(False)


        qtreewidgetitem = self.treeDisplayChains.headerItem()

        qtreewidgetitem.setText(0, "Chain")
        qtreewidgetitem.setText(1, "Visible")
        qtreewidgetitem.setText(2, "Connection")
        self.buttonRemoveChain.setText("Remove Chain")

        self.treeDisplayChains.header().setSectionsClickable(True)

        self._checked_icon = get_checkbox_icon(Qt.CheckState.Checked)
        self._unchecked_icon = get_checkbox_icon(Qt.CheckState.Unchecked)
        self._partially_checked_icon = get_checkbox_icon(Qt.CheckState.PartiallyChecked)

        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeDisplayChains.sizePolicy().hasHeightForWidth())
        self.treeDisplayChains.setSizePolicy(sizePolicy)

        self.visibility_header_checkbox_set_checkstate(Qt.CheckState.Unchecked)

    def visibility_header_checkbox_set_checkstate(self, checked: Qt.CheckState):
        """
        Sets the "Visible" column checkbox to the correct icon.
        :param checked: Qt.CheckState.
        """
        if checked == Qt.CheckState.Checked:
            self.treeDisplayChains.headerItem().setIcon(1, self._checked_icon)
        elif checked == Qt.CheckState.PartiallyChecked:
            self.treeDisplayChains.headerItem().setIcon(1, self._partially_checked_icon)
        else:
            self.treeDisplayChains.headerItem().setIcon(1, self._unchecked_icon)