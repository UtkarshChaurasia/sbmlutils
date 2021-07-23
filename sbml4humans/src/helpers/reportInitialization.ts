import store from "@/store/index";
import allSBML from "@/data/allSBMLMap";
import listOfSBMLTypes from "@/data/listOfSBMLTypes";

function initializeComponentWiseLists(): Record<string, Array<string>> {
    const map = {};
    listOfSBMLTypes.listOfSBMLTypes.forEach((sbmlType) => {
        map[sbmlType] = [];
    });
    return map;
}

/**
 * Collects the SBML Document and all model definitions from the backend API
 * response. It then collects other SBML objects in these definitions. Also
 * updates the count of SBML components and initializes global component maps.
 * @param report The generated SBML report sent in the API response.
 */
function assembleSBasesInReport(
    report: Record<string, unknown>
): Array<Record<string, unknown>> {
    if (report === null) {
        return [];
    }

    const sbases: Array<Record<string, unknown>> = [];
    const counts: Record<string, Record<string, number>> = {};
    const allObjectsMap: Record<string, unknown> = {};
    const componentPKsMap: Record<string, Record<string, Array<string>>> = {};
    const componentWiseLists: Record<
        string,
        Array<string>
    > = initializeComponentWiseLists();

    // collecting doc
    if (report.doc) {
        sbases.push(report.doc as Record<string, unknown>);
        allObjectsMap[(report.doc as Record<string, unknown>).pk as string] =
            report.doc;
        componentWiseLists["SBMLDocument"] = [
            (report.doc as Record<string, unknown>).pk as string,
        ];
    }

    const model: Record<string, unknown> = report.model as Record<string, unknown>;
    if (model) {
        const pk = model.pk as string;
        componentWiseLists["Model"].push(pk);

        counts[pk] = allSBML.counts;

        counts[pk]["Model"] = 1;

        sbases.push(model);

        allObjectsMap[pk] = model;
        componentPKsMap[pk] = {};

        componentPKsMap[pk]["Model"] = [pk];

        // collecting all other components
        sbases.push(
            ...collectSBasesInModel(
                model,
                counts,
                allObjectsMap,
                componentPKsMap,
                componentWiseLists
            )
        );
    }

    const modelTypes = ["modelDefinitions", "externalModelDefinitions"];
    modelTypes.forEach((modelType) => {
        if (report[modelType]) {
            const modelDefinitions = report[modelType] as Array<
                Record<string, unknown>
            >;
            for (let i = 0; i < modelDefinitions.length; i++) {
                const md = modelDefinitions[i];
                const pk = md.pk as string;

                counts[pk] = {};
                componentPKsMap[pk] = {};

                counts[pk]["Model"] = 1;

                allObjectsMap[pk] = md;
                componentPKsMap[pk]["Model"] = [pk];
                componentWiseLists["Model"].push(pk);

                // collecting all other components
                sbases.push(
                    ...collectSBasesInModel(
                        md,
                        counts,
                        allObjectsMap,
                        componentPKsMap,
                        componentWiseLists
                    )
                );
            }
        }
    });

    //allObjectsMap = createComponentLists(allObjectsMap);

    store.dispatch("updateCounts", counts);
    store.dispatch("updateAllObjectsMap", allObjectsMap);
    store.dispatch("updateComponentPKsMap", componentPKsMap);
    store.dispatch("updateComponentWiseLists", componentWiseLists);

    return sbases;
}

/**
 * Collects SBML objects inside a particular model definition.
 * @param model The SBML model
 * @param counts Global counts map
 * @param allObjectsMap Global map for all SBML objects
 * @param componentPKsMap Global map for component-wise SBML objects
 */
function collectSBasesInModel(
    model: Record<string, unknown>,
    counts: Record<string, Record<string, number>>,
    allObjectsMap: Record<string, unknown>,
    componentPKsMap: Record<string, Record<string, Array<unknown>>>,
    componentWiseLists: Record<string, Array<string>>
): Array<Record<string, unknown>> {
    const sbasesInModel: Array<Record<string, unknown>> = [];

    for (let i = 0; i < listOfSBMLTypes.listOfSBMLTypes.length; i++) {
        const sbmlType = listOfSBMLTypes.listOfSBMLTypes[i];

        // camel case keys, present in the API response E.g. unitDefinitions, compartments
        let key: string = sbmlType.charAt(0).toLowerCase() + sbmlType.slice(1);
        if (sbmlType != "Species") {
            key = key + "s";
        }

        if (model[key]) {
            const component: Array<Record<string, unknown>> = model[key] as Array<
                Record<string, unknown>
            >;

            componentPKsMap[model.pk as string][sbmlType] = [];

            counts[model.pk as string][sbmlType] = component.length as number;
            component.forEach((sbase) => {
                sbasesInModel.push(sbase);

                const pk = sbase.pk as string;
                allObjectsMap[pk] = sbase;
                componentPKsMap[model.pk as string][sbmlType].push(pk);
                componentWiseLists[sbmlType].push(pk);
            });
        }
    }

    return sbasesInModel;
}

function createComponentLists(allObjectsMap: Record<string, unknown>) {
    const listsMap: Record<string, Array<string>> = {};
    listOfSBMLTypes.listOfSBMLTypes.forEach((sbmlType) => {
        listsMap[sbmlType] = [];
        for (const pk in allObjectsMap) {
            if ((allObjectsMap[pk] as Record<string, unknown>).sbmlType === sbmlType) {
                listsMap[sbmlType].push(pk);
            }
        }
    });

    return allObjectsMap;
}

export default {
    assembleSBasesInReport: assembleSBasesInReport,
};