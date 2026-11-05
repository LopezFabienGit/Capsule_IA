"""Who can speak in a video, and how they are named in the text and in the project file."""

from enum import Enum


class Speaker(str, Enum):
    """Character identifier; its value is also the key of the mouth envelopes in the alignment file."""

    PERSON_1 = "person_1"
    PERSON_2 = "person_2"
    GOAT = "goat"


# label at the start of a line of the text (duo mode)
DIALOGUE_LABELS = {"Person_1": Speaker.PERSON_1, "Person_2": Speaker.PERSON_2}

# value of « presentateur = » in the project file (solo mode)
PRESENTER_NAMES = {**DIALOGUE_LABELS, "Chevre": Speaker.GOAT}
