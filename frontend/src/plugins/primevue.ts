import PrimeVue from 'primevue/config';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import 'primevue/resources/themes/saga-blue/theme.css';
import 'primevue/resources/primevue.min.css';
import 'primeicons/primeicons.css';
import Image from 'primevue/image';
import InputText from 'primevue/inputtext';
import Menu from 'primevue/menu';
import Slider from 'primevue/slider';
import Dropdown from 'primevue/dropdown';
import InputNumber from 'primevue/inputnumber';
import Toast from 'primevue/toast';
import ToastService from 'primevue/toastservice';
import ConfirmationService from 'primevue/confirmationservice';
import ConfirmDialog from 'primevue/confirmdialog';
import FileUpload from 'primevue/fileupload';
import Textarea from 'primevue/textarea';
import Accordion from 'primevue/accordion';
import AccordionTab from 'primevue/accordiontab';
import Checkbox from 'primevue/checkbox';
import ToggleButton from 'primevue/togglebutton';
import InputSwitch from 'primevue/inputswitch';

import '@/assets/styles/theme.css';

export default {
  install: (app: any) => {
    app.use(PrimeVue);
    app.use(ToastService);
    app.use(ConfirmationService);
    app.component('PrimeFileUpload', FileUpload);
    app.component('PrimeTextarea', Textarea);
    app.component('PrimeConfirmDialog', ConfirmDialog);
    app.component('PrimeDialog', Dialog);
    app.component('PrimeButton', Button);
    app.component('PrimeImage', Image);
    app.component('PrimeInputText', InputText);
    app.component('PrimeMenu', Menu);
    app.component('PrimeSlider', Slider);
    app.component('PrimeDropdown', Dropdown);
    app.component('PrimeInputNumber', InputNumber);
    app.component('PrimeToast', Toast);
    app.component('PrimeAccordion', Accordion);
    app.component('PrimeAccordionTab', AccordionTab);
    app.component('PrimeCheckbox', Checkbox);
    app.component('PrimeToggleButton', ToggleButton);
    app.component('PrimeInputSwitch', InputSwitch);
  },
};