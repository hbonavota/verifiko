from enum import Enum


class TargetType(str, Enum):
    URL = "URL"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
