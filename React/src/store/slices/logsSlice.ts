import { createAsyncThunk, createSelector, createSlice } from '@reduxjs/toolkit';

import { LogsService } from '../../services/LogsService';
import type { DriverLogInput, DriverLogRecord } from '../../types/logs';
import type { RootState } from '../configureStore';

type LogsState = {
  records: DriverLogRecord[];
  loading: boolean;
  error: string | null;
};

const initialState: LogsState = {
  records: [],
  loading: false,
  error: null,
};

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;

export const fetchDriverLogs = createAsyncThunk<DriverLogRecord[], { tripId: string }, { rejectValue: string }>(
  'logs/fetchDriverLogs',
  async ({ tripId }, { rejectWithValue }) => {
    try {
      return await LogsService.fetchDriverLogs(tripId);
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Unable to load driver logs'));
    }
  },
);

export const createDriverLog = createAsyncThunk<DriverLogRecord[], { tripId: string; input: DriverLogInput & { dayNumber: number } }, { rejectValue: string }>(
  'logs/createDriverLog',
  async ({ tripId, input }, { rejectWithValue }) => {
    try {
      const result = await LogsService.createDriverLog(tripId, input);
      if (!result.success) {
        return rejectWithValue((result.errors ?? []).join('\n') || 'Unable to create driver log');
      }
      return await LogsService.fetchDriverLogs(tripId);
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Unable to create driver log'));
    }
  },
);

export const updateDriverLog = createAsyncThunk<DriverLogRecord[], { tripId: string; logId: string; input: DriverLogInput }, { rejectValue: string }>(
  'logs/updateDriverLog',
  async ({ tripId, logId, input }, { rejectWithValue }) => {
    try {
      const result = await LogsService.updateDriverLog(logId, input);
      if (!result.success) {
        return rejectWithValue((result.errors ?? []).join('\n') || 'Unable to update driver log');
      }
      return await LogsService.fetchDriverLogs(tripId);
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Unable to update driver log'));
    }
  },
);

export const deleteDriverLog = createAsyncThunk<DriverLogRecord[], { tripId: string; logId: string }, { rejectValue: string }>(
  'logs/deleteDriverLog',
  async ({ tripId, logId }, { rejectWithValue }) => {
    try {
      const result = await LogsService.deleteDriverLog(logId);
      if (!result.success) {
        return rejectWithValue((result.errors ?? []).join('\n') || 'Unable to delete driver log');
      }
      return await LogsService.fetchDriverLogs(tripId);
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Unable to delete driver log'));
    }
  },
);

const logsSlice = createSlice({
  name: 'logs',
  initialState,
  reducers: {
    clearLogs(state) {
      state.records = [];
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDriverLogs.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDriverLogs.fulfilled, (state, action) => {
        state.loading = false;
        state.records = action.payload;
        state.error = null;
      })
      .addCase(fetchDriverLogs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload ?? state.error;
        state.records = [];
      })
      .addCase(createDriverLog.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createDriverLog.fulfilled, (state, action) => {
        state.loading = false;
        state.records = action.payload;
        state.error = null;
      })
      .addCase(createDriverLog.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload ?? state.error;
      })
      .addCase(updateDriverLog.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateDriverLog.fulfilled, (state, action) => {
        state.loading = false;
        state.records = action.payload;
        state.error = null;
      })
      .addCase(updateDriverLog.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload ?? state.error;
      })
      .addCase(deleteDriverLog.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteDriverLog.fulfilled, (state, action) => {
        state.loading = false;
        state.records = action.payload;
        state.error = null;
      })
      .addCase(deleteDriverLog.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload ?? state.error;
      });
  },
});

export const { clearLogs } = logsSlice.actions;
export const logsReducer = logsSlice.reducer;

const selectLogsState = (state: RootState): LogsState => state.logs;

export const selectDriverLogs = (state: RootState) => selectLogsState(state).records;
export const selectLogsLoading = (state: RootState) => selectLogsState(state).loading;
export const selectLogsError = (state: RootState) => selectLogsState(state).error;

export const selectLogsViewModel = createSelector([selectLogsState], (logs) => ({
  records: logs.records,
  loading: logs.loading,
  error: logs.error,
  hasLogs: logs.records.length > 0,
}));

export type { LogsState };
