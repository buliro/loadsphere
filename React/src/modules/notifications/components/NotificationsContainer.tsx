import React from 'react';

import { useAppDispatch, useAppSelector } from '../../../store/hooks';
import { dismissNotification } from '../../../store/slices/notificationsSlice';
import { selectNotifications } from '../../../selectors/notificationsSelectors';

import './NotificationsContainer.scss';

/**
 * Render toast-style notifications sourced from the global store.
 *
 * @returns JSX element containing notification entries or null when empty.
 */
export const NotificationsContainer: React.FC = () => {
  const dispatch = useAppDispatch();
  const notifications = useAppSelector(selectNotifications);

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div className="notifications-container">
      {notifications.map((notification) => (
        <div key={notification.id} className={`notification notification--${notification.variant}`}>
          <p>{notification.message}</p>
          <button
            type="button"
            onClick={() => dispatch(dismissNotification({ id: notification.id }))}
            aria-label="Dismiss notification"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
};
