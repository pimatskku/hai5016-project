create table if not exists public.campus_menu_items (
  id uuid primary key default gen_random_uuid(),

  source_id uuid not null references public.campus_menu_sources(id),
  snapshot_id uuid references public.scraped_html_snapshots(id),

  source_url text not null default '',
  university text not null default '',
  campus text not null default '',
  restaurant_name text not null default '',

  menu_date date,
  meal_type text not null default 'unknown'
    check (meal_type in ('breakfast', 'lunch', 'dinner', 'unknown')),

  meal_name text not null,
  price_krw text not null default '',
  serving_time text not null default '',

  raw_text text not null default '',
  is_valid_menu boolean not null default true,
  name_confidence numeric(4,3) not null default 0
    check (name_confidence >= 0 and name_confidence <= 1),

  parser_model text not null default '',
  parser_run_id text not null default '',

  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  seen_count integer not null default 1,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint campus_menu_items_unique_menu
    unique (
      source_id,
      menu_date,
      meal_type,
      restaurant_name,
      meal_name,
      price_krw,
      serving_time
    )
);

create index if not exists campus_menu_items_date_idx
on public.campus_menu_items (menu_date);

create index if not exists campus_menu_items_source_date_idx
on public.campus_menu_items (source_id, menu_date);

create index if not exists campus_menu_items_university_date_idx
on public.campus_menu_items (university, menu_date);

create index if not exists campus_menu_items_valid_date_idx
on public.campus_menu_items (is_valid_menu, menu_date);
