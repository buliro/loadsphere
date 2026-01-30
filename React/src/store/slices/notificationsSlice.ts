import { createSlice, nanoid, type PayloadAction } from '@reduxjs/toolkit';

import type { Notification } from '../../types/notifications';
import type { RootState } from '../configureStore';

type NotificationsState = Notification[];

const initialState: NotificationsState = [];

const notificationsSlice = createSlice({
  name: 'notifications',
  initialState,
  reducers: {
    pushNotification: {
      reducer(state, action: PayloadAction<Notification>) {
        state.push(action.payload);
      },
      prepare(notification: Omit<Notification, 'id'> & { id?: string }) {
        return {
          payload: {
            id: notification.id ?? nanoid(),
            message: notification.message,
            variant: notification.variant,
          },
        };
      },
    },
    dismissNotification(state, action: PayloadAction<{ id: string }>) {
      return state.filter((notification) => notification.id !== action.payload.id);
    },
    clearNotifications() {
      return initialState;
    },
  },
});

export const { pushNotification, dismissNotification, clearNotifications } = notificationsSlice.actions;
export const notificationsReducer = notificationsSlice.reducer;

export const selectNotifications = (state: RootState) => state.notifications;
export const selectNotificationById = (notificationId: string) => (state: RootState) =>
  state.notifications.find((notification: Notification) => notification.id === notificationId) ?? null;
