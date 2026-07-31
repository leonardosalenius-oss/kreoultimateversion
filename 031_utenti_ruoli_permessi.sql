begin;

create extension if not exists pgcrypto;

create table if not exists gestionale_v2.ruoli_accesso (
  codice text primary key,
  nome text not null unique,
  descrizione text,
  livello integer not null default 0,
  attivo boolean not null default true
);

create table if not exists gestionale_v2.permessi_accesso (
  codice text primary key,
  descrizione text not null,
  area text not null
);

create table if not exists gestionale_v2.ruoli_permessi (
  ruolo_codice text not null references gestionale_v2.ruoli_accesso(codice) on delete cascade,
  permesso_codice text not null references gestionale_v2.permessi_accesso(codice) on delete cascade,
  primary key (ruolo_codice, permesso_codice)
);

create table if not exists gestionale_v2.utenti_aziende (
  id uuid primary key default gen_random_uuid(),
  azienda_id uuid not null references gestionale_v2.aziende(id) on delete cascade,
  auth_user_id uuid,
  email text not null,
  nome_visualizzato text not null,
  ruolo_codice text not null references gestionale_v2.ruoli_accesso(codice),
  attivo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  modificato_da text,
  unique (azienda_id, email)
);

create index if not exists idx_utenti_aziende_email
on gestionale_v2.utenti_aziende (lower(email));

