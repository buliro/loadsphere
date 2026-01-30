import type { RootState } from '../store/configureStore';
import type { NotificationsState } from '../reducer/notificationsReducer';

export const selectNotificationsState = (state: RootState): NotificationsState => state.notifications;

export const selectNotifications = (state: RootState) => selectNotificationsState(state);
