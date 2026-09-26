"""The fixed set of soundboard slots and their default physical keys."""

# slot id (legacy numpad virtual-key code, kept for config compatibility) -> label
SLOTS = [(111, "/"), (106, "*"), (109, "-"),
         (103, "7"), (104, "8"), (105, "9"), (107, "+"),
         (100, "4"), (101, "5"), (102, "6"),
         (97, "1"), (98, "2"), (99, "3"),
         (96, "0")]
SLOT_IDS = [vk for vk, _ in SLOTS]

# default physical keys as (scancode, extended)
DEFAULT_KEYS = {96: (0x52, 0), 97: (0x4F, 0), 98: (0x50, 0), 99: (0x51, 0), 100: (0x4B, 0),
                101: (0x4C, 0), 102: (0x4D, 0), 103: (0x47, 0), 104: (0x48, 0), 105: (0x49, 0),
                111: (0x35, 1), 106: (0x37, 0), 109: (0x4A, 0), 107: (0x4E, 0)}
DEFAULT_STOP = (0x53, 0)

MODES = ("normal", "hold", "loop")
NO_KEY = (0, 0)
ESCAPE_KEY = (1, 0)