create table if not exists gestionale_v2.audit_accessi (
  id bigint generated always as identity primary key,
  azienda_id uuid references gestionale_v2.aziende(id) on delete set null,
  email text not null,
  azione text not null,
  dettagli jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

insert into gestionale_v2.ruoli_accesso(codice,nome,descrizione,livello) values
('super_admin','Super Admin','Accesso completo multi-area',100),
('direzione','Direzione','Controllo direzionale e operativo',80),
('reception','Reception','Reception, clienti, agenda e incassi',60),
('trainer','Trainer','Agenda, presenze e clienti assegnati',40),
('contabilita','Contabilità','Incassi, costi, rate e report economici',60),
('magazzino','Magazzino','Prodotti, acquisti, vendite e inventario',50),
('lettura','Solo lettura','Consultazione senza modifiche',10)
on conflict (codice) do update set
nome=excluded.nome, descrizione=excluded.descrizione,
livello=excluded.livello, attivo=true;

insert into gestionale_v2.permessi_accesso(codice,descrizione,area) values
('reception.visualizza','Aprire Reception','Reception'),
('pacchetti.gestisci','Gestire pacchetti','Pacchetti'),
('abbonamenti.gestisci','Gestire abbonamenti','Abbonamenti'),
('clienti.visualizza','Visualizzare clienti','Clienti'),
('clienti.modifica','Creare e modificare clienti','Clienti'),
('contabilita.visualizza','Visualizzare contabilità','Contabilità'),
('contabilita.modifica','Registrare incassi e costi','Contabilità'),
('contabilita.annulla','Annullare movimenti contabili','Contabilità'),
('magazzino.visualizza','Visualizzare magazzino','Magazzino'),
('magazzino.modifica','Gestire movimenti magazzino','Magazzino'),
('report.visualizza','Visualizzare report','Report'),
('admin.visualizza','Visualizzare dashboard Admin','Admin'),
('utenti.gestisci','Gestire utenti e ruoli','Admin'),
('azienda.modifica','Modificare dati azienda','Azienda')
on conflict (codice) do update set descrizione=excluded.descrizione, area=excluded.area;

-- Super Admin: tutti i permessi
insert into gestionale_v2.ruoli_permessi(ruolo_codice,permesso_codice)
select 'super_admin', codice from gestionale_v2.permessi_accesso
on conflict do nothing;

-- Direzione
insert into gestionale_v2.ruoli_permessi values
('direzione','reception.visualizza'),('direzione','pacchetti.gestisci'),
('direzione','abbonamenti.gestisci'),('direzione','clienti.visualizza'),
('direzione','clienti.modifica'),('direzione','contabilita.visualizza'),
('direzione','contabilita.modifica'),('direzione','magazzino.visualizza'),
('direzione','magazzino.modifica'),('direzione','report.visualizza'),
('direzione','admin.visualizza')
on conflict do nothing;

-- Reception
insert into gestionale_v2.ruoli_permessi values
('reception','reception.visualizza'),('reception','clienti.visualizza'),
('reception','clienti.modifica'),('reception','abbonamenti.gestisci'),
('reception','contabilita.visualizza'),('reception','contabilita.modifica')
on conflict do nothing;

-- Trainer
insert into gestionale_v2.ruoli_permessi values
('trainer','reception.visualizza'),('trainer','clienti.visualizza')
on conflict do nothing;

-- Contabilità
insert into gestionale_v2.ruoli_permessi values
('contabilita','clienti.visualizza'),('contabilita','contabilita.visualizza'),
('contabilita','contabilita.modifica'),('contabilita','contabilita.annulla'),
('contabilita','report.visualizza'),('contabilita','admin.visualizza')
on conflict do nothing;

-- Magazzino
insert into gestionale_v2.ruoli_permessi values
('magazzino','magazzino.visualizza'),('magazzino','magazzino.modifica'),
('magazzino','report.visualizza')
on conflict do nothing;

-- Lettura
insert into gestionale_v2.ruoli_permessi values
('lettura','clienti.visualizza'),('lettura','contabilita.visualizza'),
('lettura','magazzino.visualizza'),('lettura','report.visualizza'),
('lettura','admin.visualizza')
on conflict do nothing;

create or replace view gestionale_v2.vista_accesso_utente as
select
  ua.id,
  ua.azienda_id,
  a.nome_visualizzato as azienda_nome,
  ua.auth_user_id,
  lower(ua.email) as email,
  ua.nome_visualizzato,
  ua.ruolo_codice,
  r.nome as ruolo_nome,
  r.livello,
  ua.attivo,
  coalesce(array_agg(rp.permesso_codice order by rp.permesso_codice)
    filter (where rp.permesso_codice is not null), array[]::text[]) as permessi
from gestionale_v2.utenti_aziende ua
join gestionale_v2.aziende a on a.id=ua.azienda_id
join gestionale_v2.ruoli_accesso r on r.codice=ua.ruolo_codice
left join gestionale_v2.ruoli_permessi rp on rp.ruolo_codice=ua.ruolo_codice
group by ua.id,a.nome_visualizzato,r.nome,r.livello;

create or replace view gestionale_v2.vista_utenti_accessi as
select * from gestionale_v2.vista_accesso_utente;

create or replace function gestionale_v2.salva_accesso_utente(payload jsonb)
returns jsonb language plpgsql security definer set search_path=gestionale_v2,public as $$
declare v_id uuid; v_result jsonb;
begin
  insert into gestionale_v2.utenti_aziende(
    id,azienda_id,auth_user_id,email,nome_visualizzato,ruolo_codice,attivo,modificato_da
  ) values (
    coalesce(nullif(payload->>'id','')::uuid,gen_random_uuid()),
    (payload->>'azienda_id')::uuid,
    nullif(payload->>'auth_user_id','')::uuid,
    lower(trim(payload->>'email')),
    trim(payload->>'nome_visualizzato'),
    payload->>'ruolo_codice',
    coalesce((payload->>'attivo')::boolean,true),
    payload->>'modificato_da'
  )
  on conflict (azienda_id,email) do update set
    auth_user_id=coalesce(excluded.auth_user_id,utenti_aziende.auth_user_id),
    nome_visualizzato=excluded.nome_visualizzato,
    ruolo_codice=excluded.ruolo_codice,
    attivo=excluded.attivo,
    modificato_da=excluded.modificato_da,
    updated_at=now()
  returning id into v_id;
  select to_jsonb(v) into v_result from gestionale_v2.vista_utenti_accessi v where v.id=v_id;
  return v_result;
end $$;

create or replace function gestionale_v2.bootstrap_super_admin(payload jsonb)
returns jsonb language plpgsql security definer set search_path=gestionale_v2,public as $$
begin
  if exists(select 1 from gestionale_v2.utenti_aziende) then
    raise exception 'Bootstrap già completato';
  end if;
  return gestionale_v2.salva_accesso_utente(payload || jsonb_build_object('ruolo_codice','super_admin','attivo',true));
end $$;

create or replace function gestionale_v2.registra_audit_accesso(payload jsonb)
returns void language plpgsql security definer set search_path=gestionale_v2,public as $$
begin
  insert into gestionale_v2.audit_accessi(azienda_id,email,azione,dettagli)
  values (nullif(payload->>'azienda_id','')::uuid,lower(payload->>'email'),payload->>'azione',coalesce(payload->'dettagli','{}'::jsonb));
end $$;

grant select on gestionale_v2.ruoli_accesso, gestionale_v2.permessi_accesso,
  gestionale_v2.ruoli_permessi, gestionale_v2.utenti_aziende,
  gestionale_v2.audit_accessi, gestionale_v2.vista_accesso_utente,
  gestionale_v2.vista_utenti_accessi to service_role;
grant insert,update on gestionale_v2.utenti_aziende to service_role;
grant execute on function gestionale_v2.salva_accesso_utente(jsonb) to service_role;
grant execute on function gestionale_v2.bootstrap_super_admin(jsonb) to service_role;
grant execute on function gestionale_v2.registra_audit_accesso(jsonb) to service_role;

commit;
notify pgrst, 'reload schema';
