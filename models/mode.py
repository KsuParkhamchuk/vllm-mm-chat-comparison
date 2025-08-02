from enum import Enum

class ChatMode(Enum):
    """
    Distinguishes between two application modes: 
        single - uses one model
        comparison - uses 2 models(bigger and smaller) and generates two separate results in parallel
    """
    SINGLE_MODE = 'sm'
    COMPARISON_MODE = 'cm'