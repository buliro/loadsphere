import React, { useEffect, useMemo, useState } from 'react';

import { OpenRouteService, type OpenRouteSuggestion } from '../../../services/OpenRouteService';

import styles from './LocationSearchInput.module.scss';

export type SelectedLocation = {
  address: string;
  lat: number | null;
  lng: number | null;
};

type LocationSearchInputProps = {
  id: string;
  label: string;
  value: SelectedLocation;
  onChange: (next: SelectedLocation) => void;
  placeholder?: string;
  required?: boolean;
  helperText?: string;
  className?: string;
};

/**
 * Merge partial location updates with an optional base location object.
 *
 * @param overrides - Fields to override on the resulting location.
 * @param base - Optional existing location to merge with.
 * @returns Normalised location object containing address and coordinates.
 */
const buildLocation = (overrides: Partial<SelectedLocation>, base?: SelectedLocation): SelectedLocation => ({
  address: overrides.address ?? base?.address ?? '',
  lat: overrides.lat ?? base?.lat ?? null,
  lng: overrides.lng ?? base?.lng ?? null,
});

/**
 * Autocomplete input capturing a structured location from OpenRouteService results.
 *
 * @param props - Component props controlling labels, value, and callbacks.
 * @returns JSX fragment rendering the search input and matching suggestions.
 */
export const LocationSearchInput: React.FC<LocationSearchInputProps> = ({
  id,
  label,
  value,
  onChange,
  placeholder,
  required,
  helperText,
  className,
}) => {
  const [inputValue, setInputValue] = useState<string>(value.address ?? '');
  const [query, setQuery] = useState<string>('');
  const [suggestions, setSuggestions] = useState<OpenRouteSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    setInputValue(value.address ?? '');
  }, [value.address]);

  useEffect(() => {
    let isActive = true;

    const trimmed = query.trim();
    if (trimmed.length < 3) {
      setSuggestions([]);
      setIsLoading(false);
      setError(null);
      return undefined;
    }

    setIsLoading(true);
    setError(null);

    const timeoutId = window.setTimeout(() => {
      OpenRouteService.searchLocations(trimmed)
        .then((results) => {
          if (!isActive) return;
          setSuggestions(results);
        })
        .catch((serviceError) => {
          if (!isActive) return;
          setError(serviceError instanceof Error ? serviceError.message : 'Unable to search locations.');
          setSuggestions([]);
        })
        .finally(() => {
          if (!isActive) return;
          setIsLoading(false);
        });
    }, 350);

    return () => {
      isActive = false;
      window.clearTimeout(timeoutId);
    };
  }, [query]);

  const hasCoordinates = useMemo(() => value.lat !== null && value.lng !== null, [value.lat, value.lng]);

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextAddress = event.target.value;
    setInputValue(nextAddress);
    setQuery(nextAddress);
    onChange(buildLocation({ address: nextAddress, lat: null, lng: null }, value));
  };

  const handleSuggestionSelection = (suggestion: OpenRouteSuggestion) => {
    setInputValue(suggestion.label);
    setQuery(suggestion.label);
    setSuggestions([]);
    setIsFocused(false);
    setError(null);
    onChange(
      buildLocation(
        {
          address: suggestion.label,
          lat: suggestion.lat,
          lng: suggestion.lng,
        },
        value,
      ),
    );
  };

  const handleFocus = () => setIsFocused(true);
  const handleBlur = () => window.setTimeout(() => setIsFocused(false), 120);

  const suggestionListVisible = isFocused && (isLoading || error || suggestions.length > 0);

  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <div className={styles.inputWrapper}>
        <input
          id={id}
          className={styles.input}
          value={inputValue}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          required={required}
        />
        {suggestionListVisible && (
          <div className={styles.suggestions} role="listbox">
            {isLoading && <div className={styles.helper}>Searching…</div>}
            {error && !isLoading && <div className={styles.error}>{error}</div>}
            {!isLoading && !error &&
              suggestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion.id}
                  className={styles.suggestionButton}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleSuggestionSelection(suggestion)}
                >
                  <span>{suggestion.label}</span>
                  <span className={styles.suggestionMeta}>
                    {[
                      suggestion.context?.locality,
                      suggestion.context?.region,
                      suggestion.context?.country,
                    ]
                      .filter(Boolean)
                      .join(', ')}
                  </span>
                </button>
              ))}
            {!isLoading && !error && suggestions.length === 0 && query.trim().length >= 3 && (
              <div className={styles.helper}>No matches found. Try refining your search.</div>
            )}
          </div>
        )}
      </div>
      <div className={styles.statusLine}>
        {hasCoordinates ? (
          <span>
            Coordinates captured:{' '}
            <strong>
              {value.lat?.toFixed(5)}, {value.lng?.toFixed(5)}
            </strong>
          </span>
        ) : (
          <span>{helperText ?? 'Select a suggestion to capture coordinates.'}</span>
        )}
      </div>
    </div>
  );
};
