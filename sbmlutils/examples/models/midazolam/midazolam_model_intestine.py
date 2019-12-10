from sbmlutils.modelcreator import creator
from sbmlutils.factory import *
from sbmlutils.units import *
from sbmlutils.annotation.sbo import *


mid = "midazolam_model_intestine"

model_units = ModelUnits(
    time=UNIT_min,
    extent=UNIT_mmole,
    substance=UNIT_mmole,
    length=UNIT_m,
    area=UNIT_m2,
    volume=UNIT_KIND_LITRE)

units = [
    UNIT_mmole,
    UNIT_min,
    UNIT_m,
    UNIT_m2,
    UNIT_mM,
    UNIT_mmole_per_min,
]

compartments = [
    Compartment("Vex", 1.0, name="stomach", sboTerm=SBO_PHYSICAL_COMPARTMENT,
                unit=UNIT_KIND_LITRE, ),
    Compartment("Vint", 1, name="intestine", sboTerm=SBO_PHYSICAL_COMPARTMENT,
                unit=UNIT_KIND_LITRE),
]

species = [
    Species("mid_ex", initialConcentration=0.0, name="midazolam (extern)",
            compartment="Vex", substanceUnit=UNIT_mmole, hasOnlySubstanceUnits=False),
    Species("mid1oh_ex", initialConcentration=0.0, name="1-hydroxy-midazolam (extern)",
            compartment="Vex", substanceUnit=UNIT_mmole, hasOnlySubstanceUnits=False),
    Species("mid", initialConcentration=0.0, name="midazolam (intestine)",
            compartment="Vint", substanceUnit=UNIT_mmole, hasOnlySubstanceUnits=False),
    Species("mid1oh", initialConcentration=0.0, name="1-hydroxy-midazolam (intestine)",
            compartment="Vint", substanceUnit=UNIT_mmole, hasOnlySubstanceUnits=False),
]

reactions = [
    Reaction("MIDIM",
             equation="mid_ex <-> mid",
             sboTerm=SBO_TRANSPORT_REACTION,
             pars=[
                 Parameter("MIDIM_Vmax", 0.5, unit=UNIT_mmole_per_min),
                 Parameter("MIDIM_Km", 4.0E-3, unit=UNIT_mM),
             ],
             formula=("MIDIM_Vmax * (mid_ex/(mid_ex + MIDIM_Km))", UNIT_mmole_per_min)),

    Reaction("MIDOH",
             equation="mid -> mid1oh",
             sboTerm=SBO_BIOCHEMICAL_REACTION,
             pars=[
                       Parameter("MIDOH_Vmax", 0.5, unit=UNIT_mmole_per_min),   #Thummel1996; 500 - 800 pmol/min/mg
                       Parameter("MIDOH_Km", 4.0E-3, unit=UNIT_mM),             #Thummel1996; 3.3 - 4.3 umol/l
                   ],
             formula=("MIDOH_Vmax * (mid/(mid + MIDOH_Km))", UNIT_mmole_per_min),
             ),

    Reaction("MID1OHEX",
             equation="mid1oh <-> mid1oh_ex",
             sboTerm=SBO_TRANSPORT_REACTION,
             pars=[
               Parameter("MID1OHBL_Vmax", 0.5, unit=UNIT_mmole_per_min),
               Parameter("MID1OHBL_Km", 4.0E-3, unit=UNIT_mM),
             ],
             formula=("MID1OHBL_Vmax * (mid1oh/(mid1oh + MID1OHBL_Km))", UNIT_mmole_per_min),
             ),
]

def create_model(target_dir):
    return creator.create_model(
        modules=['midazolam_model_intestine'],
        target_dir=target_dir,
        create_report=True
    )


if __name__ == "__main__":
    create_model(target_dir=".")