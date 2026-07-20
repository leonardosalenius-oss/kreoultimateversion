# Architettura v0.11

## Documenti

- Supabase Storage conserva i file.
- `documenti_clienti` conserva metadati e percorso.
- Il bucket è privato.
- L'apertura avviene tramite URL firmato di breve durata.
- Ogni upload usa un percorso univoco:
  `azienda_id/cliente_id/tipo_documento/uuid_nomefile`.
- La sostituzione non sovrascrive il file precedente.
- L'annullamento è logico, non distruttivo.
