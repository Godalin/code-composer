from pprint import pprint
from code_composer.config_loader import *

pprint(load_scales())
pprint(load_rhythm_patterns("4/4"))
pprint(load_rhythm_patterns("3/4"))

for progression in list_available_progression_libs():
    pprint(progression)
    pprint(load_progressions(progression))

pprint(load_motifs())


print("\nbass lib")
pprint(load_bass_patterns("4/4"))
pprint(load_bass_patterns("3/4"))

print("\nstyle lib")
for style in list_available_styles():
    pprint(style)
    style = load_style(style)
    pprint(style)
    pprint(style.rhythm_weights)
