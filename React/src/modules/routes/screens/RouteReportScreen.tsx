import React, { useMemo, useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';

import { RoutesService } from '../../../services/RoutesService';
import { useAppDispatch } from '../../../store/hooks';
import { pushNotification } from '../../../store/slices/notificationsSlice';

import styles from './RouteReportScreen.module.scss';

/**
 * Display a PDF preview for a completed route and provide download controls.
 *
 * @returns Route report preview layout with iframe and download action.
 */
const RouteReportScreen: React.FC = () => {
  const { tripId } = useParams<{ tripId: string }>();
  const dispatch = useAppDispatch();
  const [downloading, setDownloading] = useState(false);

  const inlineUrl = useMemo(() => {
    if (!tripId) {
      return '';
    }
    return RoutesService.getRouteReportUrl(tripId, 'inline');
  }, [tripId]);

  /**
   * Trigger a file download of the completed route report PDF.
   *
   * @returns Promise that resolves when the download request finishes.
   */
  const handleDownload = async () => {
    if (!tripId) {
      return;
    }

    setDownloading(true);
    try {
      await RoutesService.downloadRouteReport(tripId);
      dispatch(
        pushNotification({
          message: 'Route report download starting.',
          variant: 'success',
        }),
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to download route report.';
      dispatch(pushNotification({ message, variant: 'error' }));
    } finally {
      setDownloading(false);
    }
  };

  if (!tripId) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>Route report</h1>
          <p>Preview the completed route PDF and download a copy for your records.</p>
        </div>
        <div className={styles.actions}>
          <Link to="/dashboard" className={styles.backLink}>
            ← Back to dashboard
          </Link>
          <button
            type="button"
            className={styles.downloadButton}
            onClick={handleDownload}
            disabled={downloading}
          >
            {downloading ? 'Preparing…' : 'Download PDF'}
          </button>
        </div>
      </header>
      <section className={styles.previewSection}>
        <iframe
          title="Route PDF preview"
          src={inlineUrl}
          className={styles.previewFrame}
          aria-label="Route report PDF preview"
        />
      </section>
    </div>
  );
};

export default RouteReportScreen;
