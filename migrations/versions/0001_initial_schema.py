"""Снимок начальной схемы PostgreSQL; после публикации не менять её DDL."""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

TABLE_DDL = (
    (
        "CREATE TABLE eval_cases (\n\tid UUID NOT NULL, \n\tcase_key VARCHAR(128)"
        " NOT NULL, \n\tsplit VARCHAR(16) NOT NULL, \n\tinput_json JSONB NOT NULL"
        ", \n\texpected_json JSONB NOT NULL, \n\tprovenance_json JSONB NOT NULL, "
        "\n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIM"
        "ARY KEY (id), \n\tUNIQUE (case_key)\n)"
    ),
    (
        "CREATE TABLE eval_runs (\n\tid UUID NOT NULL, \n\tconfig_versions_json J"
        "SONB NOT NULL, \n\tsnapshot_ref VARCHAR(512) NOT NULL, \n\tstarted_at TI"
        "MESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcompleted_at TIMEST"
        "AMP WITH TIME ZONE, \n\tPRIMARY KEY (id)\n)"
    ),
    (
        "CREATE TABLE index_generations (\n\tid UUID NOT NULL, \n\tparent_id UUID"
        ", \n\tconfig_versions_json JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH"
        " TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY"
        "(parent_id) REFERENCES index_generations (id) ON DELETE SET NULL\n)"
    ),
    (
        "CREATE TABLE ingestion_jobs (\n\tid UUID NOT NULL, \n\tsource VARCHAR(32"
        ") NOT NULL, \n\texternal_id VARCHAR(512) NOT NULL, \n\tpayload_hash VARC"
        "HAR(64) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tattempts INTEGER "
        "NOT NULL, \n\tlease_token BIGINT NOT NULL, \n\tlease_until TIMESTAMP WIT"
        "H TIME ZONE, \n\terror_code VARCHAR(128), \n\tcreated_at TIMESTAMP WITH "
        "TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT c"
        "k_ingestion_jobs_status CHECK (status IN ('pending','running','compl"
        "eted','failed')), \n\tCONSTRAINT ck_ingestion_jobs_attempts CHECK (att"
        "empts >= 0), \n\tCONSTRAINT uq_ingestion_jobs_idempotency UNIQUE (sour"
        "ce, external_id, payload_hash)\n)"
    ),
    (
        "CREATE TABLE outbox_events (\n\tid UUID NOT NULL, \n\taggregate_id UUID "
        "NOT NULL, \n\tkind VARCHAR(128) NOT NULL, \n\tpayload_json JSONB NOT NUL"
        "L, \n\tattempts INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZON"
        "E DEFAULT now() NOT NULL, \n\tprocessed_at TIMESTAMP WITH TIME ZONE, \n"
        "\tPRIMARY KEY (id)\n)"
    ),
    (
        "CREATE TABLE source_documents (\n\tid UUID NOT NULL, \n\tsource VARCHAR("
        "32) NOT NULL, \n\texternal_id VARCHAR(512) NOT NULL, \n\tcanonical_url T"
        "EXT NOT NULL, \n\tkind VARCHAR(32) NOT NULL, \n\ttitle TEXT NOT NULL, \n\t"
        "publication_date DATE, \n\tactive_revision_id UUID, \n\tcreated_at TIMES"
        "TAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCO"
        "NSTRAINT uq_source_documents_source_external UNIQUE (source, externa"
        "l_id)\n)"
    ),
    (
        "CREATE TABLE users (\n\tid UUID NOT NULL, \n\temail_normalized VARCHAR(3"
        "20), \n\tpassword_hash VARCHAR(512), \n\tauth_subject VARCHAR(512), \n\tcr"
        "eated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tdisabled"
        "_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_us"
        "ers_identity CHECK (email_normalized IS NOT NULL OR auth_subject IS "
        "NOT NULL), \n\tUNIQUE (email_normalized), \n\tUNIQUE (auth_subject)\n)"
    ),
    (
        "CREATE TABLE auth_sessions (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT N"
        "ULL, \n\ttoken_hash VARCHAR(128) NOT NULL, \n\tcsrf_secret_hash VARCHAR("
        "128) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() N"
        "OT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked_a"
        "t TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_auth"
        "_sessions_token_hash CHECK (length(token_hash) >= 32), \n\tCONSTRAINT "
        "ck_auth_sessions_csrf_hash CHECK (length(csrf_secret_hash) >= 32), \n"
        "\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)"
    ),
    (
        "CREATE TABLE conversations (\n\tid UUID NOT NULL, \n\towner_user_id UUID"
        " NOT NULL, \n\ttitle VARCHAR(512), \n\tsummary_json JSONB, \n\tsummary_unt"
        "il_message_id UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT no"
        "w() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NO"
        "T NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_conversations_id_owner U"
        "NIQUE (id, owner_user_id), \n\tFOREIGN KEY(owner_user_id) REFERENCES u"
        "sers (id) ON DELETE CASCADE\n)"
    ),
    (
        "CREATE TABLE document_revisions (\n\tid UUID NOT NULL, \n\tdocument_id U"
        "UID NOT NULL, \n\tsource_updated_at TIMESTAMP WITH TIME ZONE, \n\tconten"
        "t_hash VARCHAR(64) NOT NULL, \n\tnormalized_json JSONB NOT NULL, \n\ting"
        "est_state VARCHAR(24) NOT NULL, \n\tretrieved_at TIMESTAMP WITH TIME Z"
        "ONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_docu"
        "ment_revisions_id_document UNIQUE (id, document_id), \n\tCONSTRAINT uq"
        "_document_revisions_document_hash UNIQUE (document_id, content_hash)"
        ", \n\tCONSTRAINT ck_document_revisions_ingest_state CHECK (ingest_stat"
        "e IN ('discovered','normalized','indexed','failed')), \n\tFOREIGN KEY("
        "document_id) REFERENCES source_documents (id) ON DELETE CASCADE\n)"
    ),
    (
        "CREATE TABLE eval_results (\n\tid UUID NOT NULL, \n\teval_run_id UUID NO"
        "T NULL, \n\teval_case_id UUID NOT NULL, \n\tresult_json JSONB NOT NULL, "
        "\n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIM"
        "ARY KEY (id), \n\tCONSTRAINT uq_eval_results_run_case UNIQUE (eval_run"
        "_id, eval_case_id), \n\tFOREIGN KEY(eval_run_id) REFERENCES eval_runs "
        "(id) ON DELETE CASCADE, \n\tFOREIGN KEY(eval_case_id) REFERENCES eval_"
        "cases (id) ON DELETE RESTRICT\n)"
    ),
    (
        "CREATE TABLE index_catalog (\n\tid SMALLINT NOT NULL, \n\tcurrent_genera"
        "tion_id UUID, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_index_catalog_sing"
        "leton CHECK (id = 1), \n\tFOREIGN KEY(current_generation_id) REFERENCE"
        "S index_generations (id) ON DELETE RESTRICT\n)"
    ),
    (
        "CREATE TABLE evidence_chunks (\n\tid UUID NOT NULL, \n\trevision_id UUID"
        " NOT NULL, \n\tsection VARCHAR(256) NOT NULL, \n\tordinal INTEGER NOT NU"
        "LL, \n\ttext TEXT NOT NULL, \n\tsection_start INTEGER NOT NULL, \n\tsectio"
        "n_end INTEGER NOT NULL, \n\thash VARCHAR(64) NOT NULL, \n\tlanguage VARC"
        "HAR(16) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_evidence_chunk"
        "s_id_revision UNIQUE (id, revision_id), \n\tCONSTRAINT uq_chunks_revis"
        "ion_section_ordinal_hash UNIQUE (revision_id, section, ordinal, hash"
        "), \n\tCONSTRAINT ck_evidence_chunks_offsets CHECK (ordinal >= 0 AND s"
        "ection_start >= 0 AND section_end >= section_start), \n\tFOREIGN KEY(r"
        "evision_id) REFERENCES document_revisions (id) ON DELETE RESTRICT\n)"
    ),
    (
        "CREATE TABLE ideas (\n\tid UUID NOT NULL, \n\tconversation_id UUID NOT N"
        "ULL, \n\tcurrent_version_id UUID, \n\tcreated_at TIMESTAMP WITH TIME ZON"
        "E DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_ideas_"
        "id_conversation UNIQUE (id, conversation_id), \n\tFOREIGN KEY(conversa"
        "tion_id) REFERENCES conversations (id) ON DELETE CASCADE, \n\tUNIQUE ("
        "conversation_id), \n\tFOREIGN KEY(conversation_id) REFERENCES conversa"
        "tions (id) ON DELETE CASCADE\n)"
    ),
    (
        "CREATE TABLE index_members (\n\tgeneration_id UUID NOT NULL, \n\tdocumen"
        "t_id UUID NOT NULL, \n\trevision_id UUID NOT NULL, \n\tPRIMARY KEY (gene"
        "ration_id, document_id), \n\tCONSTRAINT fk_index_members_revision_docu"
        "ment FOREIGN KEY(revision_id, document_id) REFERENCES document_revis"
        "ions (id, document_id), \n\tCONSTRAINT uq_index_members_generation_rev"
        "ision UNIQUE (generation_id, revision_id), \n\tFOREIGN KEY(generation_"
        "id) REFERENCES index_generations (id) ON DELETE CASCADE\n)"
    ),
    (
        "CREATE TABLE messages (\n\tid UUID NOT NULL, \n\tconversation_id UUID NO"
        "T NULL, \n\trole VARCHAR(16) NOT NULL, \n\tcontent TEXT NOT NULL, \n\tcrea"
        "ted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\trun_id UUI"
        "D, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_messages_role CHECK (role IN "
        "('user', 'assistant')), \n\tCONSTRAINT ck_messages_content_size CHECK "
        "(octet_length(content) <= 8192), \n\tCONSTRAINT uq_messages_id_convers"
        "ation UNIQUE (id, conversation_id), \n\tFOREIGN KEY(conversation_id) R"
        "EFERENCES conversations (id) ON DELETE CASCADE\n)"
    ),
    (
        "CREATE TABLE revision_index_acks (\n\tid UUID NOT NULL, \n\trevision_id "
        "UUID NOT NULL, \n\tbackend VARCHAR(32) NOT NULL, \n\tindexer_version VAR"
        "CHAR(128) NOT NULL, \n\tprojection_version VARCHAR(128) NOT NULL, \n\tac"
        "knowledged_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRI"
        "MARY KEY (id), \n\tFOREIGN KEY(revision_id) REFERENCES document_revisi"
        "ons (id) ON DELETE CASCADE, \n\tCONSTRAINT ck_revision_index_acks_back"
        "end CHECK (backend IN ('qdrant','domain_graph','lightrag_context')),"
        " \n\tCONSTRAINT uq_revision_index_acks_version UNIQUE (revision_id, ba"
        "ckend, indexer_version, projection_version)\n)"
    ),
    (
        "CREATE TABLE graph_facts (\n\tid UUID NOT NULL, \n\trevision_id UUID NOT"
        " NULL, \n\tfrom_key VARCHAR(512) NOT NULL, \n\tedge_type VARCHAR(128) NO"
        "T NULL, \n\tto_key VARCHAR(512) NOT NULL, \n\tchunk_id UUID, \n\tspan_star"
        "t INTEGER, \n\tspan_end INTEGER, \n\tmetadata_pointer JSONB, \n\tprovenanc"
        "e_kind VARCHAR(32) NOT NULL, \n\textractor_version VARCHAR(128) NOT NU"
        "LL, \n\tvocabulary_version VARCHAR(128) NOT NULL, \n\tconfidence FLOAT, "
        "\n\tvalidated_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tFOREI"
        "GN KEY(revision_id) REFERENCES document_revisions (id) ON DELETE CAS"
        "CADE, \n\tCONSTRAINT fk_graph_facts_chunk_revision FOREIGN KEY(chunk_i"
        "d, revision_id) REFERENCES evidence_chunks (id, revision_id), \n\tCONS"
        "TRAINT ck_graph_facts_span CHECK ((span_start IS NULL AND span_end I"
        "S NULL) OR (span_start >= 0 AND span_end >= span_start)), \n\tCONSTRAI"
        "NT ck_graph_facts_provenance CHECK (provenance_kind IN ('source_text"
        "','abstract','metadata','synthetic'))\n)"
    ),
    (
        "CREATE TABLE idea_versions (\n\tid UUID NOT NULL, \n\tidea_id UUID NOT N"
        "ULL, \n\tconversation_id UUID NOT NULL, \n\tversion_no INTEGER NOT NULL,"
        " \n\tparent_version_id UUID, \n\tnormalized_json JSONB NOT NULL, \n\tstate"
        "_hash VARCHAR(64) NOT NULL, \n\tcreated_by_message_id UUID NOT NULL, \n"
        "\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMA"
        "RY KEY (id), \n\tCONSTRAINT uq_idea_versions_idea_version UNIQUE (idea"
        "_id, version_no), \n\tCONSTRAINT uq_idea_versions_idea_id UNIQUE (idea"
        "_id, id), \n\tCONSTRAINT uq_idea_versions_id_conversation UNIQUE (id, "
        "conversation_id), \n\tCONSTRAINT fk_idea_versions_idea_conversation FO"
        "REIGN KEY(idea_id, conversation_id) REFERENCES ideas (id, conversati"
        "on_id) ON DELETE CASCADE, \n\tCONSTRAINT fk_idea_versions_parent_same_"
        "idea FOREIGN KEY(idea_id, parent_version_id) REFERENCES idea_version"
        "s (idea_id, id) ON DELETE CASCADE, \n\tCONSTRAINT fk_idea_versions_cre"
        "ated_message_conversation FOREIGN KEY(created_by_message_id, convers"
        "ation_id) REFERENCES messages (id, conversation_id) ON DELETE CASCAD"
        "E, \n\tCONSTRAINT ck_idea_versions_version_no CHECK (version_no > 0)\n)"
    ),
    (
        "CREATE TABLE analysis_runs (\n\tid UUID NOT NULL, \n\tconversation_id UU"
        "ID NOT NULL, \n\towner_user_id UUID NOT NULL, \n\tmessage_id UUID NOT NU"
        "LL, \n\tsource_run_id UUID, \n\tbase_idea_version_id UUID, \n\texpected_id"
        "ea_version INTEGER NOT NULL, \n\tidea_version_id UUID, \n\tplanner_appli"
        "ed_at TIMESTAMP WITH TIME ZONE, \n\tstatus VARCHAR(16) NOT NULL, \n\tsta"
        "ge VARCHAR(64) NOT NULL, \n\toutcome VARCHAR(32), \n\tquery TEXT NOT NUL"
        "L, \n\tindex_generation_id UUID, \n\tevidence_snapshot_json JSONB, \n\tans"
        "wer_json JSONB, \n\tcoverage_json JSONB NOT NULL, \n\tevent_seq_high_wat"
        "er BIGINT NOT NULL, \n\tconfig_versions_json JSONB NOT NULL, \n\tidempot"
        "ency_key VARCHAR(255) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL,"
        " \n\tcancel_requested_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMEST"
        "AMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcompleted_at TIMESTAMP "
        "WITH TIME ZONE, \n\terror_code VARCHAR(128), \n\tPRIMARY KEY (id), \n\tCON"
        "STRAINT uq_analysis_runs_id_conversation UNIQUE (id, conversation_id"
        "), \n\tCONSTRAINT fk_runs_owner_conversation FOREIGN KEY(conversation_"
        "id, owner_user_id) REFERENCES conversations (id, owner_user_id) ON D"
        "ELETE CASCADE, \n\tCONSTRAINT fk_runs_message_conversation FOREIGN KEY"
        "(message_id, conversation_id) REFERENCES messages (id, conversation_"
        "id) ON DELETE CASCADE, \n\tCONSTRAINT fk_runs_source_same_conversation"
        " FOREIGN KEY(source_run_id, conversation_id) REFERENCES analysis_run"
        "s (id, conversation_id) ON DELETE CASCADE, \n\tCONSTRAINT fk_runs_base"
        "_version_conversation FOREIGN KEY(base_idea_version_id, conversation"
        "_id) REFERENCES idea_versions (id, conversation_id) ON DELETE CASCAD"
        "E, \n\tCONSTRAINT fk_runs_idea_version_conversation FOREIGN KEY(idea_v"
        "ersion_id, conversation_id) REFERENCES idea_versions (id, conversati"
        "on_id) ON DELETE CASCADE, \n\tCONSTRAINT ck_runs_expected_idea_version"
        " CHECK (expected_idea_version >= 0), \n\tCONSTRAINT ck_runs_status CHE"
        "CK (status IN ('pending','running','completed','failed','cancelled')"
        "), \n\tCONSTRAINT ck_runs_outcome CHECK (outcome IS NULL OR outcome IN"
        " ('analysis','safe_fallback','no_evidence','clarification')), \n\tCONS"
        "TRAINT ck_runs_completed_outcome CHECK ((status = 'completed' AND ou"
        "tcome IS NOT NULL) OR (status <> 'completed' AND outcome IS NULL)), "
        "\n\tCONSTRAINT ck_runs_answer_terminal CHECK (status = 'completed' OR "
        "answer_json IS NULL), \n\tCONSTRAINT ck_runs_idempotency_key CHECK (le"
        "ngth(idempotency_key) BETWEEN 1 AND 255), \n\tCONSTRAINT uq_runs_owner"
        "_conversation_idempotency UNIQUE (owner_user_id, conversation_id, id"
        "empotency_key), \n\tFOREIGN KEY(index_generation_id) REFERENCES index_"
        "generations (id) ON DELETE SET NULL\n)"
    ),
    (
        "CREATE TABLE analysis_jobs (\n\trun_id UUID NOT NULL, \n\tattempts INTEG"
        "ER NOT NULL, \n\tlease_owner VARCHAR(128), \n\tlease_token BIGINT NOT NU"
        "LL, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tnext_attempt_at TIMEST"
        "AMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\theartbeat_at TIMESTAMP "
        "WITH TIME ZONE, \n\tPRIMARY KEY (run_id), \n\tCONSTRAINT ck_analysis_job"
        "s_attempts CHECK (attempts >= 0), \n\tCONSTRAINT ck_analysis_jobs_leas"
        "e_pair CHECK ((lease_owner IS NULL) = (lease_until IS NULL)), \n\tFORE"
        "IGN KEY(run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE\n)"
    ),
    (
        "CREATE TABLE run_events (\n\trun_id UUID NOT NULL, \n\tsequence_no BIGIN"
        "T NOT NULL, \n\tevent_type VARCHAR(64) NOT NULL, \n\tpayload_json JSONB "
        "NOT NULL, \n\tis_terminal BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WIT"
        "H TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (run_id, sequence_"
        "no), \n\tCONSTRAINT ck_run_events_sequence CHECK (sequence_no > 0), \n\t"
        "FOREIGN KEY(run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE\n"
        ")"
    ),
    (
        "CREATE TABLE run_evidence (\n\trun_id UUID NOT NULL, \n\tevidence_id UUI"
        "D NOT NULL, \n\tdocument_id UUID NOT NULL, \n\trevision_id UUID NOT NULL"
        ", \n\tchunk_id UUID NOT NULL, \n\tspan_start INTEGER NOT NULL, \n\tspan_en"
        "d INTEGER NOT NULL, \n\tquoted_span TEXT NOT NULL, \n\tsource_url TEXT N"
        "OT NULL, \n\tretrieval_score FLOAT, \n\trerank_score FLOAT, \n\tindex_gene"
        "ration_id UUID, \n\tPRIMARY KEY (run_id, evidence_id), \n\tFOREIGN KEY(r"
        "un_id) REFERENCES analysis_runs (id) ON DELETE CASCADE, \n\tCONSTRAINT"
        " fk_run_evidence_revision_document FOREIGN KEY(revision_id, document"
        "_id) REFERENCES document_revisions (id, document_id), \n\tCONSTRAINT f"
        "k_run_evidence_chunk_revision FOREIGN KEY(chunk_id, revision_id) REF"
        "ERENCES evidence_chunks (id, revision_id), \n\tCONSTRAINT ck_run_evide"
        "nce_span CHECK (span_start >= 0 AND span_end >= span_start), \n\tFOREI"
        "GN KEY(index_generation_id) REFERENCES index_generations (id) ON DEL"
        "ETE SET NULL\n)"
    ),
)

