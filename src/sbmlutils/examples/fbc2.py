"""FBA example with exchange reactions & boundaryCondition=True."""
from sbmlutils.examples import EXAMPLE_RESULTS_DIR, templates
from sbmlutils.factory import *
from sbmlutils.metadata.sbo import *
from sbmlutils.units import *


class U(Units):
    """UnitDefinitions."""

    hr = UnitDefinition("hr")
    mmole = UnitDefinition("mmole")
    m2 = UnitDefinition("m2", "meter^2")
    mmole_per_hr = UnitDefinition("mmole_per_hr", "mmole/hr")


_m = Model(
    "fbc_example2",
    packages=["fbc"],
    creators=templates.creators,
    notes="""
    # FBC example with exchange reactions and `boundaryCondition=True`
    ## Description
    Example creating fbc model
    """
    + templates.terms_of_use,
    units=U,
    model_units=ModelUnits(
        time=U.hr,
        extent=U.mmole,
        substance=U.mmole,
        length=U.meter,
        area=U.m2,
        volume=U.liter,
    ),
)
_m.compartments = [
    Compartment(
        sid="bioreactor",
        value=1.0,
        unit=U.liter,
        constant=True,
        name="bioreactor",
        spatialDimensions=3,
    ),
]
_m.species = [
    Species(
        sid="Glcxt",
        name="glucose",
        initialConcentration=0.0,
        substanceUnit=U.mmole,
        hasOnlySubstanceUnits=False,
        compartment="bioreactor",
    ),
    Species(
        sid="Ac",
        name="acetate",
        initialConcentration=0.0,
        substanceUnit=U.mmole,
        hasOnlySubstanceUnits=False,
        compartment="bioreactor",
        boundaryCondition=True,
    ),
    Species(
        sid="O2",
        name="oxygen",
        initialConcentration=0.0,
        substanceUnit=U.mmole,
        hasOnlySubstanceUnits=False,
        compartment="bioreactor",
    ),
    Species(
        sid="X",
        name="biomass",
        initialConcentration=0.0,
        substanceUnit=U.mmole,
        hasOnlySubstanceUnits=False,
        compartment="bioreactor",
        boundaryCondition=True,
    ),
]
# -----------------------------------------------------------------------------
# Parameters
# -----------------------------------------------------------------------------
FLUX_BOUND_ZERO = "zero"
FLUX_BOUND_PLUS_INF = "ub_inf"
FLUX_BOUND_PLUS_1000 = "ub_1000"
FLUX_BOUND_MINUS_INF = "lb_inf"
FLUX_BOUND_MINUS_1000 = "lb_1000"

FLUX_BOUND_GLC_IMPORT = "glc_import"
FLUX_BOUND_O2_IMPORT = "o2_import"

_m.parameters = [
    # bounds
    Parameter(
        sid=FLUX_BOUND_ZERO,
        name="zero bound",
        value=0.0,
        unit=U.mmole_per_hr,
        constant=True,
        sboTerm=SBO.FLUX_BOUND,
    ),
    Parameter(
        sid=FLUX_BOUND_PLUS_INF,
        name="default upper bound",
        value=float("Inf"),
        unit=U.mmole_per_hr,
        constant=True,
        sboTerm=SBO.FLUX_BOUND,
    ),
    Parameter(
        sid=FLUX_BOUND_MINUS_INF,
        name="default lower bound",
        value=-float("Inf"),
        unit=U.mmole_per_hr,
        constant=True,
        sboTerm=SBO.FLUX_BOUND,
    ),
    Parameter(
        sid=FLUX_BOUND_GLC_IMPORT,
        name="glc import bound",
        value=-15,
        unit=U.mmole_per_hr,
        constant=True,
        sboTerm=SBO.FLUX_BOUND,
    ),
    Parameter(
        sid=FLUX_BOUND_O2_IMPORT,
        name="o2 import bound",
        value=-10,
        unit=U.mmole_per_hr,
        constant=True,
        sboTerm=SBO.FLUX_BOUND,
    ),
]

# -----------------------------------------------------------------------------
# Reactions
# -----------------------------------------------------------------------------
# metabolic reactions
_m.reactions = [
    Reaction(
        sid="v1",
        name="v1 (39.43 Ac + 35 O2 -> X)",
        equation="39.43 Ac + 35 O2 => X []",
    ),
    Reaction(
        sid="v2",
        name="v2 (9.46 Glcxt + 12.92 O2 -> X)",
        equation="9.46 Glcxt + 12.92 O2 => X []",
    ),
    Reaction(
        sid="v3",
        name="v3 (9.84 Glcxt + 12.73 O2 -> 1.24 Ac + X)",
        equation="9.84 Glcxt + 12.73 O2 => 1.24 Ac + X []",
    ),
    Reaction(
        sid="v4",
        name="v4 (19.23 Glcxt -> 12.12 Ac + X)",
        equation="19.23 Glcxt => 12.12 Ac + X []",
    ),
]

for rt in _m.reactions:
    if rt.sid in ["v1", "v2", "v3", "v4"]:
        rt.compartment = "bioreactor"
        rt.lowerFluxBound = FLUX_BOUND_ZERO
        rt.upperFluxBound = FLUX_BOUND_PLUS_INF

# exchange reactions
_m.reactions.extend(
    [
        ExchangeReaction(
            species_id="Glcxt",
            lowerFluxBound=FLUX_BOUND_GLC_IMPORT,
            upperFluxBound=FLUX_BOUND_ZERO,
        ),
        ExchangeReaction(
            species_id="O2",
            lowerFluxBound=FLUX_BOUND_O2_IMPORT,
            upperFluxBound=FLUX_BOUND_ZERO,
        ),
    ]
)


# -----------------------------------------------------------------------------
# Objective function
# -----------------------------------------------------------------------------
_m.objectives = [
    Objective(
        sid="biomass_max",
        objectiveType="maximize",
        active=True,
        fluxObjectives={"v1": 1.0, "v2": 1.0, "v3": 1.0, "v4": 1.0},
    )
]


def create(tmp: bool = False) -> None:
    """Create model."""
    create_model(
        models=_m,
        output_dir=EXAMPLE_RESULTS_DIR,
        tmp=tmp,
    )


if __name__ == "__main__":
    create()
