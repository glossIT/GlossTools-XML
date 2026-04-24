# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_new_project.ui'
##
## Created by: Qt User Interface Compiler version 6.9.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFrame, QGridLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_NewProjectDialog(object):
    def __init__(self, *args, window_title: str = "Create New Project", **kwargs):
        super().__init__(*args, **kwargs)
        self.window_title = window_title

    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(718, 159)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Dialog.sizePolicy().hasHeightForWidth())
        Dialog.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.labelModelFileDisplay = QLabel(Dialog)
        self.labelModelFileDisplay.setObjectName(u"labelModelFileDisplay")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.labelModelFileDisplay.sizePolicy().hasHeightForWidth())
        self.labelModelFileDisplay.setSizePolicy(sizePolicy1)
        self.labelModelFileDisplay.setMinimumSize(QSize(76, 0))
        self.labelModelFileDisplay.setFrameShape(QFrame.Shape.Panel)
        self.labelModelFileDisplay.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.labelModelFileDisplay, 2, 1, 1, 1)

        self.buttonOpenMets = QPushButton(Dialog)
        self.buttonOpenMets.setObjectName(u"buttonOpenMets")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.buttonOpenMets.sizePolicy().hasHeightForWidth())
        self.buttonOpenMets.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.buttonOpenMets, 0, 2, 1, 1)

        self.label = QLabel(Dialog)
        self.label.setObjectName(u"label")
        sizePolicy2.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.buttonOpenModel = QPushButton(Dialog)
        self.buttonOpenModel.setObjectName(u"buttonOpenModel")
        sizePolicy2.setHeightForWidth(self.buttonOpenModel.sizePolicy().hasHeightForWidth())
        self.buttonOpenModel.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.buttonOpenModel, 2, 2, 1, 1)

        self.labelMetsFileDisplay = QLabel(Dialog)
        self.labelMetsFileDisplay.setObjectName(u"labelMetsFileDisplay")
        sizePolicy1.setHeightForWidth(self.labelMetsFileDisplay.sizePolicy().hasHeightForWidth())
        self.labelMetsFileDisplay.setSizePolicy(sizePolicy1)
        self.labelMetsFileDisplay.setMinimumSize(QSize(76, 0))
        self.labelMetsFileDisplay.setFrameShape(QFrame.Shape.Panel)
        self.labelMetsFileDisplay.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.labelMetsFileDisplay, 0, 1, 1, 1)

        self.buttonOpenTei = QPushButton(Dialog)
        self.buttonOpenTei.setObjectName(u"buttonOpenTei")
        sizePolicy2.setHeightForWidth(self.buttonOpenTei.sizePolicy().hasHeightForWidth())
        self.buttonOpenTei.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.buttonOpenTei, 1, 2, 1, 1)

        self.labelTeiFileDisplay = QLabel(Dialog)
        self.labelTeiFileDisplay.setObjectName(u"labelTeiFileDisplay")
        sizePolicy1.setHeightForWidth(self.labelTeiFileDisplay.sizePolicy().hasHeightForWidth())
        self.labelTeiFileDisplay.setSizePolicy(sizePolicy1)
        self.labelTeiFileDisplay.setMinimumSize(QSize(76, 0))
        self.labelTeiFileDisplay.setFrameShape(QFrame.Shape.Panel)
        self.labelTeiFileDisplay.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.labelTeiFileDisplay, 1, 1, 1, 1)

        self.label_5 = QLabel(Dialog)
        self.label_5.setObjectName(u"label_5")
        sizePolicy2.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.label_5, 2, 0, 1, 1)

        self.label_3 = QLabel(Dialog)
        self.label_3.setObjectName(u"label_3")
        sizePolicy2.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)


        self.verticalLayout.addLayout(self.gridLayout)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setEnabled(True)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setCenterButtons(True)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", self.window_title, None))
        self.labelModelFileDisplay.setText("")
        self.buttonOpenMets.setText(QCoreApplication.translate("Dialog", u"Open File...", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"METS File:", None))
        self.buttonOpenModel.setText(QCoreApplication.translate("Dialog", u"Open File...", None))
        self.labelMetsFileDisplay.setText("")
        self.buttonOpenTei.setText(QCoreApplication.translate("Dialog", u"Open File...", None))
        self.labelTeiFileDisplay.setText("")
        self.label_5.setText(QCoreApplication.translate("Dialog", u"OCR Model File:", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", u"TEI File:", None))
    # retranslateUi

