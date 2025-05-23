import { createApp } from 'vue';
import { createPinia } from 'pinia';
import FloatingVue from 'floating-vue';
import 'floating-vue/dist/style.css';
import { library } from '@fortawesome/fontawesome-svg-core';
import { 
  faCommentAlt,
  faPaperPlane, 
  faPaperclip, 
  faRobot, 
  faClock, 
  faRedo, 
  faTrash, 
  faExclamationTriangle, 
  faTimes, 
  faUser, 
  faBars, 
  faCog, 
  faEdit, 
  faSave, 
  faPlus,
  faSpinner,
  faFile,
  faFileAlt,
  faFolder,
  faFolderOpen,
  faFolderPlus,
  faUpload,
  faFilePdf,
  faRefresh,
  faCaretDown,
  faUserCircle, 
  faEye,
  faImage,
  faCopy,
  faCodeBranch
} from '@fortawesome/free-solid-svg-icons';
import { faComment } from '@fortawesome/free-regular-svg-icons'  
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import App from './App.vue';
import router from './router';
import primevue from './plugins/primevue';
import highlightPlugin from './plugins/highlight-plugin';
import '@/assets/styles/code-theme.css';

library.add(
  faPaperPlane, 
  faPaperclip, 
  faRobot, 
  faCommentAlt, 
  faComment, 
  faClock, 
  faRedo, 
  faTrash, 
  faExclamationTriangle, 
  faTimes, 
  faUser, 
  faBars, 
  faCog, 
  faEdit, 
  faSave, 
  faPlus,
  faSpinner,
  faFile,
  faFileAlt,
  faFolder,
  faFolderOpen,
  faFolderPlus,
  faUpload,
  faFilePdf,
  faRefresh,
  faCaretDown,
  faUserCircle,
  faEye,
  faImage,
  faCopy,
  faCodeBranch
);

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(primevue);
app.use(FloatingVue);
app.use(highlightPlugin);
app.component('font-awesome-icon', FontAwesomeIcon);
app.mount('#app');