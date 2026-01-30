import type { NotificationsAction } from '../actions/notificationsActions';
import { NOTIFICATIONS_ACTIONS } from '../actions/notificationsActions';
import type { Notification } from '../types/notifications';

export type NotificationsState = Notification[];

const initialState: NotificationsState = [];

export const notificationsReducer = (
  state: NotificationsState = initialState,
  action: NotificationsAction,
): NotificationsState => {
  switch (action.type) {
    case NOTIFICATIONS_ACTIONS.PUSH:
      return [...state, action.payload];
    case NOTIFICATIONS_ACTIONS.DISMISS:
      return state.filter((notification) => notification.id !== action.payload.id);
    case NOTIFICATIONS_ACTIONS.CLEAR:
      return initialState;
    default:
      return state;
  }
};

export { initialState as notificationsInitialState };
