import type { PushNotificationPayload } from '../types/notifications';

export const NOTIFICATIONS_ACTIONS = {
  PUSH: 'notifications/PUSH',
  DISMISS: 'notifications/DISMISS',
  CLEAR: 'notifications/CLEAR',
} as const;

export type NotificationsAction =
  | { type: typeof NOTIFICATIONS_ACTIONS.PUSH; payload: { id: string } & PushNotificationPayload }
  | { type: typeof NOTIFICATIONS_ACTIONS.DISMISS; payload: { id: string } }
  | { type: typeof NOTIFICATIONS_ACTIONS.CLEAR };

/**
 * Create an action to push a notification onto the UI stack.
 *
 * @param notification - Notification payload describing message and variant.
 * @returns Redux action containing a generated ID and payload data.
 */
export const pushNotification = (notification: PushNotificationPayload): NotificationsAction => {
  const id = typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}`;

  return {
    type: NOTIFICATIONS_ACTIONS.PUSH,
    payload: {
      id,
      ...notification,
    },
  };
};

/**
 * Create an action dismissing a notification by identifier.
 *
 * @param id - Notification identifier to remove.
 * @returns Redux action instructing reducers to drop the notification.
 */
export const dismissNotification = (id: string): NotificationsAction => ({
  type: NOTIFICATIONS_ACTIONS.DISMISS,
  payload: { id },
});

/**
 * Create an action clearing all active notifications.
 *
 * @returns Redux action signalling that the notification list should be emptied.
 */
export const clearNotifications = (): NotificationsAction => ({
  type: NOTIFICATIONS_ACTIONS.CLEAR,
});
