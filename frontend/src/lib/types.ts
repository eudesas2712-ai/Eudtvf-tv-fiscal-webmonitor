export type MonitoredItem = {
  title: string;
  url: string;
  matched_terms: {
    terms: string[];
  };
  source_name: string;
  created_at: string | null;
};

export type BannerItem = {
  page_url: string;
  image_url: string;
  alt_text?: string | null;
  width?: number | null;
  height?: number | null;
  pos_x?: number | null;
  pos_y?: number | null;
  source_name?: string | null;
  evidence_html_url?: string | null;
  screenshot_page_url?: string | null;
  screenshot_banner_url?: string | null;
  created_at?: string | null;
  ocr_text?: string | null;
  advertiser_name?: string | null;
};