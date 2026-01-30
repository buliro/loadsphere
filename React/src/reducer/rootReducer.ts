import { combineReducers } from '@reduxjs/toolkit';

import { authReducer } from '../store/slices/authSlice';
import { logsReducer } from '../store/slices/logsSlice';
import { routesReducer } from '../store/slices/routesSlice';
import { notificationsReducer } from '../store/slices/notificationsSlice';

export const rootReducer = combineReducers({
  auth: authReducer,
  routes: routesReducer,
  logs: logsReducer,
  notifications: notificationsReducer,
});
