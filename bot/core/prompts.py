bank = {}

version_1 = "v1"
version_2 = "v2"

active_version = version_2

bank[version_1] = """
Before answering any question, say woof.
"""

bank[version_2] = """
End each response with - Moo
"""

def get_assistant_prompt() -> str:
    return bank[active_version]