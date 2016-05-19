
# coding: utf-8

# # FBA Model
# This example demonstrates the creation of an SBML FBA model from scratch.

# In[1]:

#!!! DO NOT CHANGE !!! THIS FILE WAS CREATED AUTOMATICALLY FROM NOTEBOOKS !!! CHANGES WILL BE OVERWRITTEN !!! CHANGE CORRESPONDING NOTEBOOK FILE !!!
from __future__ import print_function

from sbmlutils import comp
from sbmlutils import sbmlio
from sbmlutils.factory import *
from libsbml import *


# ## Unit definitions
# Units for the model are defined in the following manner.

# In[2]:

# Unit definitions
main_units = {
    'time': 's',
    'extent': UNIT_KIND_ITEM,
    'substance': UNIT_KIND_ITEM,
    'length': 'm',
    'area': 'm2',
    'volume': 'm3',
}
units = {
    's': [(UNIT_KIND_SECOND, 1.0)],
    'kg': [(UNIT_KIND_KILOGRAM, 1.0)],
    'm': [(UNIT_KIND_METRE, 1.0)],
    'm2': [(UNIT_KIND_METRE, 2.0)],
    'm3': [(UNIT_KIND_METRE, 3.0)],
    'mM': [(UNIT_KIND_MOLE, 1.0, 0),
           (UNIT_KIND_METRE, -3.0)],
    'per_s': [(UNIT_KIND_SECOND, -1.0)],
    'item_per_s': [(UNIT_KIND_ITEM, 1.0),
                   (UNIT_KIND_SECOND, -1.0)],
    'item_per_m3': [(UNIT_KIND_ITEM, 1.0),
                    (UNIT_KIND_METRE, -3.0)],
}

UNIT_AMOUNT = UNIT_KIND_ITEM
UNIT_AREA = 'm2'
UNIT_VOLUME = 'm3'
UNIT_CONCENTRATION = 'item_per_m3'
UNIT_FLUX = 'item_per_s'


# ## Model building
# Creation of FBA model using multiple packages (`comp`, `fbc`).

# In[3]:

# Create the FBA model
sbmlns = SBMLNamespaces(3, 1)
sbmlns.addPackageNamespace("fbc", 2)
sbmlns.addPackageNamespace("comp", 1)

doc_fba = SBMLDocument(sbmlns)
doc_fba.setPackageRequired("comp", True)
mdoc = doc_fba.getPlugin("comp")
doc_fba.setPackageRequired("fbc", False)
model = doc_fba.createModel()
mplugin = model.getPlugin("fbc")
mplugin.setStrict(False)

# model
model.setId('toy_fba')
model.setName('FBA submodel')
model.setSBOTerm(comp.SBO_FLUX_BALANCE_FRAMEWORK)

create_unit_definitions(model, units)
set_main_units(model, main_units)

# compartments
compartments = [
    {A_ID: 'extern', A_VALUE: 1.0, A_UNIT: UNIT_VOLUME, A_NAME: 'external compartment', A_SPATIAL_DIMENSION: 3},
    {A_ID: 'cell', A_VALUE: 1.0, A_UNIT: UNIT_VOLUME, A_NAME: 'cell', A_SPATIAL_DIMENSION: 3},
    {A_ID: 'membrane', A_VALUE: 1.0, A_UNIT: UNIT_AREA, A_NAME: 'membrane', A_SPATIAL_DIMENSION: 2}
]
create_compartments(model, compartments)

# species
species = [
    # external
    {A_ID: 'A', A_NAME: "A", A_VALUE: 10, A_UNIT: UNIT_AMOUNT, A_HAS_ONLY_SUBSTANCE_UNITS: True,
     A_COMPARTMENT: "extern", A_BOUNDARY_CONDITION: True},
    {A_ID: 'C', A_NAME: "C", A_VALUE: 0, A_UNIT: UNIT_AMOUNT, A_HAS_ONLY_SUBSTANCE_UNITS: True,
     A_COMPARTMENT: "extern", A_BOUNDARY_CONDITION: True},
    # internal
    {A_ID: 'B1', A_NAME: "B1", A_VALUE: 0, A_UNIT: UNIT_AMOUNT, A_HAS_ONLY_SUBSTANCE_UNITS: True,
     A_COMPARTMENT: "cell"},
    {A_ID: 'B2', A_NAME: "B2", A_VALUE: 0, A_UNIT: UNIT_AMOUNT, A_HAS_ONLY_SUBSTANCE_UNITS: True,
     A_COMPARTMENT: "cell"},
]
create_species(model, species)

# parameters
parameters = [
    # bounds
    {A_ID: "ub_R1", A_NAME: "ub R1", A_VALUE: 1.0, A_UNIT: UNIT_FLUX, A_CONSTANT: False},
    {A_ID: "lb", A_NAME: "lower bound", A_VALUE: 0.0, A_UNIT: UNIT_FLUX, A_CONSTANT: True},
    {A_ID: "ub", A_NAME: "upper bound", A_VALUE: 1000.0, A_UNIT: UNIT_FLUX, A_CONSTANT: True},
]
create_parameters(model, parameters)

# reactions
r1 = create_reaction(model, rid="R1", name="A import (R1)", fast=False, reversible=True,
                       reactants={"A": 1}, products={"B1": 1}, compartment='membrane')
r2 = create_reaction(model, rid="R2", name="B1 <-> B2 (R2)", fast=False, reversible=True,
                       reactants={"B1": 1}, products={"B2": 1}, compartment='cell')
r3 = create_reaction(model, rid="R3", name="B2 export (R3)", fast=False, reversible=True,
                       reactants={"B2": 1}, products={"C": 1}, compartment='membrane')

# flux bounds
set_flux_bounds(r1, lb="lb", ub="ub_R1")
set_flux_bounds(r2, lb="lb", ub="ub")
set_flux_bounds(r3, lb="lb", ub="ub")

# objective function
create_objective(mplugin, oid="R3_maximize", otype="maximize", fluxObjectives={"R3": 1.0})

# create ports
comp._create_port(model, pid="R3_port", idRef="R3", portType=comp.PORT_TYPE_PORT)
comp._create_port(model, pid="ub_R1_port", idRef="ub_R1", portType=comp.PORT_TYPE_PORT)
comp._create_port(model, pid="cell_port", idRef="cell", portType=comp.PORT_TYPE_PORT)
comp._create_port(model, pid="extern_port", idRef="extern", portType=comp.PORT_TYPE_PORT)
comp._create_port(model, pid="C_port", idRef="C", portType=comp.PORT_TYPE_PORT)

# write SBML file
sbml_file = "fba_example.xml"
sbmlio.write_and_check(doc_fba, sbml_file)


# In[4]:


