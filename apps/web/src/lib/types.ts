// Tipos espejo de las respuestas de la API (apps/api).

export type Sport = "soccer" | "american_football";
export type MatchStatus = "scheduled" | "live" | "finished" | "postponed";

export interface Competition {
  code: string;
  name: string;
  sport: Sport;
  country: string | null;
  tier: number | null;
  is_mock: boolean;
}

export interface TeamRef {
  code: string;
  name: string;
  short_name: string | null;
}

export interface Match {
  id: number;
  sport: Sport;
  competition_code: string;
  season_label: string;
  home_team: TeamRef;
  away_team: TeamRef;
  kickoff_utc: string;
  status: MatchStatus;
  home_score: number | null;
  away_score: number | null;
  venue_name: string | null;
  stage: string | null;
  is_mock: boolean;
}

export interface MatchList {
  items: Match[];
  total: number;
  limit: number;
  offset: number;
  contains_mock: boolean;
}

export type Role = "user" | "analyst" | "admin";
export type Plan = "free" | "pro" | "analyst";

export interface User {
  id: number;
  email: string;
  role: Role;
  plan: Plan;
  email_verified: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface PredictionFactor {
  label: string;
  favors: "home" | "away" | "none";
  detail: string;
}

export interface CalibrationBin {
  lower: number;
  upper: number;
  mean_predicted: number;
  observed_frequency: number;
  count: number;
}

export interface BandPerformance {
  band: string;
  n: number;
  accuracy: number;
  brier: number;
}

export interface Performance {
  model_name: string;
  n_predictions: number;
  accuracy: number;
  brier: number;
  log_loss: number;
  baseline_brier: number;
  baseline_log_loss: number;
  beats_baseline: boolean;
  ece: number;
  calibration: CalibrationBin[];
  by_band: BandPerformance[];
  is_mock: boolean;
  disclaimer: string;
}

export interface TrackRecord {
  n_predictions: number;
  n_resolved: number;
  accuracy: number;
  brier: number;
  log_loss: number;
  note: string;
}

export interface StoredPrediction {
  match_id: number;
  competition_code: string;
  home_name: string;
  away_name: string;
  kickoff_utc: string;
  probabilities: { home: number; draw: number; away: number };
  confidence_band: string;
  model: string;
  resolved: boolean;
  actual: string | null;
  home_score: number | null;
  away_score: number | null;
  correct_pick: boolean | null;
}

export interface Prediction {
  match_id: number;
  model: { name: string; version: string };
  probabilities: { home: number; draw: number; away: number };
  expected_goals: { home: number; away: number };
  likely_scoreline: string;
  markets: {
    over_under: { line: number; over: number; under: number }[];
    btts: number | null;
  };
  confidence: {
    score: number;
    band: "baja" | "media" | "alta";
    decisiveness: number;
    data_quality: number;
    criterion: string;
  };
  ratings: { home: number; away: number };
  history_counts: { home: number; away: number };
  factors: PredictionFactor[];
  context: { kind: string; team: string; message: string }[];
  is_mock: boolean;
  disclaimer: string;
}
