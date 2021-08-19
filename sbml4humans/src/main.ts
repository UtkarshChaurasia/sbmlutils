// core
import { createApp } from "vue";
import App from "./App.vue";
import "./registerServiceWorker";
import router from "./router";
import store from "./store";

// PrimeVue UI package
import 'primevue/resources/themes/bootstrap4-light-blue/theme.css';
import "primevue/resources/primevue.min.css";
import "primeicons/primeicons.css";
import 'primeflex/primeflex.css';
import { FilterMatchMode, FilterOperator } from "primevue/api";

import PrimeVue from "primevue/config";
import Badge from "primevue/badge";
import ProgressSpinner from "primevue/progressspinner";
import ScrollPanel from "primevue/scrollpanel";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Dropdown from "primevue/dropdown";
import Button from "primevue/button";
import Slider from "primevue/slider";
import InputText from "primevue/inputtext";
import Menubar from "primevue/menubar";
import FileUpload from "primevue/fileupload";
import Card from "primevue/card";
import Tag from "primevue/tag";


// fontawesome
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faPhone,
    faCode,
    faArchive,
    faFlask,
    faSuperscript,
    faEquals,
    faTachometerAlt,
    faLeaf,
    faRuler,
    faSync,
    faClock,
    faDna,
    faLongArrowAltLeft,
    faFileCode,
    faPlug,
    faSitemap,
    faLessThanEqual,
    faBullseye,
    faFileAlt,
    faFileCsv,
    faSearch,
    faStream,
    faCheckCircle,
    faTimesCircle,
    faFileMedicalAlt,
    faTablets,
    faArrowLeft,
    faArrowRight,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add({
    faPhone,
    faCode,
    faArchive,
    faFlask,
    faSuperscript,
    faEquals,
    faTachometerAlt,
    faLeaf,
    faRuler,
    faSync,
    faClock,
    faDna,
    faLongArrowAltLeft,
    faFileCode,
    faPlug,
    faSitemap,
    faLessThanEqual,
    faBullseye,
    faFileAlt,
    faFileCsv,
    faSearch,
    faStream,
    faCheckCircle,
    faTimesCircle,
    faFileMedicalAlt,
    faTablets,
    faArrowLeft,
    faArrowRight,
});

// app initialization
createApp(App)
    .use(store)
    .use(router)
    .use(PrimeVue)
    .component("font-awesome-icon", FontAwesomeIcon)
    .component("Badge", Badge)
    .component("ProgressSpinner", ProgressSpinner)
    .component("ScrollPanel", ScrollPanel)
    .component("DataTable", DataTable)
    .component("Column", Column)
    .component("Dropdown", Dropdown)
    .component("Button", Button)
    .component("Slider", Slider)
    .component("FilterMatchMode", FilterMatchMode)
    .component("FilterOperator", FilterOperator)
    .component("InputText", InputText)
    .component("Menubar", Menubar)
    .component("FileUpload", FileUpload)
    .component("Card", Card)
    .component("Tag", Tag)
    .mount("#app");
