begin;

create table if not exists gestionale_v2.prospect (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null
    references gestionale_v2.aziende(id) on delete cascade,
  nome text not null,
  cognome text not null,
  telefono text,
  whatsapp text,
  email text,
  fonte text,
  interesse text,
  stato text not null default 'Nuovo'
    check (
      stato in (
        'Nuovo',
        'Da ricontattare',
        'Interessato',
        'In valutazione',
        'Non interessato',
        'Convertito'
      )
    ),
  operatore_assegnato text,
  data_primo_contatto date not null default current_date,
  note text,
  cliente_id uuid
    references gestionale_v2.clienti(id) on delete set null,
  converted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_prospect_azienda_stato
on gestionale_v2.prospect (azienda_id, stato, created_at desc);

create unique index if not exists uq_prospect_cliente_convertito
on gestionale_v2.prospect (cliente_id)
where cliente_id is not null;

alter table gestionale_v2.prospect enable row level security;

grant select, insert, update
on gestionale_v2.prospect
to service_role;

commit;

notify pgrst, 'reload schema';
