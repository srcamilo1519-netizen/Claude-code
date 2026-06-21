export interface TimestampHighlight {
  timestamp: string;
  description: string;
}

export interface VideoSummary {
  titulo: string;
  puntos_clave: string[];
  resumen_extendido: string;
  timestamps_relevantes: TimestampHighlight[];
  conclusion_cta: string;
}

export interface SummaryListItem {
  id: number;
  youtube_url: string;
  video_title: string;
  video_duration: number;
  transcript_length: number;
  processing_time_seconds: number;
  created_at: string;
}

export interface SummaryDetail extends SummaryListItem {
  summary: VideoSummary;
}
