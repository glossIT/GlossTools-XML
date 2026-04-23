import os
import tqdm
from typing import Iterable, Callable

from PySide6.QtCore import QEvent, Qt, QObject, Signal
from PySide6.QtWidgets import QDialog, QMainWindow, QLabel, QProgressBar, QVBoxLayout


class LoadingDialogContent(QObject):
    """
    Class LoadingWindowContent encapsulates what information should be displayed in a LoadingDialog object.

    Properties:
        changed_action_text (Signal): Signal to be emitted on setting the action text.
        changed_status_text (Signal): Signal to be emitted on setting the status text.
        changed_progress_bar_value (Signal): Signal to be emitted on setting the progress bar value.
        changed_progress_bar_visibility (Signal): Signal to be emitted when setting status bar visibility.

        callback_tqdm (CallbackTqdm): Tracking progress of iterables including callback.

        action_text (str): The name of the action that is currently being performed and displayed by the dialog.
        status_text (str): The action status text that is displayed by the loading dialog.
        progress_bar_value (int): The progress bar value that is displayed by the loading dialog.
        progress_bar_visible (bool): Indicates whether the progress bar is visible.
    """
    changed_action_text = Signal(str)
    changed_status_text = Signal(str)
    changed_progress_bar_value = Signal(int)
    changed_progress_bar_visibility = Signal(bool)

    def __init__(self):
        """
        Initializes the LoadingDialogContent instance.
        """
        super().__init__()

        self.callback_tqdm = CallbackTqdm(
            file=open(os.devnull, "w"),  # status updates are not written to stderr
            status_update_callback=lambda string: self.changed_status_text.emit(string),
            progress_bar_update_callback=lambda integer: self.changed_progress_bar_value.emit(integer)
        )
        self._action_text = None
        self._status_text = None
        self._progress_bar_value = None
        self._progress_bar_visible = None

    @property
    def action_text(self):
        return self._action_text

    @action_text.setter
    def action_text(self, text: str):
        if self._action_text != text:
            self._action_text = text
            self.changed_action_text.emit(text)

    @property
    def status_text(self):
        return self._status_text

    @status_text.setter
    def status_text(self, text: str):
        if self._status_text != text:
            self._status_text = text
            self.changed_status_text.emit(text)

    @property
    def progress_bar_value(self):
        return self._progress_bar_value

    @progress_bar_value.setter
    def progress_bar_value(self, value: int):
        if self._progress_bar_value != value:
            self._progress_bar_value = value
            self.changed_progress_bar_value.emit(value)

    @property
    def progress_bar_visible(self):
        return self._progress_bar_visible

    @progress_bar_visible.setter
    def progress_bar_visible(self, value: bool):
        if self._progress_bar_visible != value:
            self._progress_bar_visible = value
            self.changed_progress_bar_visibility.emit(value)


