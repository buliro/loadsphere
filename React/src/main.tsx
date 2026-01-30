import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { Provider } from 'react-redux';
import { App } from './modules/app/App';
import { createAppStore } from './store/configureStore';

import 'leaflet/dist/leaflet.css';

import './styles/index.scss';

const store = createAppStore();

/**
 * Hydrate the React application and mount it under the #root element.
 */
ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </Provider>
  </React.StrictMode>,
);
