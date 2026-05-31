-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE IF NOT EXISTS public.campus_menu_sources (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  university_name text NOT NULL,
  city text,
  campus text,
  source_url text NOT NULL,
  notes text,
  team integer,
  valid boolean NOT NULL DEFAULT true,
  last_scraped_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  content_div_selector text,
  CONSTRAINT campus_menu_sources_pkey PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS public.fx_rates_daily_cache (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  provider text NOT NULL DEFAULT 'exchangerate-api'::text,
  base_code text NOT NULL,
  cache_date date NOT NULL DEFAULT ((now() AT TIME ZONE 'utc'::text))::date,
  fetched_at timestamp with time zone NOT NULL DEFAULT now(),
  raw_response jsonb NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  quote_code text NOT NULL,
  rate double precision NOT NULL,
  CONSTRAINT fx_rates_daily_cache_pkey PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS public.scraped_html_snapshots (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL,
  source_url text NOT NULL,
  scraped_at timestamp with time zone NOT NULL DEFAULT now(),
  scrape_date date NOT NULL DEFAULT ((now() AT TIME ZONE 'utc'::text))::date,
  status_code integer,
  final_url text,
  content_type text,
  etag text,
  last_modified text,
  html_raw text NOT NULL,
  html_sha256 text NOT NULL,
  html_size_bytes integer,
  is_changed boolean NOT NULL DEFAULT true,
  previous_snapshot_id uuid,
  change_reason text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT scraped_html_snapshots_pkey PRIMARY KEY (id),
  CONSTRAINT scraped_html_snapshots_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.campus_menu_sources(id),
  CONSTRAINT scraped_html_snapshots_previous_snapshot_id_fkey FOREIGN KEY (previous_snapshot_id) REFERENCES public.scraped_html_snapshots(id)
);
CREATE TABLE IF NOT EXISTS public.user (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email character varying NOT NULL UNIQUE,
  password_hash character varying,
  display_name character varying,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  preferences jsonb,
  last_login timestamp with time zone,
  is_active boolean DEFAULT true,
  profile_image_url text,
  provider character varying,
  phone character varying,
  country character varying,
  language character varying,
  CONSTRAINT user_pkey PRIMARY KEY (id)
);
