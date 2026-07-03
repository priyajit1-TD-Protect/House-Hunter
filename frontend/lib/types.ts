export interface ListingScore {
  id?: string;
  listing_id: string;
  total_score: number;
  income_score: number;
  school_score: number;
  transit_score: number;
  price_score: number;
  size_score: number;
  lifestyle_score: number;
  neighbourhood_income: number;
  school_rating: number;
  transit_min: number;
  scored_at?: string;
}

export interface Listing {
  id: string;
  address: string;
  neighbourhood: string | null;
  city: string;
  price: number;
  beds: number | null;
  baths: number | null;
  sqft: number | null;
  listing_type: string | null;
  listed_date: string | null;
  realtor_url: string | null;
  img_url: string | null;
  lat: number | null;
  lng: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  listing_scores: ListingScore[];
}

export interface Neighbourhood {
  id: number;
  name: string;
  avg_income: number | null;
  school_rating: number | null;
  transit_min_union: number | null;
  lifestyle_score: number | null;
}

export interface Stats {
  active_count: number;
  avg_score: number;
  best_score: number;
  min_price: number;
  max_price: number;
}

export type SortOption = "score" | "price_asc" | "price_desc" | "transit" | "school";

export interface FilterState {
  maxPrice: number;
  minScore: number;
  neighbourhood: string;
  sortBy: SortOption;
}