ALTER_CONSTRAINT_DDL = (
    (
        "source_documents",
        "fk_source_documents_active_revision_same_document",
        (
            "ALTER TABLE source_documents ADD CONSTRAINT fk_source_documents_acti"
            "ve_revision_same_document FOREIGN KEY(id, active_revision_id) REFERE"
            "NCES document_revisions (document_id, id) DEFERRABLE INITIALLY DEFER"
            "RED"
        ),
    ),
    (
        "conversations",
        "fk_conversations_summary_message",
        (
            "ALTER TABLE conversations ADD CONSTRAINT fk_conversations_summary_me"
            "ssage FOREIGN KEY(summary_until_message_id, id) REFERENCES messages "
            "(id, conversation_id) DEFERRABLE INITIALLY DEFERRED"
        ),
    ),
    (
        "ideas",
        "fk_ideas_current_version_same_idea",
        (
            "ALTER TABLE ideas ADD CONSTRAINT fk_ideas_current_version_same_idea "
            "FOREIGN KEY(id, current_version_id) REFERENCES idea_versions (idea_i"
            "d, id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED"
        ),
    ),
    (
        "messages",
        "fk_messages_run_conversation",
        (
            "ALTER TABLE messages ADD CONSTRAINT fk_messages_run_conversation FOR"
            "EIGN KEY(run_id, conversation_id) REFERENCES analysis_runs (id, conv"
            "ersation_id) DEFERRABLE INITIALLY DEFERRED"
        ),
    ),
)

