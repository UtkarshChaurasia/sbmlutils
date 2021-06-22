"""Creates dictionary of information for given model.

The model dictionary can be used for rendering the HTML report.
The information can be serialized to JSON for later rendering in web app.
"""
import hashlib
import json
from pathlib import Path
import pprint
from typing import Any, Dict, Union, List, Optional

import libsbml
import numpy as np

from sbmlutils.io import read_sbml
from sbmlutils.metadata import miriam
from src.sbmlutils.report import units
from src.sbmlutils.report.mathml import astnode_to_latex

# FIXME: support multiple model definitions in comp; test with comp model;
# TODO: inject links
# FIXME: cleanup mypy & other issues


def _get_sbase_attribute(sbase: libsbml.SBase, key: str) -> Optional[Any]:
    """Get SBase attribute."""
    key = f"{key[0].upper()}{key[1:]}"
    if getattr(sbase, f"isSet{key}")():
        return getattr(sbase, f"get{key}")()
    else:
        return None


class SBMLDocumentInfo:
    """Class for collecting information in JSON on an SBMLDocument to create reports.

    A single document can contain multiple models or be a hierarchical
    model (comp package).
    """

    def __init__(
        self,
        doc: libsbml.SBMLDocument,
    ):
        """Initialize SBMLDocumentInfo."""
        self.doc: libsbml.SBMLDocument = doc
        self.info = self.create_info()

    @staticmethod
    def from_sbml(source: Union[Path, str]) -> 'SBMLDocumentInfo':
        """Read model info from SBML."""
        doc: libsbml.SBMLDocument = read_sbml(source)
        return SBMLDocumentInfo(doc=doc)

    def __repr__(self) -> str:
        """Get string representation."""
        return f"SBMLInfo({self.doc})"

    def __str__(self) -> str:
        """Get string."""
        return pprint.pformat(self.info, indent=2)

    def to_json(self) -> str:
        """Serialize to JSON representation."""
        return json.dumps(self.info, indent=2)

    def create_info(self) -> Dict[str, Any]:
        """Create information dictionary for report rendering."""

        d = {
            "doc": self.document(doc=self.doc),
            **self.model_definitions(),
        }

        if self.doc.isSetModel():
            d["model"] = self.model_dict(self.doc.getModel())
        else:
            d["model"] = None



        return d

    def model_dict(self, model: Union[libsbml.Model, libsbml.ModelDefinition]):
        """Creates information for a given model."""
        assignments = self._create_assignment_map(model=model)

        rules = self.rules(model=model)
        d = {
            # sbml model information
            "model": self.model(model=model),

            # core
            "functionDefinitions": self.function_definitions(model=model),
            "unitDefinitions": self.unit_definitions(model=model),
            "compartments": self.compartments(model=model, assignments=assignments),
            "species": self.species(model=model, assignments=assignments),
            "parameters": self.parameters(model=model, assignments=assignments),
            "initialAssignments": self.initial_assignments(model=model),
            "assignmentRules": rules["assignmentRules"],
            "rateRules": rules["rateRules"],
            "algebraicRules": rules["algebraicRules"],
            "constraints": self.constraints(model=model),
            "reactions": self.reactions(model=model),
            "events": self.events(model=model),

            # comp
            "submodels": self.submodels(model=model),
            "ports": self.ports(model=model),

            # fbc
            "geneProducts": self.gene_products(model=model),
            "objectives": self.objectives(model=model),
        }
        return d

    @staticmethod
    def _sbaseref(sbaseref: libsbml.SBaseRef) -> Optional[Dict]:
        """Format the SBaseRef instance.

        :param sbaseref: SBaseRef instance
        :return: Dictionary containing formatted SBaseRef instance's data
        """

        if sbaseref.isSetPortRef():
            return {
                "type": "port_ref",
                "value": sbaseref.getPortRef()
            }
        elif sbaseref.isSetIdRef():
            return {
                "type": "id_ref",
                "value": sbaseref.getIdRef()
            }
        elif sbaseref.isSetUnitRef():
            return {
                "type": "unit_ref",
                "value": sbaseref.getUnitRef()
            }
        elif sbaseref.isSetMetaIdRef():
            return {
                "type": "meta_ID_ref",
                "value": sbaseref.getMetaIdRef()
            }
        return None

    def _create_assignment_map(self, model: libsbml.Model) -> Dict:
        """Create dictionary of symbols:assignment for symbols in model.

        This allows to lookup assignments for a given variable.

        :return: assignment dictionary for model
        """
        assignments: Dict[str, Dict] = {}

        initial_assignment: libsbml.InitialAssignment
        for initial_assignment in model.getListOfInitialAssignments():
            pk_symbol = initial_assignment.getSymbol() if initial_assignment.isSetSymbol() else None
            pk = self._set_pk(initial_assignment)
            if pk_symbol:
                assignments[pk_symbol] = {
                    'pk': pk,
                    'type': 'initialAssignment',
                }

        rule: libsbml.Rule
        for rule in model.getListOfRules():
            pk_symbol = rule.getVariable() if rule.isSetVariable() else None
            pk = self._set_pk(rule)
            if pk_symbol:
                typecode = rule.getTypeCode()
                if typecode == libsbml.SBML_ASSIGNMENT_RULE:
                    sbml_type = "assignmentRule"
                elif typecode == libsbml.SBML_RATE_RULE:
                    sbml_type = "rateRule"
                elif typecode == libsbml.SBML_ALGEBRAIC_RULE:
                    sbml_type = "algebraicRule"
                else:
                    raise ValueError(f"Unsupported rule type: {typecode}")
                assignments[pk_symbol] = {
                    'pk': pk,
                    'type': sbml_type,
                }

        return assignments

    @staticmethod
    def _sbml_type(sbase: libsbml.SBase) -> str:
        class_name = str(sbase.__class__)[16:-2]
        return class_name

    @staticmethod
    def _set_pk(sbase: libsbml.SBase) -> str:
        """Calculate primary key."""
        if not hasattr(sbase, "pk"):
            pk: str
            if sbase.isSetId():
                pk = sbase.getId()
            elif sbase.isSetMetaId():
                pk = sbase.getMetaId()
            else:
                xml = sbase.toSBML()
                pk = SBMLDocumentInfo._uuid(xml)
            sbase.pk = pk
        return sbase.pk

    @staticmethod
    def _uuid(xml: str) -> str:
        """Generate unique identifier.

        Sha256 digest of the identifier (mostly the xml string).
        """
        return str(hashlib.sha256(xml.encode('utf-8')).digest())

    @classmethod
    def sbase_dict(cls, sbase: libsbml.SBase) -> Dict[str, Any]:
        """Info dictionary for SBase.

        :param sbase: SBase instance for which info dictionary is to be created
        :return info dictionary for item
        """
        pk = cls._set_pk(sbase)
        d = {
            "pk": pk,
            "sbmlType": cls._sbml_type(sbase),
            "id": sbase.getId() if sbase.isSetId() else None,
            "metaId": sbase.getMetaId() if sbase.isSetMetaId() else None,
            "name": sbase.getName() if sbase.isSetName() else None,
            "sbo": sbase.getSBOTermID() if sbase.isSetSBOTerm() else None,
            "cvterms": cls.cvterms(sbase),
            "history": cls.model_history(sbase),
            "notes": sbase.getNotesString() if sbase.isSetNotes() else None,
        }

        if sbase.getTypeCode() in {libsbml.SBML_DOCUMENT, libsbml.SBML_MODEL}:
            d['xml'] = None
        else:
            d['xml'] = sbase.toSBML()

        # comp
        item_comp = sbase.getPlugin("comp")
        if item_comp and type(item_comp) == libsbml.CompSBasePlugin:
            # ReplacedBy
            if item_comp.isSetReplacedBy():
                replaced_by = item_comp.getReplacedBy()
                submodel_ref = replaced_by.getSubmodelRef()
                d["replacedBy"] = {
                    "submodelRef": submodel_ref,
                    "replacedBySbaseref": cls._sbaseref(replaced_by)
                }
            else:
                d["replacedBy"] = None

            # ListOfReplacedElements
            if item_comp.getNumReplacedElements() > 0:
                replaced_elements = []
                for rep_el in item_comp.getListOfReplacedElements():
                    submodel_ref = rep_el.getSubmodelRef()
                    replaced_elements.append({
                        "submodelRef": submodel_ref,
                        "replacedElementSbaseref": cls._sbaseref(rep_el)
                    })

                d["replacedElements"] = replaced_elements
            else:
                d["replacedElements"] = None

        # distrib
        sbml_distrib: libsbml.DistribSBasePlugin = sbase.getPlugin("distrib")
        if sbml_distrib and isinstance(sbml_distrib, libsbml.DistribSBasePlugin):
            d["uncertainties"] = []
            for uncertainty in sbml_distrib.getListOfUncertainties():
                u_dict = SBMLDocumentInfo.sbase_dict(uncertainty)

                u_dict["uncert_parameters"] = []
                upar: libsbml.UncertParameter
                for upar in uncertainty.getListOfUncertParameters():
                    param_dict = {
                        "var": upar.getVar() if upar.isSetVar() else None,
                        "value": upar.getValue() if upar.isSetValue() else None,
                        "units": upar.getUnits() if upar.isSetUnits() else None,
                        "type": upar.getTypeAsString() if upar.isSetType() else None,
                        "definition_url": upar.getDefinitionURL() if upar.isSetDefinitionURL() else None,
                        "math": astnode_to_latex(upar.getMath(), model=sbase.getModel()) if upar.isSetMath() else None
                    }

                    u_dict["uncert_parameters"].append(param_dict)

                d["uncertainties"].append(u_dict)

        return d

    def sbaseref_dict(self, sbaseref: libsbml.SBaseRef) -> Dict[str, Any]:
        """Info dictionary for SBaseRef.

        :param sbaseref: SBaseRef instance for which information dictionary is created
        :return: information dictionary for SBaseRef
        """
        d = self.sbase_dict(sbaseref)

        d["portRef"] = sbaseref.getPortRef() if sbaseref.isSetPortRef() else None
        d["idRef"] = sbaseref.getIdRef() if sbaseref.isSetIdRef() else None
        d["unitRef"] = sbaseref.getUnitRef() if sbaseref.isSetUnitRef() else None
        d["metaIdRef"] = sbaseref.getMetaIdRef() if sbaseref.isSetMetaIdRef() else None
        d["referencedElement"] = {
            "element": type(sbaseref.getReferencedElement()).__name__,
            "elementId": sbaseref.getReferencedElement().getId()
        }

        return d

    @classmethod
    def cvterms(cls, sbase: libsbml.SBase) -> Optional[List]:
        """Parse CVTerms information.

        :param sbase: SBase instance
        """
        if not sbase.isSetAnnotation():
            return None

        cvterms = []
        for kcv in range(sbase.getNumCVTerms()):
            cv: libsbml.CVTerm = sbase.getCVTerm(kcv)
            # qualifier
            q_type = cv.getQualifierType()
            if q_type == libsbml.MODEL_QUALIFIER:
                qualifier = miriam.ModelQualifierType[
                    cv.getModelQualifierType()
                ]
            elif q_type == libsbml.BIOLOGICAL_QUALIFIER:
                qualifier = miriam.BiologicalQualifierType[
                    cv.getBiologicalQualifierType()
                ]
            else:
                raise ValueError(f"Unsupported qualifier type: '{q_type}'")

            resources = [
                cv.getResourceURI(k) for k in range(cv.getNumResources())
            ]
            cvterms.append({
                "qualifier": qualifier,
                "resources": resources,
            })

        return cvterms

    @classmethod
    def model_history(cls, sbase: libsbml.SBase) -> Optional[Dict]:
        """Parse model history information.

        :return
        """

        if sbase.isSetModelHistory():
            history: libsbml.ModelHistory = sbase.getModelHistory()
        else:
            return None

        creators = []
        for kc in range(history.getNumCreators()):
            c: libsbml.ModelCreator = history.getCreator(kc)
            creators.append({
                "givenName":  c.getGivenName() if c.isSetGivenName() else None,
                "familyName": c.getFamilyName() if c.isSetFamilyName() else None,
                "organization": c.getOrganization() if c.isSetOrganization() else None,
                "email": c.getEmail() if c.isSetEmail() else None
            })

        created_date = history.getCreatedDate().getDateAsString() if history.isSetCreatedDate() else None
        modified_dates = []
        for km in range(history.getNumModifiedDates()):
            modified_dates.append(history.getModifiedDate(km).getDateAsString())
        return {
            "creators": creators,
            "createdDate": created_date,
            "modifiedDates": modified_dates
        }

    def document(self, doc: libsbml.SBMLDocument) -> Dict[str, str]:
        """Info for SBMLDocument.

        :param doc: SBMLDocument
        :return: information dictionary for SBMLDocument
        """
        d = self.sbase_dict(doc)

        packages = {}
        packages["document"] = {
            "level": doc.getLevel(),
            "version": doc.getVersion()
        }

        plugins = []
        for k in range(doc.getNumPlugins()):
            plugin = doc.getPlugin(k)
            prefix = plugin.getPrefix()
            version = plugin.getPackageVersion()
            plugins.append({
                "prefix": prefix,
                "version": version
            })
        packages["plugins"] = plugins

        d["packages"] = packages
        return d

    def model(self, model: libsbml.Model) -> Dict[str, str]:
        """Info for SBML Model.

        :param model: Model
        :return: information dictionary for Model
        """
        d = self.sbase_dict(model)
        for key in [
            "substanceUnits",
            "timeUnits",
            "volumeUnits",
            "areaUnits",
            "lengthUnits",
            "extentUnits",
            "conversionFactor",
        ]:
            d[key] = _get_sbase_attribute(model, key)

        return d

    def function_definitions(self, model: libsbml.Model) -> List:
        """Information dictionaries for FunctionDefinitions.

        :return: list of info dictionaries for FunctionDefinitions
        """
        func_defs = []
        fd: libsbml.FunctionDefinition
        for fd in model.getListOfFunctionDefinitions():
            d = self.sbase_dict(fd)
            d["math"] = astnode_to_latex(fd.getMath(), model) if fd.isSetMath() else None

            func_defs.append(d)

        return func_defs

    def unit_definitions(self, model: libsbml.Model) -> List:
        """Information for UnitDefinitions.

        :return: list of info dictionaries for UnitDefinitions
        """
        unit_defs = []
        ud: libsbml.UnitDefinition
        for ud in model.getListOfUnitDefinitions():
            d = self.sbase_dict(ud)
            d["units"] = self.ud_to_latex(ud, model=model)

            unit_defs.append(d)

        return unit_defs

    @staticmethod
    def ud_to_latex(ud: libsbml.UnitDefinition, model: libsbml.Model) -> Optional[str]:
        """Convert unit definition to latex."""
        if ud is None or 'None':
            return None

        ud_str: str = units.unitDefinitionToString(ud)
        astnode = libsbml.parseL3FormulaWithModel(ud_str, model=model)
        return astnode_to_latex(astnode, model=model)

    def compartments(self, model: libsbml.Model, assignments: Dict[str, Dict[str, str]]) -> List[Dict]:
        """Information for Compartments.

        :return: list of info dictionaries for Compartments
        """
        compartments = []
        c: libsbml.Compartment
        for c in model.getListOfCompartments():
            d = self.sbase_dict(c)
            for key in [
                "spatialDimensions",
                "size",
                "constant"
            ]:
                d[key] = _get_sbase_attribute(c, key)

            d["units"] = self.ud_to_latex(c.getUnits(), model=model) if c.isSetUnits() else None
            d["derivedUnits"] = self.ud_to_latex(c.getDerivedUnitDefinition(), model=model)

            if c.pk in assignments:
                d["assignment"] = assignments[c.pk]

            compartments.append(d)

        return compartments

    def species(
        self,
        model: libsbml.Model,
        assignments: Dict[str, Dict[str, str]]
    ) -> List[Dict]:
        """Information for Species.

        :return: list of info dictionaries for Species
        """

        species = []
        s: libsbml.Species
        for s in model.getListOfSpecies():
            d = self.sbase_dict(s)

            for key in [
                "compartment",
                "initialAmount",
                "initialConcentration",
                "substanceUnits",
                "hasOnlySubstanceUnits",
                "boundaryCondition",
                "constant",
            ]:
                d[key] = _get_sbase_attribute(s, key)

            d["units"] = self.ud_to_latex(s.getUnits(), model=model) if s.isSetUnits() else None
            d["derivedUnits"] = self.ud_to_latex(s.getDerivedUnitDefinition(), model=model)

            if s.pk in assignments:
                d["assignment"] = assignments[s.pk]

            if s.isSetConversionFactor():
                cf_sid = s.getConversionFactor()
                cf_p: libsbml.Parameter = model.getParameter(cf_sid)
                cf_value = cf_p.getValue()
                cf_units = cf_p.getUnits()

                d["conversionFactor"] = {
                    "sid": cf_sid,
                    "value": cf_value,
                    "units": cf_units
                }
            else:
                d["conversionFactor"] = {}

            # fbc
            sfbc = s.getPlugin("fbc")
            d["fbc"] = {
                "formula": sfbc.getChemicalFormula() if sfbc.isSetChemicalFormula() else None,
                "charge": sfbc.getCharge() if (sfbc.isSetCharge() and sfbc.getCharge() != 0) else None,
            } if sfbc else None

            species.append(d)

        return species

    def parameters(self, model: libsbml.Model,
        assignments: Dict[str, Dict[str, str]]
                   ) -> List[Dict]:
        """Information for SBML Parameters.

        :return: list of info dictionaries for Reactions
        """

        parameters = []
        p: libsbml.Parameter
        for p in model.getListOfParameters():
            d = self.sbase_dict(p)

            if p.isSetValue():
                value = p.getValue()
                if np.isnan(value):
                    value = None
            else:
                value = None

            d["value"] = value
            d["constant"] = p.getConstant() if p.isSetConstant() else None

            d["units"] = self.ud_to_latex(p.getUnits(), model=model) if p.isSetUnits() else None
            d["derivedUnits"] = self.ud_to_latex(p.getDerivedUnitDefinition(), model=model)

            if p.pk in assignments:
                d["assignment"] = assignments[p.pk]

            parameters.append(d)

        return parameters

    def initial_assignments(self, model: libsbml.Model) -> List:
        """Information for InitialAssignments.

        :return: list of info dictionaries for InitialAssignments
        """

        assignments = []
        assignment: libsbml.InitialAssignment
        for assignment in model.getListOfInitialAssignments():
            d = self.sbase_dict(assignment)
            d["symbol"] = assignment.getSymbol() if assignment.isSetSymbol() else None
            d["math"] = astnode_to_latex(assignment.getMath(), model=model)
            d["derivedUnits"] = self.ud_to_latex(assignment.getDerivedUnitDefinition(), model=model)
            assignments.append(d)

        return assignments

    def rules(self, model: libsbml.Model) -> Dict:
        """Information for Rules.

        :return: list of info dictionaries for Rules
        """

        rules = {
            "assignmentRules": [],
            "rateRules": [],
            "algebraicRules": [],
        }
        rule: libsbml.Rule
        for rule in model.getListOfRules():
            d = self.sbase_dict(rule)
            d["variable"] = self._rule_variable_to_string(rule)
            d["math"] = astnode_to_latex(rule.getMath(), model=model) if rule.isSetMath() else None
            d["derivedUnits"] = self.ud_to_latex(
                rule.getDerivedUnitDefinition(),
                model=model
            )

            type = d["sbmlType"]
            key = f"{type[0].lower()}{type[1:]}s"

            rules[key].append(d)

        return rules

    @staticmethod
    def _rule_variable_to_string(rule: libsbml.Rule) -> str:
        """Format variable for rule.

        :param rule: SBML rule instance
        :return formatted string representation of the rule
        """
        if isinstance(rule, libsbml.AlgebraicRule):
            return "0"
        elif isinstance(rule, libsbml.AssignmentRule):
            return rule.variable  # type: ignore
        elif isinstance(rule, libsbml.RateRule):
            return f"d {rule.variable}/dt"
        else:
            raise TypeError(rule)

    def constraints(self, model: libsbml.Model) -> List[Dict[str, Any]]:
        """Information for Constraints.

        :return: list of info dictionaries for Constraints
        """

        constraints = []
        constraint: libsbml.Constraint
        for constraint in model.getListOfConstraints():
            d = self.sbase_dict(constraint)
            d["math"] = astnode_to_latex(constraint.getMath(), model=model) if constraint.isSetMath() else None
            d["message"] = constraint.getMessage() if constraint.isSetMessage() else None
            constraints.append(d)

        return constraints

    def reactions(self, model: libsbml.Model) -> List[Dict[str, Any]]:
        """Information dictionaries for ListOfReactions.

        :return: list of info dictionaries for Reactions

        -- take a look at local parameter once
        -- also made additions for products and reactions
        """

        reactions = []
        r: libsbml.Reaction
        for r in model.getListOfReactions():
            d = self.sbase_dict(r)
            d["reversible"] = r.getReversible() if r.isSetReversible() else None
            d["compartment"] = r.getCompartment() if r.isSetCompartment() else None
            d["listOfReactants"] = [
                self._species_reference(reac) for reac in r.getListOfReactants()
            ]
            d["listOfProducts"] = [
                self._species_reference(prod) for prod in r.getListOfProducts()
            ]
            d["listOfModifiers"] = [mod.getSpecies() for mod in r.getListOfModifiers()]
            d["fast"] = r.getFast() if r.isSetFast() else None
            d["equation"] = self._equation_from_reaction(r)

            klaw: libsbml.KineticLaw = r.getKineticLaw() if r.isSetKineticLaw() else None
            if klaw:
                d_law = {}
                d_law["math"] = astnode_to_latex(klaw.getMath(), model=model) if klaw.isSetMath() else None
                d_law["derivedUnits"] = self.ud_to_latex(klaw.getDerivedUnitDefinition(), model=model)

                d_law["localParameters"] = []
                for i in range(len(klaw.getListOfLocalParameters())):
                    lp: libsbml.LocalParameter = klaw.getLocalParameter(i)
                    lpar_info = {
                        "id": lp.getId() if lp.isSetId() else None,
                        "value": lp.getValue() if lp.isSetValue() else None,
                        "units": self.ud_to_latex(lp.getUnits(), model=model) if lp.isSetUnits() else None,
                        "derivedUnits": self.ud_to_latex(lp.getDerivedUnitDefinition(), model=model),
                    }
                    d_law["localParameters"].append(lpar_info)
                d["kineticLaw"] = d_law
            else:
                d["kineticLaw"] = None

            # fbc
            rfbc = r.getPlugin("fbc")
            d["fbc"] = {
                "bounds": self._bounds_dict_from_reaction(r, model),
                "gpa": self._gene_product_association_dict_from_reaction(r)
            } if rfbc else None

            reactions.append(d)

        return reactions

    @staticmethod
    def _species_reference(species: libsbml.SpeciesReference):
        return {
            "species": species.getSpecies() if species.isSetSpecies() else None,
            "stoichiometry": species.getStoichiometry() if species.isSetStoichiometry() else 1.0,
            "constant": species.getConstant() if species.isSetConstant() else None
        }

    @staticmethod
    def _bounds_dict_from_reaction(reaction: libsbml.Reaction, model: libsbml.Model) -> Dict:
        """Render string of bounds from the reaction.

        :param reaction: SBML reaction instance
        :param model: SBML model instance
        :return: String of bounds extracted from the reaction
        """
        bounds = {}
        rfbc = reaction.getPlugin("fbc")
        if rfbc is not None:
            # get values for bounds
            lb_id, ub_id = None, None
            lb_value, ub_value = None, None
            if rfbc.isSetLowerFluxBound():
                lb_id = rfbc.getLowerFluxBound()
                lb_p = model.getParameter(lb_id)
                if lb_p.isSetValue():
                    lb_value = lb_p.getValue()
            if rfbc.isSetUpperFluxBound():
                ub_id = rfbc.getUpperFluxBound()
                ub_p = model.getParameter(ub_id)
                if ub_p.isSetValue():
                    ub_value = ub_p.getValue()

            bounds["lowerFluxBound"] = {
                'id': lb_id,
                'value': lb_value,
            }
            bounds["upperFluxBound"] = {
                'id': ub_id,
                'value': ub_value,
            }
        else:
            bounds = None

        return bounds

    @staticmethod
    def _gene_product_association_dict_from_reaction(reaction: libsbml.Reaction) -> Dict:
        """Render string representation of the GeneProductAssociation for given reaction.

        :param reaction: SBML reaction instance
        :return: string representation of GeneProductAssociation
        """

        rfbc = reaction.getPlugin("fbc")
        d = rfbc.getGeneProductAssociation().getAssociation().toInfix() if (
            rfbc and rfbc.isSetGeneProductAssociation()
        ) else None

        return d

    @staticmethod
    def _equation_from_reaction(
        reaction: libsbml.Reaction,
        sep_reversible: str = "&#8646;",
        sep_irreversible: str = "&#10142;",
        modifiers: bool = False,
    ) -> str:
        """Create equation for reaction.

        :param reaction: SBML reaction instance for which equation is to be generated
        :param sep_reversible: escape sequence for reversible equation (<=>) separator
        :param sep_irreversible: escape sequence for irreversible equation (=>) separator
        :param modifiers: boolean flag to use modifiers
        :return equation string generated for the reaction
        """

        left = SBMLDocumentInfo._half_equation(reaction.getListOfReactants())
        right = SBMLDocumentInfo._half_equation(reaction.getListOfProducts())
        if reaction.getReversible():
            # '<=>'
            sep = sep_reversible
        else:
            # '=>'
            sep = sep_irreversible
        if modifiers:
            mods = SBMLDocumentInfo._modifier_equation(reaction.getListOfModifiers())
            if mods is None:
                return " ".join([left, sep, right])
            else:
                return " ".join([left, sep, right, mods])
        return " ".join([left, sep, right])

    @staticmethod
    def _modifier_equation(modifierList: libsbml.ListOfSpeciesReferences) -> str:
        """Render string representation for list of modifiers.

        :param modifierList: list of modifiers
        :return: string representation for list of modifiers
        """
        if len(modifierList) == 0:
            return ""
        mids = [m.getSpecies() for m in modifierList]
        return "[" + ", ".join(mids) + "]"  # type: ignore

    @staticmethod
    def _half_equation(speciesList: libsbml.ListOfSpecies) -> str:
        """Create equation string of the half reaction of the species in the species list.

        :param speciesList: list of species in the half reaction
        :return: half equation string
        """
        items = []
        for sr in speciesList:
            stoichiometry = sr.getStoichiometry()
            species = sr.getSpecies()
            if abs(stoichiometry - 1.0) < 1e-8:
                sd = f"{species}"
            elif abs(stoichiometry + 1.0) < 1e-8:
                sd = f"-{species}"
            elif stoichiometry >= 0:
                sd = f"{stoichiometry} {species}"
            elif stoichiometry < 0:
                sd = f"-{stoichiometry} {species}"
            else:
                raise ValueError(f"Half equation could not be generated: '{sr}'")
            items.append(sd)
        return " + ".join(items)

    def events(self, model: libsbml.Model) -> List[Dict[str, Any]]:
        """Information dictionaries for Events.

        :return: list of info dictionaries for Events
        """

        events = []
        event: libsbml.Event
        for event in model.getListOfEvents():
            d = self.sbase_dict(event)

            d["useValuesFromTriggerTime"] = event.getUseValuesFromTriggerTime() if event.isSetUseValuesFromTriggerTime() else None

            trigger: libsbml.Trigger = event.getTrigger()
            if trigger:
                d["trigger"] = {
                    "math": astnode_to_latex(trigger.getMath(), model=model) if trigger.isSetMath() else None,
                    "initialValue": trigger.initial_value,
                    "persistent": trigger.persistent
                }
            else:
                d["trigger"] = None

            d["priority"] = astnode_to_latex(event.getPriority(), model=model) if event.isSetPriority() else None
            d["delay"] = astnode_to_latex(event.getDelay(), model=model) if event.isSetDelay() else None

            assignments = []
            eva: libsbml.EventAssignment
            for eva in event.getListOfEventAssignments():
                assignments.append({
                    "variable": eva.getVariable() if eva.isSetVariable() else None,
                    "math": astnode_to_latex(eva.getMath(), model=model) if eva.isSetMath() else None
                })
            d["listOfEventAssignments"] = assignments

            events.append(d)

        return events

    # ---------------------------------------------------------------------------------
    # comp
    # ---------------------------------------------------------------------------------
    def model_definitions(self) -> Dict:
        """Information for comp:ModelDefinitions.

        :return: list of info dictionaries for comp:ModelDefinitions
        """
        d = {
            'externalModelDefinitions': None,
            'modelDefinitions': None,
        }
        doc_comp: libsbml.CompSBMLDocumentPlugin = self.doc.getPlugin("comp")
        if doc_comp:
            model_defs = []
            md: libsbml.ModelDefinition
            for md in doc_comp.getListOfModelDefinitions():
                model_defs.append(
                    self.model_dict(model=md)
                )
            d["modelDefinitions"] = model_defs

            external_model_defs = []
            emd: libsbml.ExternalModelDefinition
            for emd in doc_comp.getListOfExternalModelDefinitions():
                d = self.sbase_dict(emd)
                d["type"] = {
                    "class": type(emd).__name__,
                    "source_code": emd.getSource()
                }
                external_model_defs.append(d)
            d["externalModelDefinitions"] = external_model_defs

        return d

    def submodels(self, model: libsbml.Model) -> List[Dict[str, Any]]:
        """Information dictionaries for comp:Submodels.

        :return: list of info dictionaries for comp:Submodels
        """
        d = []
        model_comp = model.getPlugin("comp")
        if model_comp:
            submodels = []
            submodel: libsbml.Submodel
            for submodel in model_comp.getListOfSubmodels():
                d = self.sbase_dict(submodel)
                d["modelRef"] = submodel.getModelRef() if submodel.isSetModelRef() else None

                deletions = []
                for deletion in submodel.getListOfDeletions():
                    deletions.append(self._sbaseref(deletion))
                d["deletions"] = deletions

                d["timeConversion"] = submodel.getTimeConversionFactor() if submodel.isSetTimeConversionFactor() else None
                d["extentConversion"] = submodel.getExtentConversionFactor() if submodel.isSetExtentConversionFactor() else None

                submodels.append(d)
            d = submodels

        return d

    def ports(self, model: libsbml.Model) -> List:
        """Information for comp:Ports.

        :return: list of info dictionaries for comp:Ports
        """

        model_comp = model.getPlugin("comp")
        ports = []
        if model_comp:
            port: libsbml.Port
            for port in model_comp.getListOfPorts():
                d = self.sbaseref_dict(port)
                ports.append(d)

        return ports

    # ---------------------------------------------------------------------------------
    # fbc
    # ---------------------------------------------------------------------------------
    def gene_products(self, model: libsbml.Model) -> List[Dict[str, Any]]:
        """Information dictionaries for GeneProducts.

        :return: list of info dictionaries for Reactions
        """
        gps = []
        model_fbc: libsbml.FbcModelPlugin = model.getPlugin("fbc")
        if model_fbc:

            gp: libsbml.GeneProduct
            for gp in model_fbc.getListOfGeneProducts():
                d = self.sbase_dict(gp)
                d["label"] = gp.getLabel() if gp.isSetLabel() else None
                d["associatedSpecies"] = gp.getAssociatedSpecies() if gp.isSetAssociatedSpecies() else None
                gps.append(d)

        return gps

    def objectives(self, model: libsbml.Model) -> List[Dict[str, Any]]:
        """Information dictionaries for Objectives.

        :return: list of info dictionaries for Objectives
        """

        objectives = []
        model_fbc: libsbml.FbcModelPlugin = model.getPlugin("fbc")
        if model_fbc:
            objective: libsbml.Objective
            for objective in model_fbc.getListOfObjectives():
                d = self.sbase_dict(objective)
                d["type"] = objective.getType() if objective.isSetType() else None

                flux_objectives = []
                f_obj: libsbml.FluxObjective
                for f_obj in objective.getListOfFluxObjectives():
                    coefficient = f_obj.getCoefficient()
                    if coefficient < 0.0:
                        sign = "-"
                    else:
                        sign = "+"
                    part = {
                        "sign": sign,
                        "coefficient": abs(coefficient),
                        "reaction": f_obj.getReaction() if f_obj.isSetReaction() else None
                    }
                    flux_objectives.append(part)
                d["fluxObjectives"] = flux_objectives

                objectives.append(d)

        return objectives


if __name__ == "__main__":
    from pathlib import Path

    output_dir = Path(__file__).parent / "test"
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    print("-" * 80)
    from src.sbmlutils.test import (
        ICG_BODY,
        REPRESSILATOR_SBML,
        RECON3D_SBML,
        ICG_LIVER,
        ICG_BODY_FLAT,
        MODEL_DEFINITIONS_SBML,
    )
    for source in [
        # ICG_BODY,
        REPRESSILATOR_SBML,
        # RECON3D_SBML,
        # ICG_LIVER,
        # ICG_BODY_FLAT,
        # MODEL_DEFINITIONS_SBML,
    ]:
        info = SBMLDocumentInfo.from_sbml(source)
        json_str = info.to_json()
        print(info)
        print("-" * 80)
        print(json_str)
        print("-" * 80)

    with open(output_dir / "test.json", "w") as fout:
        fout.write(json_str)
