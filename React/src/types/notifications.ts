export type NotificationVariant = 'success' | 'info' | 'warning' | 'error';

export type Notification = {
  id: string;
  message: string;
  variant: NotificationVariant;
};

export type PushNotificationPayload = Omit<Notification, 'id'>;