class CallbackTqdm(tqdm.tqdm):
    """
    A wrapper to a tqdm.tqdm object such that a callback function is executed on each
    reset and update.

    Attributes:
        iterable (Iterable): An iterable that should be traversed and whose progress is to be tracked.
        status_update_callback (Callable[[str], None]): A callback function taking a string of the current progress.
                                                        It is executed on each reset and update.

    Methods:
        update (int): Override. Update the progress bar and execute callback if set.
        reset: Override. Reset the progress bar displayed state and execute callback if set.
        close: Override. Close the current tqdm object and construct a new one for future use.

    Private Methods:
        _get_progress_text: Construct a progress text that for use in the callback function.
        _get_progress_percentage: Returns the progress percentage as integer.
    """

    def __init__(self,
                 *args,
                 iterable: Iterable = None,
                 status_update_callback: Callable[[str], None] = None,
                 progress_bar_update_callback: Callable[[int], None] = None,
                 **kwargs
                 ):
        """
        Initializes an instance of class CallbackTqdm.

        :param args: Arguments passed to tqdm.tqdm.
        :param iterable: An iterable that should be traversed and whose progress is to be tracked.
        :param status_update_callback: Callback that is executed when the status is
        :param progress_bar_update_callback:
        :param kwargs: Keyword arguments passed to tqdm.tqdm.
        """
        super().__init__(*args, **kwargs)
        self.iterable = iterable
        self.status_update_callback = status_update_callback
        self.progress_bar_callback = progress_bar_update_callback
        self._args = args
        self._kwargs = kwargs

    def __iter__(self):
        if self.iterable is None:
            raise ValueError("Iterable not set. Set iterable and total parameters.")
        for item in self.iterable:
            yield item
            self.update()

    def update(self, n: int = 1):
        """
        Override. Update the progress bar and execute callback if set.
        :param n: Increment to add to the internal counter of iterations.
        """
        super().update(n)
        if self.status_update_callback is not None:
            self.status_update_callback(self._get_progress_text())
        if self.progress_bar_callback is not None:
            self.progress_bar_callback(self._get_progress_percentage())

    def reset(self, *args, **kwargs):
        """
        Override. Reset the progress bar displayed state and execute callback if set.

        :param args: Arguments passed to tqdm.tqdm.reset.
        :param kwargs: Keyword arguments passed to tqdm.tqdm.reset.
        """
        super().reset(*args, **kwargs)
        if self.status_update_callback is not None:
            self.status_update_callback(self._get_progress_text())
        if self.progress_bar_callback is not None:
            self.progress_bar_callback(self._get_progress_percentage())

    def close(self):
        """
        Override. Close the current tqdm object and construct a new one for future use.
        """
        super().close()
        super().__init__(*self._args, **self._kwargs)

    def _get_progress_text(self) -> str:
        """
        Construct a progress text that for use in the callback function.
        :return: Progress text.
        """
        elapsed_time = self.format_dict["elapsed"]
        loop_index = self.format_dict["n"]
        total_iterations = self.format_dict["total"]

        iterations_string = f"Finished: {loop_index}/{total_iterations}\n"

        if total_iterations is not None and loop_index is not None and self.format_dict["rate"] is not None:
            remaining_time = (total_iterations - loop_index) / self.format_dict["rate"]
        elif total_iterations is not None and loop_index is not None:
            return iterations_string
        else:
            return "Please wait. Time is estimated..."

        return (iterations_string +
                f"Elapsed time: {int(elapsed_time)//60:02d}:{int(elapsed_time%60):02d}\n"
                f"Estimated remaining time: {int(remaining_time)//60:02d}:{int(remaining_time%60):02d}")

    def _get_progress_percentage(self) -> int:
        """
        Returns the progress percentage as integer.
        :return: Progress percentage.
        """
        loop_index = self.format_dict["n"]
        total_iterations = self.format_dict["total"]
        percentage = (loop_index / total_iterations) * 100 if total_iterations else 0

        return int(percentage)


class LoadingDialog(QDialog):
    """
    Class LoadingDialog represents a dialog which displays the label "Please wait..." only.
    It is used during execution of a thread, indicating the user that an action is currently
    being performed.

    The dialog cannot be closed by the user, it must be closed by calling the method close_dialog.

    Properties:
        content (LoadingWindowContent): The LoadingWindowContent instance for manipulating the contents.

    Methods:
        closeEvent (QEvent): Overrides QDialog.closeEvent to prevent that the dialog is closed by the user.
        close_dialog: Programmatically closes the dialog.

    Private Attributes:
        _programmatic_close (bool): Must be true in order for the dialog to be closeable.
        _action_label (QLabel): Displays the currently performed action.
        _status_label (QLabel): Displays the status message.
        _progress_bar (QProgressBar): Displays the current progress.
    """

    def __init__(self, parent: QMainWindow, action_text: str = None, content: LoadingDialogContent = None):
        """
        Constructs an instance of class LoadingDialog.
        :param parent: The parent QMainWindow instance.
        :param content: The LoadingWindowContent instance for manipulating the contents.
        """
        super().__init__(parent)
        self.content = content
        self._programmatic_close = False

        action_text = action_text if action_text is not None else "Action in progress"
        status_text = "Please wait..."
        self._action_label = QLabel(action_text, parent=self)
        self._action_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._status_label = QLabel(status_text, parent=self)
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setVisible(False)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)

        self.content.changed_action_text.connect(lambda string: self._action_label.setText(string))
        self.content.changed_status_text.connect(lambda string: self._status_label.setText(string))
        self.content.changed_progress_bar_value.connect(lambda integer: self._progress_bar.setValue(integer))
        self.content.changed_progress_bar_visibility.connect(lambda boolean: self._progress_bar.setVisible(boolean))

        self.setWindowTitle("Loading")
        self.setModal(True)
        layout = QVBoxLayout()
        layout.addWidget(self._action_label)
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress_bar)
        self.setLayout(layout)

    def closeEvent(self, event: QEvent):
        """
        Overrides QDialog.closeEvent to prevent that the dialog is closed by the user.

        :param event: Close event that is automatically passed to the method.
        """
        if self._programmatic_close:
            event.accept()
        else:
            event.ignore()

    def close_dialog(self):
        """
        Programmatically closes the dialog.
        """
        self._programmatic_close = True
        self.close()
