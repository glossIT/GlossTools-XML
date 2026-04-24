import logging
import threading
import traceback


# Initialize custom logging levels
USER_INTERACTION = 25
THREADED_FUNCTION = 26

logging.addLevelName(USER_INTERACTION, "USER_INTERACTION")
logging.addLevelName(THREADED_FUNCTION, "THREADED_FUNCTION")

def user_interaction(self, message, *args, **kwargs):
    if self.isEnabledFor(USER_INTERACTION):
        self._log(USER_INTERACTION, message, args, **kwargs)

def threaded_function(self, message, *args, **kwargs):
    if self.isEnabledFor(THREADED_FUNCTION):
        self._log(THREADED_FUNCTION, message, args, **kwargs)

logging.Logger.user_interaction = user_interaction
logging.Logger.threaded_function = threaded_function


class _Logger:
    """
    Class _Logger is used for logging exceptions, user interactions, and GUI function calls.
    The logger outputs to stderr and a log file on the hard disk.

    Attributes:
        logger (logging.Logger): Logger instance

    Methods:
        log_exception(Exception): Logs an exception.
        log_warning (str): Logs a warning message.
        log_error (str): Logs an error message.
        log_info (str): Logs an info message.
        log_debug (str): Logs a debug message.
        log_user_interaction (str): Logs a user interaction message.
        log_threaded_function (str): Logs a threaded function call.
    """
    def __init__(self, log_file='GlossConnector.log'):
        """
        Initializes the logger with a specified log file.
        :param log_file: The file where logs will be written.
        """
        self.logger = logging.getLogger("ExceptionLogger")
        logging_level = logging.WARNING
        self.logger.setLevel(logging_level)  # Set the logging level to ERROR

        # Create a file handler to write logs to a file
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging_level)

        # Create a stream handler to log to stderr
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging_level)

        # Create a formatter for timestamps and log messages
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s",
            datefmt="[%Y-%m-%d %H:%M:%S]"
        )
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        # Add the file handler to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def log_exception(self, exception):
        """
        Logs an exception with a timestamp.
        :param exception: The exception to log.
        """
        # Get the stack trace as a formatted string
        stack_trace = traceback.format_exc()
        # Indent the stack trace for better readability
        indented_stack_trace = "\n".join(["    " + line for line in stack_trace.splitlines()])
        self.logger.error("Exception occurred: %s\n%s", str(exception), indented_stack_trace)

    def log_warning(self, message):
        """
        Logs a message at the WARNING level.
        :param message: The message to log.
        """
        self.logger.warning(message)

    def log_error(self, message):
        """
        Logs a message at the ERROR level.
        :param message: The message to log.
        """
        self.logger.error(message)

    def log_info(self, message):
        """
        Logs a message at the INFO level.
        :param message: The message to log.
        """
        self.logger.info(message)

    def log_debug(self, message):
        """
        Logs a message at the DEBUG level.
        :param message: The message to log.
        """
        self.logger.debug(message)

    def log_user_interaction(self, message):
        """
        Logs user interactions at the custom USER_INTERACTION level.
        :param message: The message to log.
        """
        self.logger.user_interaction(message)

    def log_threaded_function(self, message):
        """
        Logs threaded function calls at the custom FUNCTION_CALL level.
        :param message: The message to log.
        """
        self.logger.threaded_function(message)


class LoggerSingleton:
    """
    Class LoggerSingleton encapsulates the _Logger in a global singleton.

    Attributes:
        logger: The logger object that is held by the singleton.

    Private Attributes:
        _instance: The global instance of the singleton.
        _lock: The mechanism ensuring thread safety.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LoggerSingleton, cls).__new__(cls)
                    cls._instance.logger = _Logger()
        return cls._instance