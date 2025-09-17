import inspect
import sys


try:
    from pentesting.utils.logging import ConvenientLogging
except ImportError:
    from src.utils.logging import ConvenientLogging

class BaseClass:
    """
    Base class for all classes in the pentesting toolboxes.
    This class can be extended to provide common functionality or attributes.
    """

    def __init__(self, project_path):

        self.project_path = project_path
        # Automatically infer the calling class
        self.calling_class = self._get_calling_class_name()

        # Initialize logging with the calling class name
        self.convenient_logging = ConvenientLogging(self.project_path)
        self.logger = self.convenient_logging.getLogger(self.calling_class)

    def _get_calling_class_name(self):
        frame = inspect.currentframe()
        outer_frames = inspect.getouterframes(frame)
        # Skip the first frame (this __init__) and find the first class context
        for frame_info in outer_frames[1:]:
            cls = frame_info.frame.f_locals.get("self", None)
            if cls and hasattr(cls, "__class__") and cls.__class__.__name__ != "BaseClass":
                return cls.__class__.__name__
        return "UnknownClass"  # Fallback if no class context is found

    def error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs, stacklevel=2)

    def critical(self, *args, **kwargs):
        self.logger.critical(*args, **kwargs, stacklevel=2)
        sys.exit(-1)

    def warning(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs, stacklevel=2)

    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs, stacklevel=2)

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs, stacklevel=2)

    def console(self, *args, **kwargs):
        return self.convenient_logging.console