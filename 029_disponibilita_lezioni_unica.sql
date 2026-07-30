begin;

create or replace view gestionale_v2.vista_disponibilita_lezioni
with (security_invoker = false)
as
with periodi as (
  select
    a.azienda_id,
    a.id as abbonamento_id,
    a.cliente_id,
    a.pacchetto_id,
    a.data_inizio,
    a.data_fine_prevista,
    a.stato,
    a.lezioni_iniziali,
    p.nome as pacchetto,
    p.modalita_lezioni,
    coalesce(p.lezioni_per_periodo, 0)::integer
      as quota_configurata,
    case
      when p.modalita_lezioni = 'Settimanale'
        then date_trunc('week', current_date)::date
      when p.modalita_lezioni = 'Mensile'
        then date_trunc('month', current_date)::date
      else null
    end as periodo_inizio,
    case
      when p.modalita_lezioni = 'Settimanale'
        then (
          date_trunc('week', current_date)::date
          + interval '6 days'
        )::date
      when p.modalita_lezioni = 'Mensile'
        then (
          date_trunc('month', current_date)
          + interval '1 month'
          - interval '1 day'
        )::date
      else null
    end as periodo_fine
  from gestionale_v2.abbonamenti a
  join gestionale_v2.pacchetti p
    on p.id = a.pacchetto_id
),
movimenti as (
  select
    p.abbonamento_id,
    coalesce(
      sum(m.quantita)
        filter (where m.stato = 'valido'),
      0
    )::integer as movimenti_netto_complessivo,

    greatest(
      -coalesce(
        sum(m.quantita)
          filter (
            where m.stato = 'valido'
              and m.prenotazione_id is not null
          ),
        0
      ),
      0
    )::integer as presenze_totali,

    greatest(
      -coalesce(
        sum(m.quantita)
          filter (
            where m.stato = 'valido'
              and m.prenotazione_id is not null
              and coalesce(
                pr.data_prenotazione,
                m.data_movimento
              ) between p.periodo_inizio and p.periodo_fine
          ),
        0
      ),
      0
    )::integer as utilizzate_periodo
  from periodi p
  left join gestionale_v2.movimenti_lezioni m
    on m.abbonamento_id = p.abbonamento_id
  left join gestionale_v2.prenotazioni pr
    on pr.id = m.prenotazione_id
  group by p.abbonamento_id
)
select
  p.azienda_id,
  p.abbonamento_id,
  p.cliente_id,
  p.pacchetto_id,
  p.pacchetto,
  p.data_inizio,
  p.data_fine_prevista,
  p.stato,
  p.modalita_lezioni,

  (
    p.stato not in (
      'terminato',
      'chiuso_anticipatamente',
      'annullato'
    )
    and p.data_inizio <= current_date
    and (
      p.data_fine_prevista is null
      or p.data_fine_prevista >= current_date
    )
  ) as corrente,

  p.periodo_inizio,
  p.periodo_fine,

  case
    when p.modalita_lezioni in ('Settimanale', 'Mensile')
      then p.quota_configurata
    else null
  end::integer as quota_periodo,

  case
    when p.modalita_lezioni in ('Settimanale', 'Mensile')
      then coalesce(m.utilizzate_periodo, 0)
    else null
  end::integer as utilizzate_periodo,

  case
    when p.modalita_lezioni in ('Settimanale', 'Mensile')
      then greatest(
        p.quota_configurata
        - coalesce(m.utilizzate_periodo, 0),
        0
      )
    else null
  end::integer as disponibili_periodo,

  p.lezioni_iniziali::integer as lezioni_contrattuali,
  coalesce(m.presenze_totali, 0)::integer as presenze_totali,

  (
    p.lezioni_iniziali
    + coalesce(m.movimenti_netto_complessivo, 0)
  )::integer as saldo_complessivo,

  case
    when p.modalita_lezioni = 'Settimanale' then
      greatest(
        p.quota_configurata
        - coalesce(m.utilizzate_periodo, 0),
        0
      )::text
      || ' disponibili su '
      || p.quota_configurata::text
      || ' questa settimana'

    when p.modalita_lezioni = 'Mensile' then
      greatest(
        p.quota_configurata
        - coalesce(m.utilizzate_periodo, 0),
        0
      )::text
      || ' disponibili su '
      || p.quota_configurata::text
      || ' questo mese'

    else
      (
        p.lezioni_iniziali
        + coalesce(m.movimenti_netto_complessivo, 0)
      )::text
      || ' residue su '
      || p.lezioni_iniziali::text
  end as disponibilita_principale,

  case
    when p.modalita_lezioni in ('Settimanale', 'Mensile') then
      coalesce(m.presenze_totali, 0)::text
      || ' effettuate su '
      || p.lezioni_iniziali::text
      || ' previste · '
      || greatest(
        p.lezioni_iniziali
        + coalesce(m.movimenti_netto_complessivo, 0),
        0
      )::text
      || ' teoriche residue'

    else
      coalesce(m.presenze_totali, 0)::text
      || ' lezioni effettuate'
  end as disponibilita_secondaria

from periodi p
left join movimenti m
  on m.abbonamento_id = p.abbonamento_id;


grant select
on gestionale_v2.vista_disponibilita_lezioni
to service_role;

commit;

notify pgrst, 'reload schema';