INDEX_DDL = (
    ("CREATE INDEX ix_ingestion_jobs_lease ON ingestion_jobs (status, lease_until, created_at)"),
    (
        "CREATE INDEX ix_outbox_events_unprocessed ON outbox_events (created_"
        "at) WHERE processed_at IS NULL"
    ),
    ("CREATE UNIQUE INDEX ix_auth_sessions_token_hash ON auth_sessions (token_hash)"),
    ("CREATE INDEX ix_auth_sessions_user_expires ON auth_sessions (user_id, expires_at)"),
    ("CREATE INDEX ix_conversations_owner_updated ON conversations (owner_user_id, updated_at)"),
    ("CREATE INDEX ix_evidence_chunks_revision_section ON evidence_chunks (revision_id, section)"),
    (
        "CREATE INDEX ix_index_members_generation_revision ON index_members ("
        "generation_id, revision_id)"
    ),
    ("CREATE INDEX ix_messages_conversation_created ON messages (conversation_id, created_at)"),
    ("CREATE INDEX ix_graph_facts_revision ON graph_facts (revision_id)"),
    ("CREATE INDEX ix_idea_versions_idea_version ON idea_versions (idea_id, version_no)"),
    (
        "CREATE INDEX ix_analysis_runs_conversation_created ON analysis_runs "
        "(conversation_id, created_at)"
    ),
    (
        "CREATE UNIQUE INDEX uq_analysis_runs_one_active_per_conversation ON "
        "analysis_runs (conversation_id) WHERE status IN ('pending', 'running"
        "')"
    ),
    ("CREATE INDEX ix_analysis_jobs_next_lease ON analysis_jobs (next_attempt_at, lease_until)"),
    ("CREATE UNIQUE INDEX uq_run_events_one_terminal ON run_events (run_id) WHERE is_terminal"),
    ("CREATE INDEX ix_run_evidence_document ON run_evidence (run_id, document_id)"),
)

REVERSE_TABLES = (
    "run_evidence",
    "run_events",
    "analysis_jobs",
    "analysis_runs",
    "idea_versions",
    "graph_facts",
    "revision_index_acks",
    "messages",
    "index_members",
    "ideas",
    "evidence_chunks",
    "index_catalog",
    "eval_results",
    "document_revisions",
    "conversations",
    "auth_sessions",
    "users",
    "source_documents",
    "outbox_events",
    "ingestion_jobs",
    "index_generations",
    "eval_runs",
    "eval_cases",
)


def upgrade() -> None:
    for statement in TABLE_DDL:
        op.execute(statement)
    for _, _, statement in ALTER_CONSTRAINT_DDL:
        op.execute(statement)
    for statement in INDEX_DDL:
        op.execute(statement)


def downgrade() -> None:
    for table_name, constraint_name, _ in reversed(ALTER_CONSTRAINT_DDL):
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")
    for table_name in REVERSE_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
