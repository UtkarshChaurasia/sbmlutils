"""
Helper functions and information for building DFBA models.
"""

from __future__ import print_function, absolute_import, division
from sbmlutils import factory as fac
from sbmlutils import comp


#################################################
# Builder constants
#################################################
MODEL_FRAMEWORK_FBA = 'fba'
MODEL_FRAMEWORK_ODE = 'ode'
# MODEL_FRAMEWORK_STOCHASTIC = 'stochastic'
# MODEL_FRAMEWORK_LOGICAL = 'logical'

MODEL_FRAMEWORKS = [
    MODEL_FRAMEWORK_FBA,
    MODEL_FRAMEWORK_ODE,
    # MODEL_FRAMEWORK_STOCHASTIC,
    # MODEL_FRAMEWORK_LOGICAL,
]

# dt parameter
DT_ID = 'dt'
DT_SIM = 0.1
DT_SBO = "SBO:0000346"

# flux bounds
LOWER_BOUND_DEFAULT = -1000
UPPER_BOUND_DEFAULT = 1000
ZERO_BOUND = 0
LOWER_BOUND_PREFIX = 'lb_'
UPPER_BOUND_PREFIX = 'ub_'
FLUX_BOUND_SBO = "SBO:0000625"

# update reactions
UPDATE_REACTION_PREFIX = "update_"
UPDATE_REACTION_SBO = "SBO:0000631"
UPDATE_PARAMETER_SBO = "SBO:0000613"

# exchange reactions
EXCHANGE_REACTION_PREFIX = 'EX_'
EXCHANGE_REACTION_SBO = "SBO:0000627"
EXCHANGE = 'exchange'
EXCHANGE_IMPORT = 'import'
EXCHANGE_EXPORT = 'export'
#################################################

def create_dt(step_size=DT_SIM, unit=None):
    """ Creates the dt parameter in the model.

    :param step_size:
    :type step_size:
    :param unit:
    :type unit:
    :return:
    :rtype:
    """
    return fac.Parameter(sid='dt', value=step_size, unit=unit, constant=True, sboTerm=DT_SBO)


def create_exchange_reaction(model, species_id, exchange_type=EXCHANGE, flux_unit=None):
    """ Factory method to create exchange reactions for species in the FBA model.

    Creates the exchange reaction, the upper and lower bounds,
    and the ports.

    :param model:
    :param species:
    :param reversible:
    :param flux_unit:
    :return:
    :rtype:
    """
    if exchange_type not in [EXCHANGE, EXCHANGE_IMPORT, EXCHANGE_EXPORT]:
        raise ValueError("Wrong exchange_type: {}".format(exchange_type))

    # id (e.g. EX_A)
    ex_rid = EXCHANGE_REACTION_PREFIX + species_id
    lb_id = LOWER_BOUND_PREFIX + ex_rid
    ub_id = UPPER_BOUND_PREFIX + ex_rid

    lb_value = LOWER_BOUND_DEFAULT
    ub_value = UPPER_BOUND_DEFAULT
    if exchange_type == EXCHANGE_IMPORT:
        # negative flux through exchange reaction
        ub_value = ZERO_BOUND
    if exchange_type == EXCHANGE_EXPORT:
        lb_value = ZERO_BOUND

    parameters = [
        fac.Parameter(sid=lb_id,
                      value=lb_value,
                      unit=flux_unit, constant=True, sboTerm=FLUX_BOUND_SBO),
        fac.Parameter(sid=ub_id,
                      value=ub_value,
                      unit=flux_unit, constant=True, sboTerm=FLUX_BOUND_SBO),
    ]
    fac.create_objects(model, parameters)

    # exchange reactions are all reversible (it depends on the bounds in which direction they operate)
    ex_r = fac.create_reaction(model, rid=ex_rid, reversible=True,
                               reactants={species_id: 1}, sboTerm=EXCHANGE_REACTION_SBO)

    # exchange bounds
    fac.set_flux_bounds(ex_r, lb=lb_id, ub=ub_id)

    # create ports
    comp.create_ports(model, portType=comp.PORT_TYPE_PORT,
                      idRefs=[ex_rid, lb_id, ub_id])

    return ex_r


def create_update_parameter(model, sid, unit):
    """ Creates the update parameter.

    :param model:
    :type model:
    :param sid:
    :type sid:
    :param unit:
    :type unit:
    :return:
    :rtype:
    """
    pid = EXCHANGE_REACTION_PREFIX + sid
    parameter = fac.Parameter(sid=pid, value=1.0, constant=True, unit=unit, sboTerm=UPDATE_PARAMETER_SBO)
    fac.create_objects(model, [parameter])
    # create port
    comp.create_ports(model, portType=comp.PORT_TYPE_PORT,
                      idRefs=[pid])


def create_update_reaction(model, sid, modifiers=[], formula=None):
    """ Creates the update reaction for a given species.

    :param model:
    :param sid:
    :param modifiers:
    :param formula:
    :return:
    :rtype:
    """
    rid = UPDATE_REACTION_PREFIX + sid

    if formula is None:
        formula = "-{}{}".format(EXCHANGE_REACTION_PREFIX, sid)

    fac.create_reaction(model, rid=rid, sboTerm=UPDATE_REACTION_PREFIX,
                       reactants={sid: 1}, modifiers=modifiers,
                       formula=formula)


def exchange_flux_bound_parameters(exchange_rids, unit):
    # exchange flux bounds
    parameters = []
    for ex_rid in exchange_rids:
        for bound_type in ['lb', 'ub']:
            if bound_type == 'lb':
                value = LOWER_BOUND_DEFAULT
            elif bound_type == 'ub':
                value = UPPER_BOUND_DEFAULT
            parameters.append(
                fac.Parameter(sid="{}_{}".format(bound_type, ex_rid), value=value, unit=unit, constant=False,
                              sboTerm=FLUX_BOUND_SBO)
            )
    return parameters
