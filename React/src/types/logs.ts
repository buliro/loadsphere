export type RawDutySegment = {
  id: string;
  status: string;
  startTime: string;
  endTime: string;
  location?: string | null;
  activity?: string | null;
  remarks?: string | null;
};

export type RawDriverLog = {
  id: string;
  dayNumber: number;
  logDate: string;
  notes?: string | null;
  totalDistanceMiles?: number | null;
  totalDrivingMinutes: number;
  totalOnDutyMinutes: number;
  totalOffDutyMinutes?: number | null;
  totalSleeperMinutes?: number | null;
  segments?: RawDutySegment[] | null;
};

export type DriverLogSegment = {
  id: string | null;
  status: string;
  startTime: string;
  endTime: string;
  location: string;
  activity: string;
  remarks: string;
};

export type DriverLogRecord = {
  id: string;
  dayNumber: number;
  logDate: string;
  notes: string;
  totalDistanceMiles: number | null;
  totalDrivingMinutes: number;
  totalOnDutyMinutes: number;
  totalOffDutyMinutes: number;
  totalSleeperMinutes: number;
  segments: DriverLogSegment[];
};

export type DriverLogSegmentInput = {
  status: string;
  startTime: string;
  endTime: string;
  location?: string;
  activity?: string;
  remarks?: string;
};

export type DriverLogInput = {
  dayNumber?: number;
  logDate?: string;
  notes?: string;
  totalDistanceMiles?: number | null;
  segments: DriverLogSegmentInput[];
};
