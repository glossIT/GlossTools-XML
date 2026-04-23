from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QStyle, QMessageBox


class DialogSaveOnExit(QDialog):
    CANCEL: int = 0
    DISCARD: int = 1
    SAVE: int = 2

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unsaved Changes")

        self.warning_label = QLabel()
        self.warning_label.setPixmap(QMessageBox.standardIcon(QMessageBox.Icon.Warning))
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.message_label = QLabel(
            "The project contains unsaved changes.\n"
            "Changes which are not saved will be permanently lost."
        )
        self.message_label.setWordWrap(True)  # Enable word wrapping for the text

        # Create buttons
        self.discard_button = QPushButton("Close without Saving")
        self.discard_button.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditDelete)))
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditClear)))
        self.save_button = QPushButton("Save")
        self.save_button.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave)))

        self.save_button.setFocus()

        # Connect buttons to their respective actions
        self.cancel_button.clicked.connect(lambda: self.done(self.CANCEL))
        self.discard_button.clicked.connect(lambda: self.done(self.DISCARD))
        self.save_button.clicked.connect(lambda: self.done(self.SAVE))

        # Layout to arrange buttons vertically
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.discard_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        message_layout = QHBoxLayout()
        message_layout.addWidget(self.warning_label)
        message_layout.addWidget(self.message_label)

        layout = QVBoxLayout()
        layout.addLayout(message_layout)
        layout.addLayout(button_layout)

        # Set the layout for the dialog
        self.setLayout(layout)
