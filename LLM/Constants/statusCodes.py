from enum import Enum

class StatusCodes(Enum):
    REGULAR_MESSAGE = 1
    PROCESSING_DATA_DOWNLOAD = 2
    PARAMS_NEEDED = 3
    ERROR_WITH_DATA_DOWNLOAD = 4
    LLM_ERROR = 5