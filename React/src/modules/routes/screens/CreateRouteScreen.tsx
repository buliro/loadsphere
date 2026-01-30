import React, { useCallback, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { graphqlRequest } from '../../../services/graphql';
import { pushNotification } from '../../../store/slices/notificationsSlice';
import { useAppDispatch } from '../../../store/hooks';
import { LocationSearchInput, type SelectedLocation } from '../components/LocationSearchInput';

import styles from './CreateRouteScreen.module.scss';

interface RouteFormState {
  tractorNumber: string;
  trailerNumbers: string;
  carrierNames: string;
  mainOfficeAddress: string;
  homeTerminalAddress: string;
  coDriverName: string;
  shipperName: string;
  commodity: string;
  commodityCustom: string;
  startLocation: SelectedLocation;
  pickupLocation: SelectedLocation;
  dropoffLocation: SelectedLocation;
  cycleHoursUsed: string;
}

/**
 * Produce an empty location object used for initializing form state.
 *
 * @returns Location object with blank address and null coordinates.
 */
const createEmptyLocation = (): SelectedLocation => ({ address: '', lat: null, lng: null });

const INITIAL_FORM: RouteFormState = {
  tractorNumber: '',
  trailerNumbers: '',
  carrierNames: '',
  mainOfficeAddress: '',
  homeTerminalAddress: '',
  coDriverName: '',
  shipperName: '',
  commodity: '',
  commodityCustom: '',
  startLocation: createEmptyLocation(),
  pickupLocation: createEmptyLocation(),
  dropoffLocation: createEmptyLocation(),
  cycleHoursUsed: '0',
};

const COMMODITY_SUGGESTIONS = [
  'LPG',
  'Horticultural products',
  'Fresh produce',
  'Automotive parts',
  'Construction materials',
  'Pharmaceuticals',
  'Temperature-controlled goods',
  'General freight',
];

const PLAN_TRIP_MUTATION = `
  mutation PlanTrip($input: PlanTripInput!) {
    planTrip(input: $input) {
      success
      errors
      trip {
        id
        status
      }
    }
  }
`;

type CreateRouteScreenProps = {
  /**
   * Optional handler invoked when the form should close without navigation.
   */
  onDismiss?: () => void;
  /**
   * Optional handler invoked after a route has been created successfully.
   */
  onRouteCreated?: () => void;
};

/**
 * Render the new route planner form and handle submission to the backend.
 *
 * @param props - Optional callbacks to customise dismiss and success behaviour.
 * @returns Form layout enabling users to configure and submit route plans.
 */
export const CreateRouteScreen: React.FC<CreateRouteScreenProps> = ({ onDismiss, onRouteCreated }) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const [form, setForm] = useState<RouteFormState>(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const trailerList = useMemo(() =>
    form.trailerNumbers
      .split(/\s|,|\n/)
      .map((item) => item.trim())
      .filter(Boolean),
  [form.trailerNumbers]);

  const carrierList = useMemo(() =>
    form.carrierNames
      .split(/\s|,|\n/)
      .map((item) => item.trim())
      .filter(Boolean),
  [form.carrierNames]);

  const commodityValue = useMemo(() => {
    return form.commodity === '__custom__' ? form.commodityCustom.trim() : form.commodity.trim();
  }, [form.commodity, form.commodityCustom]);

  const isLocationComplete = (location: SelectedLocation) =>
    Boolean(location.address.trim() && location.lat !== null && location.lng !== null);

  const isValid = useMemo(() => {
    return (
      isLocationComplete(form.startLocation) &&
      isLocationComplete(form.pickupLocation) &&
      isLocationComplete(form.dropoffLocation) &&
      form.tractorNumber.trim() &&
      trailerList.length > 0 &&
      carrierList.length > 0 &&
      form.mainOfficeAddress.trim() &&
      form.homeTerminalAddress.trim() &&
      form.shipperName.trim() &&
      commodityValue.length > 0
    );
  }, [carrierList.length, commodityValue.length, form, trailerList.length]);

  const handleCommodityChange = useCallback((event: React.ChangeEvent<HTMLSelectElement>) => {
    const { value } = event.target;
    setForm((current) => ({
      ...current,
      commodity: value,
      commodityCustom: value === '__custom__' ? current.commodityCustom : '',
    }));
  }, []);

  const handleCommodityCustomChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setForm((current) => ({
      ...current,
      commodityCustom: value,
    }));
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isValid || submitting) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    const cycleHoursUsed = Number(form.cycleHoursUsed) || 0;

    const toGraphqlLocation = (location: SelectedLocation) => ({
      address: location.address.trim(),
      lat: location.lat,
      lng: location.lng,
    });

    const input = {
      startLocation: toGraphqlLocation(form.startLocation),
      pickupLocation: toGraphqlLocation(form.pickupLocation),
      dropoffLocation: toGraphqlLocation(form.dropoffLocation),
      cycleHoursUsed,
      tractorNumber: form.tractorNumber.trim(),
      trailerNumbers: trailerList,
      carrierNames: carrierList,
      mainOfficeAddress: form.mainOfficeAddress.trim(),
      homeTerminalAddress: form.homeTerminalAddress.trim(),
      coDriverName: form.coDriverName.trim() || null,
      shipperName: form.shipperName.trim(),
      commodity: commodityValue,
    };

    try {
      const data = await graphqlRequest<{ planTrip: { success: boolean; errors?: string[] | null } }>(
        PLAN_TRIP_MUTATION,
        {
          variables: { input },
        },
      );

      if (!data?.planTrip?.success) {
        const message = data?.planTrip?.errors?.join('\n') || 'Failed to create route. Please review your entries.';
        setError(message);
        return;
      }

      dispatch(
        pushNotification({
          message: 'Route created successfully.',
          variant: 'success',
        }),
      );
      onRouteCreated?.();

      if (onDismiss) {
        onDismiss();
      } else {
        setSuccessMessage('Route created successfully. Redirecting to dashboard…');
        setTimeout(() => {
          navigate('/dashboard');
        }, 1200);
      }
    } catch (mutationError) {
      const message =
        mutationError instanceof Error
          ? mutationError.message
          : 'Unable to create route at this time. Please try again.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (onDismiss) {
      onDismiss();
      return;
    }

    navigate('/dashboard');
  };

  return (
    <div className={styles.screen}>
      <header className={styles.header}>
        <h1>Create a new route</h1>
        <p>Capture vehicle, equipment, and shipper information to plan the next route.</p>
      </header>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <section className={styles.fieldGroup}>
          <h2>Equipment details</h2>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="tractorNumber">Vehicle plates</label>
              <input
                id="tractorNumber"
                name="tractorNumber"
                value={form.tractorNumber}
                onChange={handleChange}
                required
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="coDriverName">Co-driver (optional)</label>
              <input
                id="coDriverName"
                name="coDriverName"
                value={form.coDriverName}
                onChange={handleChange}
                placeholder="Jane Driver"
              />
            </div>
          </div>

          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="trailerNumbers">Trailer plates</label>
              <textarea
                id="trailerNumbers"
                name="trailerNumbers"
                value={form.trailerNumbers}
                onChange={handleChange}
                placeholder="Enter one per line or separate with commas"
                required
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="carrierNames">Carrier name(s)</label>
              <textarea
                id="carrierNames"
                name="carrierNames"
                value={form.carrierNames}
                onChange={handleChange}
                placeholder="Enter one per line or separate with commas"
                required
              />
            </div>
          </div>
        </section>

        <section className={styles.fieldGroup}>
          <h2>Locations</h2>
          <div className={styles.fieldRow}>
            <LocationSearchInput
              id="startLocation"
              label="Current location"
              value={form.startLocation}
              onChange={(next) => setForm((current) => ({ ...current, startLocation: next }))}
              placeholder="Yard or current tractor location"
              required
            />
            <LocationSearchInput
              id="pickupLocation"
              label="Pickup location"
              value={form.pickupLocation}
              onChange={(next) => setForm((current) => ({ ...current, pickupLocation: next }))}
              placeholder="Primary shipper pickup address"
              required
            />
          </div>

          <div className={styles.fieldRow}>
            <LocationSearchInput
              id="dropoffLocation"
              label="Dropoff location"
              value={form.dropoffLocation}
              onChange={(next) => setForm((current) => ({ ...current, dropoffLocation: next }))}
              placeholder="Destination / receiver address"
              required
            />
            <div className={styles.field}>
              <label htmlFor="cycleHoursUsed">Cycle hours used</label>
              <input
                id="cycleHoursUsed"
                name="cycleHoursUsed"
                type="number"
                min="0"
                step="0.1"
                value={form.cycleHoursUsed}
                onChange={handleChange}
              />
            </div>
          </div>
        </section>

        <section className={styles.fieldGroup}>
          <h2>Shipper details</h2>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="shipperName">Shipper name</label>
              <input
                id="shipperName"
                name="shipperName"
                value={form.shipperName}
                onChange={handleChange}
                required
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="commodity">Commodity</label>
              <div className={styles.selectWrapper}>
                <select
                  id="commodity"
                  name="commodity"
                  value={form.commodity}
                  onChange={handleCommodityChange}
                  required
                >
                  <option value="" disabled>
                    Select commodity
                  </option>
                  {COMMODITY_SUGGESTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                  <option value="__custom__">Other (specify)</option>
                </select>
                <span className={styles.selectIcon} aria-hidden="true">
                  <svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg" focusable="false">
                    <path
                      d="M4.47 6.47a.75.75 0 0 1 1.06 0L8 8.94l2.47-2.47a.75.75 0 0 1 1.06 1.06l-3 3a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 0 1 0-1.06Z"
                      fill="currentColor"
                    />
                  </svg>
                </span>
              </div>
              {form.commodity === '__custom__' && (
                <input
                  id="commodityCustom"
                  name="commodityCustom"
                  className={styles.inlineInput}
                  placeholder="Enter commodity"
                  value={form.commodityCustom}
                  onChange={handleCommodityCustomChange}
                  required
                />
              )}
            </div>
          </div>

          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="mainOfficeAddress">Main office address</label>
              <textarea
                id="mainOfficeAddress"
                name="mainOfficeAddress"
                value={form.mainOfficeAddress}
                onChange={handleChange}
                required
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="homeTerminalAddress">Home terminal address</label>
              <textarea
                id="homeTerminalAddress"
                name="homeTerminalAddress"
                value={form.homeTerminalAddress}
                onChange={handleChange}
                required
              />
            </div>
          </div>
        </section>

        {error && <div className={styles.error}>{error}</div>}
        {successMessage && <div className={styles.success}>{successMessage}</div>}

        <div className={styles.actions}>
          <button type="button" className={styles.secondary} onClick={handleCancel} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" className={styles.primary} disabled={!isValid || submitting}>
            {submitting ? 'Creating…' : 'Create route'}
          </button>
        </div>
      </form>
    </div>
  );
};
