from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QSizePolicy, QPushButton, QTreeWidget, QVBoxLayout


class ChainManipulation(QWidget):
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

        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeDisplayChains.sizePolicy().hasHeightForWidth())
        self.treeDisplayChains.setSizePolicy(sizePolicy)