# -------------------------------------------------
# File: src/pixel/traits.py
#
# High-level evolutionary traits and their prerequisites.
# These are not yet wired into the simulation logic, but provide
# a central definition that metabolism/genome modules can use to
# unlock capabilities over evolutionary time.
# -------------------------------------------------

from typing import Dict, List


TRAIT_PREREQS: Dict[str, List[str]] = {
    "radiation_resistance": ["cell_wall", "epigenetic_modification"],
    "heat_resistance": ["antifreeze_proteins", "thermoregulation"],
    # unicellular basics
    "cilia": [],
    "flagella": [],
    "cell_wall": [],
    "pilli": [],  # aderenza e scambio genetico
    # metabolic pathways
    "photosynthesis": ["chloroplasts"],
    "chemosynthesis": ["cell_wall"],
    "nitrogen_fixation": ["roots"],
    # epigenetic mechanisms
    "epigenetic_modification": ["chemosynthesis"],
    "horizontal_gene_transfer": ["pilli"],
    # plant and fungal traits
    "chloroplasts": ["cell_wall"],
    "stationary": ["cell_wall"],
    "roots": ["stationary"],
    "leaves": ["chloroplasts"],
    "stomata": ["leaves"],
    "woody_tissue": ["vascular_system"],
    "vascular_system": ["roots", "leaves"],
    "bark": ["woody_tissue"],
    "flowering": ["woody_tissue"],
    "fruiting_body": ["flowering"],
    "spores": ["stationary"],
    "mycelium": ["spores"],
    # basic animal traits
    "muscle": ["cilia", "flagella"],
    "skeletal_system": ["muscle"],
    "exoskeleton": ["cell_wall"],
    "endoskeleton": ["skeletal_system"],
    # internal organs
    "heart": ["endoskeleton"],
    "blood_vessels": ["heart"],
    "digestive_system": ["cell_wall"],
    "liver": ["digestive_system"],
    "kidneys": ["digestive_system"],
    "excretory_system": ["kidneys"],
    "respiratory_organs": ["digestive_system"],
    "gills": ["respiratory_organs"],
    "lungs": ["respiratory_organs"],
    "endocrine_system": ["nervous_system"],
    "reproductive_system": ["multicell"],
    # nervous system and sensory
    "nervous_system": ["muscle"],
    "sensory_organs": ["nervous_system"],
    "eyes": ["sensory_organs"],
    "ears": ["sensory_organs"],
    "olfactory": ["sensory_organs"],
    "taste_buds": ["sensory_organs"],
    "lateral_line": ["sensory_organs"],
    "ampullae_of_lorenzini": ["sensory_organs"],
    # brain architecture
    "ganglia": ["nervous_system"],
    "brainstem": ["ganglia"],
    "cerebellum": ["brainstem"],
    "limbic_system": ["brainstem"],
    "cerebral_cortex": ["limbic_system"],
    "neocortex": ["cerebral_cortex"],
    # immunity
    "innate_immunity": ["multicell"],
    "adaptive_immunity": ["innate_immunity"],
    # locomotion
    "fins": ["muscle"],
    "legs": ["muscle"],
    "wings": ["muscle", "respiratory_organs"],
    "tube_feet": ["muscle"],
    "moult": ["exoskeleton"],
    "shedding_skin": ["endoskeleton"],
    # antifreeze and temperature
    "antifreeze_proteins": ["digestive_system"],
    "thermoregulation": ["endocrine_system"],
    "cold_tolerance": ["antifreeze_proteins"],
    # feeding strategies
    "herbivore": ["digestive_system", "chloroplasts"],
    "carnivore": ["digestive_system", "muscle"],
    "omnivore": ["herbivore", "carnivore"],
    "filter_feeding": ["digestive_system"],
    "detritivore": ["digestive_system"],
    "parasitic": ["digestive_system"],
    # chemical warfare
    "venom_glands": ["carnivore"],
    "fangs": ["venom_glands", "sensory_organs"],
    "spitting_venom": ["venom_glands", "fangs"],
    "toxic_skin": ["venom_glands"],
    "acid_secretion": ["digestive_system"],
    # physical defenses
    "spines": ["exoskeleton"],
    "shell": ["exoskeleton"],
    "quills": ["exoskeleton"],
    "horns": ["endoskeleton"],
    "claws": ["muscle"],
    "talons": ["wings", "muscle"],
    "beak": ["sensory_organs", "muscle"],
    "camouflage": ["sensory_organs"],
    "mimicry": ["camouflage", "nervous_system"],
    "bioluminescence": ["sensory_organs"],
    "ink_cloud": ["nervous_system"],
    "autotomy": ["exoskeleton"],
    "regeneration": ["multicell"],
    "electric_organs": ["muscle", "nervous_system"],
    # reproduction and lifecycle
    "sexual_dimorphism": ["multicell"],
    "parthenogenesis": ["multicell"],
    "metamorphosis": ["reproductive_system"],
    "hibernation": ["thermoregulation"],
    "estivation": ["thermoregulation"],
    "torpor": ["thermoregulation"],
    "diapause": ["reproductive_system"],
    "migration": ["sensory_organs", "muscle"],
    # social and cognition
    "vocal_cords": ["sensory_organs", "nervous_system"],
    "song": ["vocal_cords"],
    "language": ["neocortex", "vocal_cords"],
    "tool_use": ["neocortex"],
    "culture": ["language"],
    "social_structure": ["cooperation"],
    "pack_hunting": ["social_structure", "carnivore"],
    "schooling": ["social_structure", "vocal_cords"],
}


REPRODUCTION_PREREQS: Dict[str, List[str]] = {
    # Formazione di colonie semplici (non ancora multicellulari)
    "aggregation": [],
    # Organizzazione cellulare stabile
    "multicell": ["aggregation"],
    "reproductive_system": ["multicell"],
    "sexual_dimorphism": ["multicell"],
    "parthenogenesis": ["multicell"],
    "metamorphosis": ["reproductive_system"],
    "diapause": ["reproductive_system"],
}


def all_prereqs_met(trait: str, owned: List[str], prereq_map: Dict[str, List[str]]) -> bool:
    """Return True if all prerequisites of trait are contained in owned."""
    reqs = prereq_map.get(trait, [])
    return all(r in owned for r in reqs)

