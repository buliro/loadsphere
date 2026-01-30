import { graphqlRequest } from './graphql';
import type { DriverLogInput, DriverLogRecord, RawDriverLog } from '../types/logs';

const LOG_QUERIES = {
  driverLogs: `
    query DriverLogs($tripId: ID!) {
      myDriverLogs(tripId: $tripId) {
        id
        dayNumber
        logDate
        notes
        totalDistanceMiles
        totalDrivingMinutes
        totalOnDutyMinutes
        totalOffDutyMinutes
        totalSleeperMinutes
        segments {
          id
          status
          startTime
          endTime
          location
          activity
          remarks
        }
      }
    }
  `,
} as const;

const LOG_MUTATIONS = {
  createLog: `
    mutation CreateDriverLog(
      $tripId: ID!
      $dayNumber: Int!
      $logDate: String
      $notes: String
      $totalDistanceMiles: Float
      $segments: [DutySegmentInput!]!
    ) {
      createDriverLog(
        tripId: $tripId
        dayNumber: $dayNumber
        logDate: $logDate
        notes: $notes
        totalDistanceMiles: $totalDistanceMiles
        segments: $segments
      ) {
        success
        errors
        log {
          id
        }
      }
    }
  `,
  updateLog: `
    mutation UpdateDriverLog(
      $logId: ID!
      $logDate: String
      $notes: String
      $totalDistanceMiles: Float
      $segments: [DutySegmentInput!]!
    ) {
      updateDriverLog(
        logId: $logId
        logDate: $logDate
        notes: $notes
        totalDistanceMiles: $totalDistanceMiles
        segments: $segments
      ) {
        success
        errors
        log {
          id
        }
      }
    }
  `,
  deleteLog: `
    mutation DeleteDriverLog($logId: ID!) {
      deleteDriverLog(logId: $logId) {
        success
        errors
      }
    }
  `,
} as const;

const trimTime = (value: string | undefined | null): string => {
  if (!value) {
    return '';
  }

  return value.slice(0, 5);
};

const normaliseLog = (log: RawDriverLog): DriverLogRecord => {
  const segments = (log.segments ?? []).map((segment): DriverLogRecord['segments'][number] => ({
    id: segment.id ?? null,
    status: segment.status,
    startTime: trimTime(segment.startTime),
    endTime: trimTime(segment.endTime),
    location: segment.location ?? '',
    activity: segment.activity ?? '',
    remarks: segment.remarks ?? '',
  }));

  return {
    id: log.id,
    dayNumber: log.dayNumber,
    logDate: log.logDate,
    notes: log.notes ?? '',
    totalDistanceMiles: log.totalDistanceMiles ?? null,
    totalDrivingMinutes: log.totalDrivingMinutes,
    totalOnDutyMinutes: log.totalOnDutyMinutes,
    totalOffDutyMinutes: log.totalOffDutyMinutes ?? 0,
    totalSleeperMinutes: log.totalSleeperMinutes ?? 0,
    segments,
  };
};

export const LogsService = {
  async fetchDriverLogs(tripId: string): Promise<DriverLogRecord[]> {
    const data = await graphqlRequest<{
      myDriverLogs: RawDriverLog[];
    }>(LOG_QUERIES.driverLogs, {
      variables: { tripId },
    });

    const logs = data?.myDriverLogs ?? [];
    return logs.map(normaliseLog).sort((a, b) => a.dayNumber - b.dayNumber);
  },

  async createDriverLog(
    tripId: string,
    input: DriverLogInput & { dayNumber: number },
  ): Promise<{ success: boolean; errors: string[] }> {
    const payload = await graphqlRequest<{
      createDriverLog: { success: boolean; errors?: string[] | null };
    }>(LOG_MUTATIONS.createLog, {
      variables: {
        tripId,
        dayNumber: input.dayNumber,
        logDate: input.logDate,
        notes: input.notes,
        totalDistanceMiles: input.totalDistanceMiles,
        segments: input.segments,
      },
    });

    const result = payload?.createDriverLog;
    return {
      success: Boolean(result?.success),
      errors: result?.errors ?? [],
    };
  },

  async updateDriverLog(
    logId: string,
    input: DriverLogInput,
  ): Promise<{ success: boolean; errors: string[] }> {
    const payload = await graphqlRequest<{
      updateDriverLog: { success: boolean; errors?: string[] | null };
    }>(LOG_MUTATIONS.updateLog, {
      variables: {
        logId,
        logDate: input.logDate,
        notes: input.notes,
        totalDistanceMiles: input.totalDistanceMiles,
        segments: input.segments,
      },
    });

    const result = payload?.updateDriverLog;
    return {
      success: Boolean(result?.success),
      errors: result?.errors ?? [],
    };
  },

  async deleteDriverLog(logId: string): Promise<{ success: boolean; errors: string[] }> {
    const payload = await graphqlRequest<{
      deleteDriverLog: { success: boolean; errors?: string[] | null };
    }>(LOG_MUTATIONS.deleteLog, {
      variables: { logId },
    });

    const result = payload?.deleteDriverLog;
    return {
      success: Boolean(result?.success),
      errors: result?.errors ?? [],
    };
  },
};
