import { createAsyncThunk, createSelector, createSlice } from '@reduxjs/toolkit';

import { RoutesService } from '../../services/RoutesService';
import type { ActiveRouteSummary } from '../../types/routes';
import type { RootState } from '../configureStore';

type RoutesState = {
  activeRoute: ActiveRouteSummary | null;
  loading: boolean;
  error: string | null;
  lastFetchedAt: string | null;
};

const initialState: RoutesState = {
  activeRoute: null,
  loading: false,
  error: null,
  lastFetchedAt: null,
};

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;

export const fetchActiveRoute = createAsyncThunk<ActiveRouteSummary | null, void, { rejectValue: string }>(
  'routes/fetchActiveRoute',
  async (_, { rejectWithValue }) => {
    try {
      return await RoutesService.fetchActiveRouteSummary();
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Unable to load active route'));
    }
  },
);

const routesSlice = createSlice({
  name: 'routes',
  initialState,
  reducers: {
    clearActiveRoute(state) {
      state.activeRoute = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchActiveRoute.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchActiveRoute.fulfilled, (state, action) => {
        state.loading = false;
        state.activeRoute = action.payload ?? null;
        state.error = null;
        state.lastFetchedAt = new Date().toISOString();
      })
      .addCase(fetchActiveRoute.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload ?? state.error;
        state.activeRoute = null;
      });
  },
});

export const { clearActiveRoute } = routesSlice.actions;
export const routesReducer = routesSlice.reducer;

const selectRoutesState = (state: RootState): RoutesState => state.routes;

export const selectActiveRoute = (state: RootState) => selectRoutesState(state).activeRoute;
export const selectRoutesLoading = (state: RootState) => selectRoutesState(state).loading;
export const selectRoutesError = (state: RootState) => selectRoutesState(state).error;
export const selectRoutesLastFetchedAt = (state: RootState) => selectRoutesState(state).lastFetchedAt;

export const selectRoutesViewModel = createSelector([selectRoutesState], (routes) => ({
  activeRoute: routes.activeRoute,
  loading: routes.loading,
  error: routes.error,
  hasActiveRoute: Boolean(routes.activeRoute),
  lastFetchedAt: routes.lastFetchedAt,
}));

export type { RoutesState };
